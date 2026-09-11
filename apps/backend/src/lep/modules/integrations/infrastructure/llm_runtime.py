"""Local LLM runtime status adapters (WP-PKD-033A, ADR-018).

Two adapters for ``LlmRuntimePort``:

``FixtureLlmRuntimeAdapter``
    No network. Reports honestly that nothing is configured, or why the real
    adapter could not be selected. ``AGENTS.md`` 14절 forbids tests reaching
    real services; this is what every test outside this module's own real-
    adapter tests uses.

``OllamaLlmRuntimeAdapter``
    Reads the actually-selected server through two read-only calls: the
    OpenAI-compatible ``GET /models`` (installed models) and Ollama's native
    ``GET /api/ps`` (currently loaded models). Neither call can start
    inference, pull, load, unload or restart a model — there is no such call
    in this file. GPU utilization is not returned by either endpoint, so it is
    never reported; a fabricated zero would be a stronger claim than the probe
    can support.

    ``client`` is an injection point so tests can supply an
    ``httpx.MockTransport`` instead of reaching a real server.
"""

from __future__ import annotations

import httpx

from ..domain.entities import LlmRuntimeSnapshot, LlmRuntimeStatus

#: Short and bounded: this is a status read on a settings page, not an
#: inference call. A slow or hung server should not hang the page.
REQUEST_TIMEOUT_SECONDS = 5.0


def _ollama_root(base_url: str) -> str:
    """``http://ollama:11434/v1`` → ``http://ollama:11434``.

    ``/api/ps`` is Ollama-native, not part of the OpenAI-compatible surface
    ``LEP_LLM_BASE_URL`` points at.
    """

    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        return trimmed[: -len("/v1")]
    return trimmed


def _parse_models(body: object) -> list[str] | None:
    """OpenAI-compatible ``/models`` shape: ``{"data": [{"id": "..."}, ...]}``.

    Any row that is not a dict, is missing ``id``, or has a blank/non-string
    ``id`` makes the whole probe untrustworthy — it is reported as a failed
    probe (``None``), not as a shorter list. A legitimate empty ``data`` array
    is a real, reportable zero.
    """

    if not isinstance(body, dict):
        return None
    data = body.get("data")
    if not isinstance(data, list):
        return None
    names: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            return None
        names.append(item_id)
    return names


def _parse_running(body: object) -> list[str] | None:
    """Ollama ``/api/ps`` shape: ``{"models": [{"name": "..."}, ...]}``.

    Same all-or-nothing rule as ``_parse_models``: one malformed or blank row
    fails the whole probe rather than silently shrinking the count.
    """

    if not isinstance(body, dict):
        return None
    models = body.get("models")
    if not isinstance(models, list):
        return None
    names: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        names.append(name)
    return names


class FixtureLlmRuntimeAdapter:
    """No network. Fixture or not-configured, reported honestly."""

    def __init__(self, *, unavailable_reason: str | None = None) -> None:
        self._unavailable_reason = unavailable_reason

    def snapshot(self) -> LlmRuntimeSnapshot:
        if self._unavailable_reason:
            status = LlmRuntimeStatus.NOT_CONFIGURED
            detail = self._unavailable_reason
        else:
            status = LlmRuntimeStatus.FIXTURE
            detail = "실제 추론 서버가 설정되지 않았습니다."
        return LlmRuntimeSnapshot(
            status=status,
            detail=detail,
            gpu_usage_percent=None,
            active_model_count=None,
            available_model_names=(),
            running_model_names=(),
        )


class OllamaLlmRuntimeAdapter:
    """Reads the configured OpenAI-compatible / Ollama server's status only."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._root = _ollama_root(base_url)
        self._timeout = timeout
        self._client = client
        #: Checked once, before any request. A base URL that isn't http(s)
        #: is a configuration error, not something worth handing to httpx —
        #: and never worth echoing back to the caller verbatim.
        try:
            scheme = httpx.URL(self._base_url).scheme
        except httpx.InvalidURL:
            scheme = ""
        self._configured = scheme in ("http", "https")

    def _fetch(self, client: httpx.Client, url: str) -> tuple[object | None, str | None]:
        """Return ``(body, error_category)``. Never the remote's raw error text."""

        try:
            response = client.get(url, timeout=self._timeout)
        except httpx.TimeoutException:
            return None, "시간 초과"
        except httpx.InvalidURL:
            # Not an ``httpx.HTTPError`` subclass, so it needs its own branch.
            # A malformed ``LEP_LLM_BASE_URL`` is a configuration problem, not
            # a network one, but it must still fail closed, not with a 500.
            return None, "잘못된 서버 주소 설정"
        except httpx.HTTPError:
            return None, "연결 실패"
        if response.status_code >= 400:
            return None, f"HTTP {response.status_code}"
        try:
            return response.json(), None
        except ValueError:
            return None, "응답 형식 오류"

    def snapshot(self) -> LlmRuntimeSnapshot:
        if not self._configured:
            return LlmRuntimeSnapshot(
                status=LlmRuntimeStatus.NOT_CONFIGURED,
                detail="추론 서버 주소 설정이 올바르지 않습니다 (http 또는 https만 지원).",
                gpu_usage_percent=None,
                active_model_count=None,
                available_model_names=(),
                running_model_names=(),
            )

        owns_client = self._client is None
        client = self._client or httpx.Client()
        try:
            models_body, models_error = self._fetch(client, f"{self._base_url}/models")
            ps_body, ps_error = self._fetch(client, f"{self._root}/api/ps")
        finally:
            if owns_client:
                client.close()

        available = _parse_models(models_body) if models_error is None else None
        if available is None:
            reason = models_error or "응답 형식 오류"
            return LlmRuntimeSnapshot(
                status=LlmRuntimeStatus.UNAVAILABLE,
                detail=f"설치된 모델 목록을 확인하지 못했습니다: {reason}",
                gpu_usage_percent=None,
                active_model_count=None,
                available_model_names=(),
                running_model_names=(),
            )

        running = _parse_running(ps_body) if ps_error is None else None
        if running is None:
            reason = ps_error or "응답 형식 오류"
            return LlmRuntimeSnapshot(
                status=LlmRuntimeStatus.DEGRADED,
                detail=f"실행 중인 모델을 확인하지 못했습니다: {reason}",
                gpu_usage_percent=None,
                active_model_count=None,
                available_model_names=tuple(available),
                running_model_names=(),
            )

        return LlmRuntimeSnapshot(
            status=LlmRuntimeStatus.CONNECTED,
            detail="추론 서버에 연결됐습니다.",
            gpu_usage_percent=None,
            active_model_count=len(running),
            available_model_names=tuple(available),
            running_model_names=tuple(running),
        )
