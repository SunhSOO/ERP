"""kordoc document converter adapter (WP-PKD-030, ADR-018).

kordoc is a Node CLI that turns Markdown into Korean government-style HWPX.
Upstream: https://github.com/chrisryugj/kordoc (npm package ``kordoc``).

This wraps the ``generate`` subcommand:

    kordoc generate <markdown> -o <output.hwpx> --preset <preset>

Two ways to reach it. ``LEP_KORDOC_CLI`` points at a local checkout's
``dist/cli.js`` and is run with ``node``; ``LEP_KORDOC_USE_NPX=1`` runs
``npx --yes kordoc`` instead, which needs no path but fetches on first use.

The adapter satisfies ``DocumentConverterPort``, so nothing above the
infrastructure layer changes when it replaces the fixture.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from ....common.adapters import kordoc_cli, kordoc_output_dir, kordoc_use_npx
from ..domain.ports import ArtifactConversionResult, ConversionArtifact

logger = logging.getLogger(__name__)

#: kordoc's presets. The mockup's 보고서 template maps to ``보고서``.
#: Keys are what our screens call things; values are what kordoc expects.
PRESETS: dict[str, str] = {
    "표준 검수보고서": "보고서",
    "보고서": "보고서",
    "기안문": "기안문",
    "계획서": "계획서",
    "통지": "통지",
    "회의록": "회의록",
    "개조식": "개조식",
    "보도자료": "보도자료",
}

DEFAULT_PRESET = "보고서"

#: A conversion that has not finished in this long is treated as failed. The
#: local CLI turns a small report around in well under a second.
TIMEOUT_SECONDS = 120

#: kordoc writes Korean on stdout and stderr. ``text=True`` alone decodes with the
#: locale encoding, which is cp949 on a Korean Windows install and raises inside
#: subprocess's reader thread on UTF-8 bytes. Every call below therefore passes
#: ``encoding="utf-8"`` explicitly so error messages survive instead of being
#: lost to a thread exception.
OUTPUT_ENCODING = "utf-8"

#: How many fresh UUIDs to try before giving up on finding an unused artifact
#: name. Collisions are practically impossible; this only guards against a
#: stale file left over from a previous run reusing the same name.
MAX_ARTIFACT_NAME_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class KordocConverter:
    """Runs the real kordoc CLI as a subprocess."""

    cli_path: str | None = None
    use_npx: bool = False
    output_dir: str = ".kordoc-out"

    @classmethod
    def from_env(cls) -> KordocConverter:
        return cls(
            cli_path=kordoc_cli(),
            use_npx=kordoc_use_npx(),
            output_dir=kordoc_output_dir(),
        )

    @property
    def name(self) -> str:
        return "kordoc"

    @property
    def version(self) -> str:
        """The installed CLI's version, or a marker when it cannot be asked.

        Reported on the integrations screen, so guessing would be worse than
        admitting the tool did not answer.
        """

        try:
            result = subprocess.run(  # noqa: S603
                [*self._command(), "--version"],
                capture_output=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
                text=True,
                encoding=OUTPUT_ENCODING,
                errors="replace",
            )
        except (OSError, subprocess.SubprocessError):
            return "알 수 없음"
        if result.returncode != 0:
            return "알 수 없음"
        return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "알 수 없음"

    def convert(self, markdown: str, *, template: str) -> tuple[bool, str | None]:
        """Generate an HWPX from Markdown.

        Returns ``(succeeded, failure_detail)``. A failure is reported as a
        failure; the pipeline screen shows it with a retry rather than claiming
        the document is ready. Kept for callers that only need the boolean
        outcome; see ``convert_with_artifact`` for the stored artifact identity.
        """

        result = self.convert_with_artifact(markdown, template=template)
        return result.succeeded, result.detail

    def convert_with_artifact(
        self, markdown: str, *, template: str
    ) -> ArtifactConversionResult:
        """Generate an HWPX from Markdown and persist it as a distinct artifact.

        The stored file name is a generated UUID inside the configured output
        directory; caller-supplied filenames or paths never decide where the
        artifact is stored, and an existing artifact is never overwritten.
        Failure details are sanitized categories: no markdown content,
        converter stdout/stderr, or local filesystem paths are included.
        """

        if not markdown.strip():
            return ArtifactConversionResult(False, "빈 문서는 변환할 수 없습니다.")

        preset = PRESETS.get(template, DEFAULT_PRESET)
        destination = Path(self.output_dir)

        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError:
            return ArtifactConversionResult(False, "출력 디렉터리를 만들지 못했습니다.")

        try:
            with tempfile.TemporaryDirectory(prefix="lep-kordoc-") as workspace:
                source = Path(workspace) / "input.md"
                produced = Path(workspace) / "output.hwpx"
                source.write_text(markdown, encoding="utf-8")

                try:
                    result = subprocess.run(  # noqa: S603
                        [
                            *self._command(),
                            "generate",
                            str(source),
                            "-o",
                            str(produced),
                            "--preset",
                            preset,
                        ],
                        capture_output=True,
                        timeout=TIMEOUT_SECONDS,
                        check=False,
                        text=True,
                        encoding=OUTPUT_ENCODING,
                        errors="replace",
                    )
                except FileNotFoundError:
                    return ArtifactConversionResult(
                        False, "변환기를 실행할 수 없습니다. node 또는 npx가 필요합니다."
                    )
                except subprocess.TimeoutExpired:
                    return ArtifactConversionResult(
                        False, f"변환이 {TIMEOUT_SECONDS}초 안에 끝나지 않았습니다."
                    )
                except OSError:
                    return ArtifactConversionResult(False, "변환기를 실행하지 못했습니다.")

                if result.returncode != 0:
                    return ArtifactConversionResult(False, "변환기가 오류로 종료했습니다.")

                if not produced.is_file() or produced.stat().st_size == 0:
                    return ArtifactConversionResult(False, "변환기가 파일을 만들지 않았습니다.")

                payload = produced.read_bytes()
                if not payload:
                    return ArtifactConversionResult(False, "변환기가 파일을 만들지 않았습니다.")
        except OSError:
            return ArtifactConversionResult(False, "임시 작업 공간을 사용하지 못했습니다.")

        artifact = self._store_artifact(payload, destination)
        if artifact is None:
            return ArtifactConversionResult(False, "생성된 파일을 저장하지 못했습니다.")

        return ArtifactConversionResult(True, None, artifact)

    def _store_artifact(
        self, payload: bytes, destination: Path
    ) -> ConversionArtifact | None:
        """Write ``payload`` under a generated, unused name in ``destination``.

        Uses exclusive binary creation (``Path.open("xb")``, not the raw
        ``os.O_CREAT | os.O_EXCL`` flags) so a concurrent or repeated
        conversion never overwrites a previously stored artifact, and so the
        write is never subject to the CRT text-mode translation that
        ``os.open`` falls into on Windows without ``os.O_BINARY``. Because the
        exclusive open guarantees *this* call created the file, a write
        failure only ever removes the candidate it just created, never a
        pre-existing file that caused a naming collision.
        """

        checksum = hashlib.sha256(payload).hexdigest()
        for _ in range(MAX_ARTIFACT_NAME_ATTEMPTS):
            candidate = destination / f"{uuid.uuid4().hex}.hwpx"
            try:
                handle = candidate.open("xb")
            except FileExistsError:
                continue
            except OSError:
                return None
            try:
                with handle:
                    handle.write(payload)
            except OSError:
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    logger.warning("kordoc artifact cleanup failed after a write error")
                return None
            return ConversionArtifact(
                path=str(candidate), size_bytes=len(payload), sha256=checksum
            )
        return None

    def _command(self) -> list[str]:
        if self.cli_path:
            return ["node", self.cli_path]
        if self.use_npx:
            return ["npx", "--yes", "kordoc"]
        # from_env only builds this adapter when one of the two is configured;
        # a direct construction without either still gets a usable default.
        return ["npx", "--yes", "kordoc"]
