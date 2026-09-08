"""Adapter selection (ADR-018).

Each integration has a fixture adapter and a real one. Which is used is a
configuration choice, never a code change, so the product runs end to end whether
or not the external system is reachable.

The default is always ``fixture``. An operator opts into a real adapter by setting
the variable and supplying whatever that adapter needs. If a real adapter is
selected but its configuration is incomplete, the selection helper says so rather
than silently falling back — a silent fallback would make a screen claim it is
talking to GitHub when it is not.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum


class AdapterKind(StrEnum):
    FIXTURE = "fixture"
    REAL = "real"


@dataclass(frozen=True, slots=True)
class AdapterChoice:
    kind: AdapterKind
    #: Why the real adapter could not be used, when one was asked for.
    unavailable_reason: str | None = None

    @property
    def use_real(self) -> bool:
        return self.kind is AdapterKind.REAL


def _select(variable: str, real_value: str, requirements: dict[str, str | None]) -> AdapterChoice:
    requested = os.getenv(variable, AdapterKind.FIXTURE.value).strip().lower()
    if requested != real_value:
        return AdapterChoice(AdapterKind.FIXTURE)

    missing = [name for name, value in requirements.items() if not value]
    if missing:
        return AdapterChoice(
            AdapterKind.FIXTURE,
            f"{variable}={real_value}로 설정됐지만 {', '.join(missing)}가 없습니다.",
        )
    return AdapterChoice(AdapterKind.REAL)


# ── kordoc 문서 변환기 ────────────────────────────────────────────────────


def kordoc_cli() -> str | None:
    """Path to kordoc's CLI entry point, or ``None``.

    A local checkout is used directly. Without one the adapter falls back to
    ``npx kordoc``, which needs no path but does need network on first use.
    """

    return os.getenv("LEP_KORDOC_CLI") or None


def kordoc_use_npx() -> bool:
    return os.getenv("LEP_KORDOC_USE_NPX", "").strip() == "1"


def converter_choice() -> AdapterChoice:
    reachable = kordoc_cli() or ("1" if kordoc_use_npx() else None)
    return _select(
        "LEP_ADAPTER_CONVERTER",
        "kordoc",
        {"LEP_KORDOC_CLI 또는 LEP_KORDOC_USE_NPX": reachable},
    )


def kordoc_output_dir() -> str:
    return os.getenv("LEP_KORDOC_OUTPUT_DIR", ".kordoc-out")


# ── 깃허브 ────────────────────────────────────────────────────────────────


def github_token() -> str | None:
    return os.getenv("LEP_GITHUB_TOKEN") or None


def github_repos() -> dict[str, str]:
    """Project ID to ``owner/name`` map.

    ``LEP_GITHUB_REPOS`` takes a JSON object. ``LEP_GITHUB_REPO`` is the
    single-repository shorthand and applies to every project.
    """

    raw = os.getenv("LEP_GITHUB_REPOS")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return {str(key): str(value) for key, value in parsed.items()}
        return {}

    single = os.getenv("LEP_GITHUB_REPO")
    return {"*": single} if single else {}


def github_api_base() -> str:
    return os.getenv("LEP_GITHUB_API_BASE", "https://api.github.com")


def vcs_choice() -> AdapterChoice:
    repos = github_repos()
    return _select(
        "LEP_ADAPTER_VCS",
        "github",
        {
            "LEP_GITHUB_TOKEN": github_token(),
            "LEP_GITHUB_REPO 또는 LEP_GITHUB_REPOS": next(iter(repos.values()), None),
        },
    )


# ── 옵시디언 볼트 ────────────────────────────────────────────────────────


def vault_root() -> str | None:
    return os.getenv("LEP_OBSIDIAN_VAULT") or None


def vault_choice() -> AdapterChoice:
    return _select(
        "LEP_ADAPTER_VAULT",
        "obsidian",
        {"LEP_OBSIDIAN_VAULT": vault_root()},
    )


# ── 하이웍스 메일 ────────────────────────────────────────────────────────


def hiworks_user() -> str | None:
    return os.getenv("LEP_HIWORKS_USER") or None


def hiworks_password() -> str | None:
    return os.getenv("LEP_HIWORKS_PASSWORD") or None


def mail_choice() -> AdapterChoice:
    return _select(
        "LEP_ADAPTER_MAIL",
        "hiworks",
        {
            "LEP_HIWORKS_USER": hiworks_user(),
            "LEP_HIWORKS_PASSWORD": hiworks_password(),
        },
    )

# ── 로컬 LLM ──────────────────────────────────────────────────────────────


def llm_base_url() -> str:
    """OpenAI 호환 엔드포인트. compose의 ollama가 기본값이다."""

    return os.getenv("LEP_LLM_BASE_URL", "http://ollama:11434/v1").rstrip("/")


def llm_model() -> str | None:
    """쓸 모델 이름. 없으면 실제 어댑터를 켜지 않는다.

    기본값을 두지 않는다. 서버에 없는 모델 이름을 몰래 고르면 첫 분류 요청에서야
    404가 나고, 그때는 왜 실패했는지 화면에서 알 길이 없다.
    """

    return os.getenv("LEP_LLM_MODEL") or None


def llm_timeout_seconds() -> int:
    raw = os.getenv("LEP_LLM_TIMEOUT_SECONDS", "180")
    try:
        return max(10, int(raw))
    except ValueError:
        return 180


def llm_choice() -> AdapterChoice:
    return _select("LEP_ADAPTER_LLM", "ollama", {"LEP_LLM_MODEL": llm_model()})
