"""WP-PKD-DMS-20260909-A: kordoc conversion artifacts.

``KordocConverter`` used to copy every successful conversion over the same
``latest.hwpx`` file, so two conversions in flight (or a retry after review)
silently destroyed each other's output. These tests drive the subprocess
through mocks only, per ``AGENTS.md`` 14절: no real kordoc/node/npx process is
started.
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock

import pytest

from lep.modules.documents.domain.ports import ArtifactConversionResult
from lep.modules.documents.infrastructure.kordoc_converter import KordocConverter


def _fake_run_that_writes(payload: bytes) -> Callable[..., MagicMock]:
    """Build a ``subprocess.run`` stand-in that writes ``payload`` to ``-o``."""

    def run(cmd: list[str], **_kwargs: object) -> MagicMock:
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_bytes(payload)
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    return run


def _converter(tmp_path: Path) -> KordocConverter:
    return KordocConverter(cli_path="fake-cli.js", output_dir=str(tmp_path / "out"))


# ── 성공: 서로 다른 산출물 ──────────────────────────────────────────────────


def test_two_successful_conversions_each_keep_a_distinct_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    converter = _converter(tmp_path)

    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"hwpx-bytes-one"))
    first = converter.convert_with_artifact("# 첫 번째 문서\n", template="보고서")

    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"hwpx-bytes-two"))
    second = converter.convert_with_artifact("# 두 번째 문서\n", template="보고서")

    assert first.succeeded is True
    assert second.succeeded is True
    assert first.artifact is not None
    assert second.artifact is not None
    assert first.artifact.path != second.artifact.path
    assert Path(first.artifact.path).is_file()
    assert Path(second.artifact.path).is_file()
    assert Path(first.artifact.path).read_bytes() == b"hwpx-bytes-one"
    assert Path(second.artifact.path).read_bytes() == b"hwpx-bytes-two"


def test_artifact_size_and_checksum_match_the_written_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"deterministic-hwpx-payload"
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(payload))

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.artifact is not None
    assert result.artifact.size_bytes == len(payload)
    assert result.artifact.sha256 == hashlib.sha256(payload).hexdigest()


def test_control_byte_payload_round_trips_and_checksums_exactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR, LF, NUL, and 0x1a (the CRT text-mode EOF marker on Windows) must
    survive storage byte-for-byte."""

    payload = b"line-one\r\nline-two\x00tail\x1amore-bytes-after-the-marker"
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(payload))

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.artifact is not None
    assert result.artifact.size_bytes == len(payload)
    assert result.artifact.sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(result.artifact.path).read_bytes() == payload


def test_stored_artifact_path_is_inside_the_configured_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caller filenames/paths never decide where the artifact lands."""

    output_dir = tmp_path / "out"
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"bytes"))
    converter = KordocConverter(cli_path="fake-cli.js", output_dir=str(output_dir))

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.artifact is not None
    assert Path(result.artifact.path).parent == output_dir
    # generated identity, not something derived from caller input
    assert "문서" not in Path(result.artifact.path).name


# ── convert() 호환성 ────────────────────────────────────────────────────────


def test_convert_keeps_the_boolean_tuple_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"bytes"))

    succeeded, detail = _converter(tmp_path).convert("# 문서\n", template="보고서")

    assert (succeeded, detail) == (True, None)


def test_convert_still_refuses_blank_markdown_without_running_anything(
    tmp_path: Path,
) -> None:
    converter = _converter(tmp_path)

    succeeded, detail = converter.convert("   \n  ", template="보고서")

    assert succeeded is False
    assert detail == "빈 문서는 변환할 수 없습니다."


# ── 실패: 출력 없음/빈 파일 ──────────────────────────────────────────────────


def test_missing_output_file_is_not_reported_as_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> MagicMock:
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess, "run", run)

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result == ArtifactConversionResult(False, "변환기가 파일을 만들지 않았습니다.")


def test_empty_output_file_is_not_reported_as_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b""))

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None


# ── 실패: subprocess 오류/타임아웃/비정상 종료 ───────────────────────────────


def test_subprocess_failure_is_sanitized_not_leaking_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> MagicMock:
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "/secret/local/path/leaked-internal-trace.js:42 boom"
        return result

    monkeypatch.setattr(subprocess, "run", run)

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert result.detail is not None
    assert "secret" not in result.detail
    assert "leaked-internal-trace" not in result.detail


def test_timeout_is_sanitized_not_leaking_local_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=str(tmp_path / "secret-cli.js"), timeout=120)

    monkeypatch.setattr(subprocess, "run", run)

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert str(tmp_path) not in (result.detail or "")


def test_missing_converter_binary_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> None:
        raise FileNotFoundError("node not found")

    monkeypatch.setattr(subprocess, "run", run)

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert "node" in (result.detail or "")


def test_unwritable_output_directory_is_sanitized_not_leaking_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = tmp_path / "blocked-out"
    blocked.write_text("this is a file, not a directory", encoding="utf-8")
    converter = KordocConverter(cli_path="fake-cli.js", output_dir=str(blocked))

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert str(blocked) not in (result.detail or "")


def test_markdown_content_never_appears_in_a_failure_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> MagicMock:
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "일급비밀 고객 정보가 stderr로 새어나온 상황을 가정합니다"
        return result

    monkeypatch.setattr(subprocess, "run", run)

    sensitive_markdown = "일급비밀 고객 정보"
    result = _converter(tmp_path).convert_with_artifact(
        f"# {sensitive_markdown}\n", template="보고서"
    )

    assert result.detail is not None
    assert sensitive_markdown not in result.detail


# ── 저장 실패/충돌 시 정리 ─────────────────────────────────────────────────


def test_partial_write_failure_cleans_up_only_the_candidate_it_just_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    converter = _converter(tmp_path)
    real_open = Path.open

    class FlakyHandle:
        def __init__(self, path: Path) -> None:
            self._path = path
            self._real: object = None

        def __enter__(self) -> FlakyHandle:
            self._real = real_open(self._path, "xb")
            return self

        def write(self, data: bytes) -> int:
            self._real.write(data[:1])  # type: ignore[attr-defined]
            raise OSError("disk full")

        def __exit__(self, *_exc: object) -> Literal[False]:
            self._real.close()  # type: ignore[attr-defined]
            return False

    def flaky_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if mode == "xb":
            return FlakyHandle(self)
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky_open)
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"bytes"))

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert list(output_dir.glob("*.hwpx")) == []


def test_unlink_failure_after_write_failure_still_returns_sanitized_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Best-effort cleanup must not let an ``unlink`` failure escape or leak
    the candidate path; the caller only ever sees a sanitized failure."""

    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    converter = _converter(tmp_path)
    real_open = Path.open

    class FlakyHandle:
        def __init__(self, path: Path) -> None:
            self._path = path
            self._real: object = None

        def __enter__(self) -> FlakyHandle:
            self._real = real_open(self._path, "xb")
            return self

        def write(self, _data: bytes) -> int:
            raise OSError("disk full")

        def __exit__(self, *_exc: object) -> Literal[False]:
            self._real.close()  # type: ignore[attr-defined]
            return False

    def flaky_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if mode == "xb":
            return FlakyHandle(self)
        return real_open(self, mode, *args, **kwargs)

    def flaky_unlink(self: Path, *, missing_ok: bool = False) -> None:
        raise OSError("cleanup also failed")

    monkeypatch.setattr(Path, "open", flaky_open)
    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"bytes"))

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert result.detail is not None
    assert str(output_dir) not in result.detail


def test_temp_source_write_failure_returns_sanitized_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure writing the temporary markdown source is a sanitized failure,
    never a raised exception or a leaked local path."""

    converter = _converter(tmp_path)
    real_write_text = Path.write_text

    def flaky_write_text(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
        if self.name == "input.md":
            raise OSError("disk full")
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert str(tmp_path) not in (result.detail or "")


def test_produced_output_read_failure_returns_sanitized_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure reading back the converter's own output is a sanitized
    failure, never a raised exception or a leaked local path."""

    converter = _converter(tmp_path)
    real_read_bytes = Path.read_bytes

    def flaky_read_bytes(self: Path) -> bytes:
        if self.name == "output.hwpx":
            raise OSError("read failed")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"bytes"))

    result = converter.convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is False
    assert result.artifact is None
    assert str(tmp_path) not in (result.detail or "")


def test_existing_filename_collision_is_preserved_and_retried_past(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    colliding_id = uuid.UUID(int=1)
    fresh_id = uuid.UUID(int=2)
    existing_path = output_dir / f"{colliding_id.hex}.hwpx"
    existing_path.write_bytes(b"pre-existing-collision-content")

    ids = iter([colliding_id, fresh_id])
    monkeypatch.setattr(uuid, "uuid4", lambda: next(ids))
    monkeypatch.setattr(subprocess, "run", _fake_run_that_writes(b"new-bytes"))

    result = _converter(tmp_path).convert_with_artifact("# 문서\n", template="보고서")

    assert result.succeeded is True
    assert result.artifact is not None
    assert Path(result.artifact.path) != existing_path
    assert existing_path.read_bytes() == b"pre-existing-collision-content"
