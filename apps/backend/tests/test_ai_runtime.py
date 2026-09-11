"""Tests for the read-only LLM runtime status (WP-PKD-033A).

Every adapter test drives ``OllamaLlmRuntimeAdapter`` with ``httpx.MockTransport``.
None reach a real server — ``AGENTS.md`` 14절. The fixture adapter takes no
transport at all because it never opens a connection.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from lep.modules.integrations.domain.entities import LinkHealth, LlmRuntimeStatus
from lep.modules.integrations.infrastructure.fixtures import FixtureIntegrationAdapter
from lep.modules.integrations.infrastructure.llm_runtime import (
    FixtureLlmRuntimeAdapter,
    OllamaLlmRuntimeAdapter,
)

BASE_URL = "http://ollama.invalid:11434/v1"


def _adapter(handler: Any) -> OllamaLlmRuntimeAdapter:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return OllamaLlmRuntimeAdapter(base_url=BASE_URL, client=client)


# ── fixture adapter ──────────────────────────────────────────────────────


def test_fixture_reports_fixture_when_no_real_adapter_is_selected() -> None:
    snapshot = FixtureLlmRuntimeAdapter().snapshot()

    assert snapshot.status is LlmRuntimeStatus.FIXTURE
    assert snapshot.gpu_usage_percent is None
    assert snapshot.active_model_count is None
    assert snapshot.available_model_names == ()
    assert snapshot.running_model_names == ()


def test_fixture_reports_not_configured_with_the_real_reason() -> None:
    snapshot = FixtureLlmRuntimeAdapter(
        unavailable_reason="LEP_ADAPTER_LLM=ollama로 설정됐지만 LEP_LLM_MODEL이 없습니다."
    ).snapshot()

    assert snapshot.status is LlmRuntimeStatus.NOT_CONFIGURED
    assert "LEP_LLM_MODEL" in snapshot.detail


# ── ollama adapter: both probes answer ──────────────────────────────────


def test_installed_and_loaded_models_are_reported_and_connected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}, {"id": "llama3:8b"}]})
        assert request.url.path == "/api/ps"
        return httpx.Response(200, json={"models": [{"name": "qwen3:8b"}]})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.CONNECTED
    assert snapshot.available_model_names == ("qwen3:8b", "llama3:8b")
    assert snapshot.running_model_names == ("qwen3:8b",)
    # 적재된 모델만 센다. 설치됐지만 적재되지 않은 llama3:8b는 세지 않는다.
    assert snapshot.active_model_count == 1
    assert snapshot.gpu_usage_percent is None


def test_no_loaded_models_is_zero_not_unmeasured() -> None:
    """/ps가 정상 응답했고 목록이 비어 있으면 그것은 실측된 0이다."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}]})
        return httpx.Response(200, json={"models": []})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.CONNECTED
    assert snapshot.active_model_count == 0
    assert snapshot.running_model_names == ()


# ── ollama adapter: /ps unavailable, /models fine ───────────────────────


def test_ps_unavailable_with_models_working_is_degraded_not_zero() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}]})
        return httpx.Response(500, json={"error": "internal"})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.DEGRADED
    assert snapshot.available_model_names == ("qwen3:8b",)
    assert snapshot.running_model_names == ()
    # 측정하지 못했다. 0으로 지어내지 않는다.
    assert snapshot.active_model_count is None
    assert snapshot.gpu_usage_percent is None


def test_degraded_detail_does_not_carry_the_raw_remote_error_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(
            500, json={"error": "SECRET_INTERNAL_STACK_TRACE something-private"}
        )

    snapshot = _adapter(handler).snapshot()

    assert "SECRET_INTERNAL_STACK_TRACE" not in snapshot.detail
    assert "HTTP 500" in snapshot.detail


# ── ollama adapter: /models itself fails ────────────────────────────────


def test_timeout_yields_unavailable_without_raw_error_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("connect timed out to 10.0.0.1:11434", request=request)

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert snapshot.gpu_usage_percent is None
    assert snapshot.active_model_count is None
    assert snapshot.available_model_names == ()
    assert snapshot.running_model_names == ()
    assert "10.0.0.1" not in snapshot.detail
    assert "시간 초과" in snapshot.detail


def test_malformed_body_yields_unavailable_without_raw_error_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all {{{")

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert "not json at all" not in snapshot.detail


def test_unexpected_json_shape_is_treated_as_a_failed_probe() -> None:
    """형식은 유효한 JSON이지만 계약한 모양이 아니다. 모델이 있는 척하지 않는다."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert snapshot.available_model_names == ()


# ── malformed rows: one bad row fails the whole probe, not just that row ──


def test_a_malformed_model_row_fails_the_whole_installed_probe() -> None:
    """하나가 이상하면 전체를 신뢰하지 않는다. 나머지만 조용히 골라내지 않는다."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(
                200, json={"data": [{"id": "qwen3:8b"}, {"id": 12345}]}
            )
        return httpx.Response(200, json={"models": []})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert snapshot.available_model_names == ()


def test_a_blank_model_id_fails_the_whole_installed_probe() -> None:
    """빈 이름은 유효한 모델이 아니다. 화면에 이름 없는 항목으로 새지 않는다."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}, {"id": "  "}]})
        return httpx.Response(200, json={"models": []})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert snapshot.available_model_names == ()


def test_a_malformed_running_row_fails_the_running_probe_not_zero() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}]})
        return httpx.Response(200, json={"models": [{"name": ""}]})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.DEGRADED
    assert snapshot.running_model_names == ()
    assert snapshot.active_model_count is None


def test_a_mix_of_valid_and_invalid_model_rows_is_still_a_failed_probe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(
                200,
                json={"data": [{"id": "qwen3:8b"}, {"not_id": "llama3:8b"}, {"id": "gpt-oss"}]},
            )
        return httpx.Response(200, json={"models": []})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert snapshot.available_model_names == ()


def test_a_legitimately_empty_model_list_is_a_real_zero_not_a_failure() -> None:
    """빈 배열 자체는 유효한 응답이다. 형식이 이상한 것과 구분해야 한다."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"models": []})

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.CONNECTED
    assert snapshot.available_model_names == ()
    assert snapshot.active_model_count == 0


# ── malformed configured base URL ───────────────────────────────────────


def test_malformed_configured_url_is_not_configured_without_leaking_it() -> None:
    """설정값 자체가 URL이 아니면 요청을 시도하지 않고 안전하게 실패한다."""

    adapter = OllamaLlmRuntimeAdapter(base_url="not a url at all :::: secret-token")

    snapshot = adapter.snapshot()

    assert snapshot.status is LlmRuntimeStatus.NOT_CONFIGURED
    assert "secret-token" not in snapshot.detail
    assert "not a url at all" not in snapshot.detail


def test_non_http_scheme_is_not_configured_not_attempted() -> None:
    adapter = OllamaLlmRuntimeAdapter(base_url="file:///etc/passwd")

    snapshot = adapter.snapshot()

    assert snapshot.status is LlmRuntimeStatus.NOT_CONFIGURED
    assert snapshot.available_model_names == ()


def test_invalid_url_raised_by_the_transport_is_handled_not_a_500() -> None:
    """스킴은 http(s)로 통과하지만 하위 계층에서 InvalidURL이 날 수도 있다.

    ``httpx.InvalidURL``은 ``httpx.HTTPError``의 하위 클래스가 아니므로 별도로
    잡아야 한다. 잡지 못하면 이 예외가 그대로 올라가 500이 된다.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.InvalidURL("invalid URL for transport")

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert "invalid URL for transport" not in snapshot.detail


def test_http_error_status_yields_unavailable_without_raw_error_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="detailed internal path leaked here")

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert "detailed internal path" not in snapshot.detail
    assert "HTTP 404" in snapshot.detail


def test_connection_error_yields_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    snapshot = _adapter(handler).snapshot()

    assert snapshot.status is LlmRuntimeStatus.UNAVAILABLE
    assert "connection refused" not in snapshot.detail


# ── API surface ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_integration_service_cache() -> Iterator[None]:
    """``get_integration_service`` is process-cached; each test starts clean."""

    from lep.modules.integrations.public import get_integration_service

    get_integration_service.cache_clear()
    yield
    get_integration_service.cache_clear()


def test_ai_server_requires_authentication(client: Any) -> None:
    response = client.get("/api/v1/ai/server")

    assert response.status_code == 401


def test_ai_server_serializes_nullable_fields_honestly_on_the_fixture(
    client: Any, signed_up: dict[str, str]
) -> None:
    response = client.get("/api/v1/ai/server")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "fixture"
    assert data["gpu_usage_percent"] is None
    assert data["active_model_count"] is None
    assert data["available_model_names"] == []
    assert data["running_model_names"] == []


def test_llm_credential_reflects_the_runtime_probe_not_a_hardcoded_value(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    response = client.get(f"/api/v1/projects/{project['id']}/integrations")

    assert response.status_code == 200, response.text
    rows = {row["kind"]: row for row in response.json()["data"]}
    assert rows["llm"]["health"] == "not_configured"
    assert "설정되지 않았습니다" in rows["llm"]["detail"]
    assert rows["llm"]["missing_input"] is not None


def test_restart_always_rejects_with_state_conflict(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    response = client.post(f"/api/v1/projects/{project['id']}/ai/restart")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "STATE_CONFLICT"


def test_restart_checks_the_project_first(client: Any, signed_up: dict[str, str]) -> None:
    response = client.post("/api/v1/projects/does-not-exist/ai/restart")

    assert response.status_code == 404


# ── routes that make a blocking httpx call must run in the threadpool ────


def test_ai_server_route_is_sync_so_fastapi_uses_the_threadpool() -> None:
    """``get_server`` calls ``httpx`` synchronously. As ``async def`` that
    blocking call would stall the whole event loop; FastAPI only offloads
    plain ``def`` routes to its threadpool."""

    from lep.modules.integrations.api.routes import get_server

    assert not inspect.iscoroutinefunction(get_server)


def test_list_credentials_route_is_sync_so_fastapi_uses_the_threadpool() -> None:
    from lep.modules.integrations.api.routes import list_credentials

    assert not inspect.iscoroutinefunction(list_credentials)


# ── backward compatibility: pre-WP-PKD-033A two-arg credentials() call ───


def test_fixture_adapter_credentials_still_works_with_two_positional_args() -> None:
    """Direct callers that predate the LLM runtime port supplied only
    ``(project_id, converter)``. The third argument must stay optional with a
    safe, honestly-not-configured default, never a fabricated connected row."""

    rows = FixtureIntegrationAdapter().credentials("prj-daon", ("Kordoc", "1.0"))

    llm_row = next(row for row in rows if row.kind == "llm")
    assert llm_row.health is LinkHealth.NOT_CONFIGURED
    assert llm_row.missing_input is not None
