"""GitHub repository adapter (WP-PKD-031, ADR-018).

Reads a real repository through the GitHub REST API and reconciles what it finds
against the WBS. The reconciliation is the point of screen 07: work happening in
the repository that the plan does not know about, and plan items the repository
contradicts.

Matching is by task code. A pull request, branch or commit belongs to a task when
its title, branch name or message mentions that task's code. Two code shapes are
recognised: this track's ``TSK-1234`` and the work-package form ``WP-PLT-001``,
which is what this repository's own branches use.

The token is read from the environment and never logged. ``AGENTS.md`` 1절 7항.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import httpx

from ....common.adapters import github_api_base, github_repos, github_token
from ..domain.entities import (
    Credential,
    LinkHealth,
    Mismatch,
    MismatchKind,
    ProjectModel,
    TaskMapping,
    VcsStatus,
)
from .fixtures import _DEFAULT_LLM_CREDENTIAL, FixtureIntegrationAdapter

#: Task codes this adapter recognises in repository text.
TASK_CODE = re.compile(r"\b(TSK-\d+|WP-[A-Z]+(?:-[A-Z]+)?-\d+)\b")

TIMEOUT_SECONDS = 15
#: Enough to see recent activity without paging the whole history.
COMMIT_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class RepoActivity:
    """What the repository currently shows."""

    open_pull_requests: int
    #: (ref, title, state, merged, codes)
    pull_requests: list[tuple[str, str, str, bool, set[str]]]
    branches: list[tuple[str, set[str]]]
    commits: list[tuple[str, str, set[str]]]
    issues: list[tuple[str, str, str, set[str]]]
    pushed_at: datetime
    #: Work on the default branch is the plan of record, not a deviation.
    default_branch: str = "main"


def extract_codes(*texts: str) -> set[str]:
    """Pull task codes out of repository text."""

    found: set[str] = set()
    for text in texts:
        found.update(match.group(1) for match in TASK_CODE.finditer(text or ""))
    return found


class GitHubVcsAdapter:
    """Talks to GitHub. Everything else in this module stays unchanged."""

    def __init__(
        self,
        *,
        token: str,
        repos: dict[str, str],
        api_base: str = "https://api.github.com",
        client: httpx.Client | None = None,
    ) -> None:
        self._token = token
        self._repos = repos
        self._api_base = api_base.rstrip("/")
        self._client = client

    @classmethod
    def from_env(cls) -> GitHubVcsAdapter:
        token = github_token()
        if token is None:
            raise ValueError("LEP_GITHUB_TOKEN이 없습니다.")
        return cls(token=token, repos=github_repos(), api_base=github_api_base())

    def repo_for(self, project_id: str) -> str | None:
        return self._repos.get(project_id) or self._repos.get("*")

    # ── HTTP ───────────────────────────────────────────────────────────────
    def _get(self, path: str, params: dict[str, str | int] | None = None) -> object:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"{self._api_base}{path}"
        if self._client is not None:
            response = self._client.get(url, headers=headers, params=params)
        else:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_activity(self, repo: str) -> RepoActivity:
        repository = self._get(f"/repos/{repo}")
        pulls = self._get(f"/repos/{repo}/pulls", {"state": "all", "per_page": 50})
        branches = self._get(f"/repos/{repo}/branches", {"per_page": 100})
        commits = self._get(f"/repos/{repo}/commits", {"per_page": COMMIT_PAGE_SIZE})
        issues = self._get(f"/repos/{repo}/issues", {"state": "all", "per_page": 50})

        assert isinstance(repository, dict)
        assert isinstance(pulls, list)
        assert isinstance(branches, list)
        assert isinstance(commits, list)
        assert isinstance(issues, list)

        pull_rows = [
            (
                f"PR #{item['number']}",
                str(item.get("title") or ""),
                str(item.get("state") or ""),
                item.get("merged_at") is not None,
                extract_codes(
                    str(item.get("title") or ""),
                    str((item.get("head") or {}).get("ref") or ""),
                ),
            )
            for item in pulls
        ]

        branch_rows = [
            (str(item.get("name") or ""), extract_codes(str(item.get("name") or "")))
            for item in branches
        ]

        commit_rows = [
            (
                str(item.get("sha") or "")[:7],
                str((item.get("commit") or {}).get("message") or "").split("\n")[0],
                extract_codes(str((item.get("commit") or {}).get("message") or "")),
            )
            for item in commits
        ]

        # GitHub returns pull requests through the issues endpoint too; drop them
        # so a PR is not counted twice.
        issue_rows = [
            (
                f"이슈 #{item['number']}",
                str(item.get("title") or ""),
                str(item.get("state") or ""),
                extract_codes(str(item.get("title") or "")),
            )
            for item in issues
            if "pull_request" not in item
        ]

        pushed_raw = str(repository.get("pushed_at") or "")
        pushed_at = (
            datetime.fromisoformat(pushed_raw.replace("Z", "+00:00"))
            if pushed_raw
            else datetime.now(tz=UTC)
        )

        return RepoActivity(
            open_pull_requests=len(
                [row for row in pull_rows if row[2] == "open"]
            ),
            pull_requests=pull_rows,
            branches=branch_rows,
            commits=commit_rows,
            issues=issue_rows,
            pushed_at=pushed_at,
            default_branch=str(repository.get("default_branch") or "main"),
        )

    # ── reconciliation ─────────────────────────────────────────────────────
    def reconcile(
        self,
        project_id: str,
        repo: str,
        activity: RepoActivity,
        tasks: list[tuple[str, str, str]],
    ) -> tuple[VcsStatus, list[Mismatch], list[TaskMapping]]:
        """Compare repository activity with the WBS.

        ``tasks`` is ``(code, title, status)`` read from the delivery module's
        public interface. This adapter never touches delivery's data directly.
        """

        by_code = {code: (title, status) for code, title, status in tasks}
        mappings: list[TaskMapping] = []
        mismatches: list[Mismatch] = []
        matched_codes: set[str] = set()

        for ref, title, state, merged, codes in activity.pull_requests:
            known = codes & by_code.keys()
            matched_codes |= known
            if not known:
                mappings.append(
                    TaskMapping(
                        task_code=None,
                        task_title=title or ref,
                        vcs_ref=ref,
                        task_status="vcs_only",
                        aligned=False,
                    )
                )
                mismatches.append(
                    Mismatch(
                        id=f"mis-{ref.replace(' ', '').replace('#', '')}",
                        project_id=project_id,
                        kind=MismatchKind.UNDEFINED_WORK,
                        title="WBS 외 작업 감지",
                        detail=(
                            f'{ref} "{title}"에 대응하는 WBS 태스크가 없습니다. '
                            f"저장소 {repo}."
                        ),
                        task_code=None,
                        vcs_ref=ref,
                    )
                )
                continue

            for code in sorted(known):
                task_title, task_status = by_code[code]
                # Marked done in the plan but the pull request is not merged.
                aligned = not (task_status == "done" and state == "open" and not merged)
                mappings.append(
                    TaskMapping(
                        task_code=code,
                        task_title=task_title,
                        vcs_ref=ref,
                        task_status=task_status,
                        aligned=aligned,
                    )
                )
                if not aligned:
                    mismatches.append(
                        Mismatch(
                            id=f"mis-{code}",
                            project_id=project_id,
                            kind=MismatchKind.STATUS_CONFLICT,
                            title="완료 표시됐지만 PR 미병합",
                            detail=(
                                f'{code} "{task_title}"는 WBS상 완료지만 연결된 '
                                f"{ref}은 아직 열려 있습니다."
                            ),
                            task_code=code,
                            vcs_ref=ref,
                        )
                    )

        for ref, _title, _state, codes in activity.issues:
            known = codes & by_code.keys()
            matched_codes |= known
            for code in sorted(known):
                task_title, task_status = by_code[code]
                mappings.append(
                    TaskMapping(
                        task_code=code,
                        task_title=task_title,
                        vcs_ref=ref,
                        task_status=task_status,
                        aligned=True,
                    )
                )

        # Branches carrying a code nobody has opened a pull request for still
        # count as linked work; they are what this repository currently has.
        seen_refs = {ref for ref, *_ in activity.pull_requests}
        for name, codes in activity.branches:
            if name == activity.default_branch:
                continue

            known = codes & by_code.keys()
            matched_codes |= known
            for code in sorted(known):
                task_title, task_status = by_code[code]
                mappings.append(
                    TaskMapping(
                        task_code=code,
                        task_title=task_title,
                        vcs_ref=f"브랜치 {name}",
                        task_status=task_status,
                        aligned=True,
                    )
                )

            # A named branch carrying a work code the plan does not have is the
            # same gap a stray pull request is: someone is doing work the WBS
            # cannot see. Branches with no code at all are left alone, since
            # plenty of them are throwaway.
            unknown = codes - by_code.keys()
            if unknown and f"브랜치 {name}" not in seen_refs:
                label = ", ".join(sorted(unknown))
                mappings.append(
                    TaskMapping(
                        task_code=None,
                        task_title=f"{label} (WBS에 없는 코드)",
                        vcs_ref=f"브랜치 {name}",
                        task_status="vcs_only",
                        aligned=False,
                    )
                )
                mismatches.append(
                    Mismatch(
                        id=f"mis-branch-{name.replace('/', '-')}",
                        project_id=project_id,
                        kind=MismatchKind.UNDEFINED_WORK,
                        title="WBS 외 브랜치 감지",
                        detail=(
                            f"브랜치 {name}이 {label} 작업을 진행 중이지만 WBS에 "
                            f"대응하는 태스크가 없습니다. 저장소 {repo}."
                        ),
                        task_code=None,
                        vcs_ref=f"브랜치 {name}",
                    )
                )

        total = len(by_code) or 1
        match_rate = round(len(matched_codes) / total * 100)

        # Health is about what the reconciliation found, not merely whether the
        # request succeeded. Reporting "정상" next to a 0% match rate would be a
        # contradiction the user has to resolve themselves: nothing in the
        # repository is traceable to the plan, and that is worth flagging.
        if mismatches:
            health = LinkHealth.MISMATCH
        elif matched_codes:
            health = LinkHealth.OK
        else:
            health = LinkHealth.STALE

        status = VcsStatus(
            project_id=project_id,
            repository=repo,
            health=health,
            last_sync_at=datetime.now(tz=UTC),
            open_pull_requests=activity.open_pull_requests,
            match_rate_percent=match_rate,
        )
        return status, mismatches, mappings


@dataclass
class GitHubIntegrationAdapter:
    """Real GitHub reads with fixture project-model settings.

    Only the repository half of this module has a real backend today; the
    project-model list (name, priority, GPU share) has no persistence yet and
    stays on the fixture. LLM *runtime status* is not part of this adapter at
    all — ``IntegrationService.server()`` and ``.credentials()`` read it
    directly through a separate ``LlmRuntimePort`` (WP-PKD-033A).
    """

    github: GitHubVcsAdapter
    #: The repository half goes real; the project-model list stays on the
    #: fixture until settings persistence exists, so this is deliberately the
    #: concrete fixture type.
    fallback: FixtureIntegrationAdapter
    _cache: dict[str, tuple[VcsStatus, list[Mismatch], list[TaskMapping]]] | None = None

    def __post_init__(self) -> None:
        self._cache = {}

    def _load(self, project_id: str) -> tuple[VcsStatus, list[Mismatch], list[TaskMapping]] | None:
        assert self._cache is not None
        if project_id in self._cache:
            return self._cache[project_id]

        repo = self.github.repo_for(project_id)
        if repo is None:
            return None

        # WBS 태스크는 delivery 모듈이 소유한다. 데이터베이스 세션이 필요하므로
        # 저장소 정합 계산은 요청 경로에서 세션과 함께 호출돼야 한다.
        # 프로젝트별 저장소 설정이 들어오는 WP-PKD-041에서 배선한다.
        tasks: list[tuple[str, str, str]] = []
        activity = self.github.fetch_activity(repo)
        result = self.github.reconcile(project_id, repo, activity, tasks)
        self._cache[project_id] = result
        return result

    def vcs_status(self, project_id: str) -> VcsStatus | None:
        loaded = self._load(project_id)
        return loaded[0] if loaded else None

    def list_mismatches(self, project_id: str) -> list[Mismatch]:
        loaded = self._load(project_id)
        return list(loaded[1]) if loaded else []

    def get_mismatch(self, mismatch_id: str) -> Mismatch | None:
        assert self._cache is not None
        for _status, mismatches, _mappings in self._cache.values():
            for mismatch in mismatches:
                if mismatch.id == mismatch_id:
                    return mismatch
        return None

    def replace_mismatch(self, mismatch: Mismatch) -> Mismatch:
        assert self._cache is not None
        cached = self._cache.get(mismatch.project_id)
        if cached is None:
            return mismatch
        status, mismatches, mappings = cached
        updated = [mismatch if item.id == mismatch.id else item for item in mismatches]
        self._cache[mismatch.project_id] = (status, updated, mappings)
        return mismatch

    def list_mappings(self, project_id: str) -> list[TaskMapping]:
        loaded = self._load(project_id)
        return list(loaded[2]) if loaded else []

    def resync_vcs(self, project_id: str) -> VcsStatus:
        assert self._cache is not None
        self._cache.pop(project_id, None)
        loaded = self._load(project_id)
        if loaded is None:
            raise ValueError(f"저장소가 설정되지 않았습니다: {project_id}")
        return loaded[0]

    # ── AI settings: name/network_note and the project-model list stay on the
    # fixture (no settings persistence yet). Runtime status is read live and
    # lives entirely outside this adapter — see IntegrationService.server(). ─
    def server(self) -> dict[str, object]:
        return self.fallback.server()

    def list_models(self) -> list[ProjectModel]:
        return self.fallback.list_models()

    def replace_model(self, model: ProjectModel) -> ProjectModel:
        return self.fallback.replace_model(model)

    def credentials(
        self,
        project_id: str,
        converter: tuple[str, str],
        llm: Credential = _DEFAULT_LLM_CREDENTIAL,
    ) -> list[Credential]:
        base = self.fallback.credentials(project_id, converter, llm)
        repo = self.github.repo_for(project_id)
        if repo is None:
            return base
        return [
            replace(
                item,
                health=LinkHealth.OK,
                detail=f"{repo}에 연결됨",
                missing_input=None,
            )
            if item.kind == "vcs"
            else item
            for item in base
        ]
