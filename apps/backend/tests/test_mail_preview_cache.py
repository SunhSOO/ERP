"""POP3 preview cache regression tests for HiworksMailAdapter list cache behavior."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from lep.modules.mail.domain.entities import Classification, MailAttachment, MailMessage
from lep.modules.mail.infrastructure import hiworks_pop3
from lep.modules.mail.infrastructure.hiworks_pop3 import HiworksMailAdapter


def _message(*, message_id: str = "uid-1", sender: str = "홍길동") -> MailMessage:
    return MailMessage(
        id=message_id,
        sender_name=sender,
        sender_org="example.invalid",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
        subject="subject",
        body="body",
        classification=Classification.UNCLASSIFIED,
        project_id=None,
        intent=None,
        confidence=None,
    )


def _message_with_attachment(*, message_id: str = "uid-1") -> MailMessage:
    return MailMessage(
        id=message_id,
        sender_name="홍길동",
        sender_org="example.invalid",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
        subject="subject",
        body="body",
        classification=Classification.UNCLASSIFIED,
        project_id=None,
        intent=None,
        confidence=None,
        attachments=(MailAttachment("a.txt", "text/plain", 10, 0),),
    )


class _TestAdapter(HiworksMailAdapter):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        limit: int,
        fetch: Callable[[], list[MailMessage]],
        fetch_full: Callable[[str], MailMessage | None] | None = None,
    ) -> None:
        super().__init__(host=host, port=port, user=user, password=password, limit=limit)
        self.fetch = fetch
        self.fetch_full = fetch_full

    def _fetch(self) -> list[MailMessage]:
        return self.fetch()

    def _fetch_full(self, uid: str) -> MailMessage | None:
        if self.fetch_full is None:
            return super()._fetch_full(uid)
        return self.fetch_full(uid)


def _adapter(
    *,
    fetch: Callable[[], list[MailMessage]],
    fetch_full: Callable[[str], MailMessage | None] | None = None,
) -> HiworksMailAdapter:
    return _TestAdapter(
        host="localhost",
        port=995,
        user="test@example.invalid",
        password="secret",
        limit=20,
        fetch=fetch,
        fetch_full=fetch_full,
    )


def test_list_recent_reuses_single_fetch_on_repeated_calls() -> None:
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        return [_message(message_id="uid-1")]

    adapter = _adapter(fetch=_fetch)
    first = adapter.list_recent()
    second = adapter.list_recent()

    assert calls == 1
    assert first == second


def test_list_recent_concurrent_calls_use_single_inflight_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start = threading.Event()
    inside = threading.Event()
    lock = threading.Lock()
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        with lock:
            calls += 1
        inside.set()
        start.wait()
        return [_message(message_id="uid-1")]

    adapter = _adapter(fetch=_fetch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(adapter.list_recent)
        assert inside.wait(1.0)
        second = pool.submit(adapter.list_recent)
        start.set()
        results = [first.result(timeout=2.0), second.result(timeout=2.0)]

    assert calls == 1
    assert results[0] == results[1]


def test_list_recent_discards_stale_fetch_result_if_identity_changes_mid_fetch() -> None:
    start = threading.Event()
    go = threading.Event()
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        if calls == 1:
            start.set()
            go.wait(timeout=1.0)
            return [_message(message_id="uid-old")]
        return [_message(message_id="uid-new")]

    adapter = _adapter(fetch=_fetch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(adapter.list_recent)
        assert start.wait(1.0)
        adapter.user = "changed@example.invalid"
        go.set()
        result = future.result(timeout=2.0)

    assert calls == 2
    assert result == [_message(message_id="uid-new")]
    assert adapter.list_recent() == [_message(message_id="uid-new")]


class _FakeMonotonic:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_list_recent_refreshes_after_ttl_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    clock = _FakeMonotonic()
    monkeypatch.setattr(hiworks_pop3, "monotonic", clock)

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        return [_message(message_id=f"uid-{calls}")]

    adapter = _adapter(fetch=_fetch)
    first = adapter.list_recent()
    second = adapter.list_recent()
    clock.advance(hiworks_pop3.PREVIEW_CACHE_TTL_SECONDS + 1)
    third = adapter.list_recent()

    assert first == [_message(message_id="uid-1")]
    assert second == first
    assert third == [_message(message_id="uid-2")]
    assert calls == 2


def test_list_recent_ttl_starts_after_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    clock = _FakeMonotonic()
    monkeypatch.setattr(hiworks_pop3, "monotonic", clock)

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        if calls == 1:
            # Simulate non-trivial fetch latency.
            clock.advance(10.0)
        return [_message(message_id=f"uid-{calls}")]

    adapter = _adapter(fetch=_fetch)
    assert adapter.list_recent() == [_message(message_id="uid-1")]

    # If TTL is stamped before fetch, this call would refetch; stamping after
    # fetch should keep the cache valid.
    clock.advance(hiworks_pop3.PREVIEW_CACHE_TTL_SECONDS - 1)
    assert adapter.list_recent() == [_message(message_id="uid-1")]
    assert calls == 1


def test_failed_refresh_does_not_return_expired_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return [_message(message_id="uid-1")]
        if calls == 2:
            raise RuntimeError("temporary")
        return [_message(message_id="uid-2")]

    adapter = _adapter(fetch=_fetch)
    clock = _FakeMonotonic()
    monkeypatch.setattr(hiworks_pop3, "monotonic", clock)
    assert adapter.list_recent() == [_message(message_id="uid-1")]

    clock.advance(hiworks_pop3.PREVIEW_CACHE_TTL_SECONDS + 1)

    with pytest.raises(RuntimeError):
        adapter.list_recent()

    clock.advance(1.0)
    assert adapter.list_recent() == [_message(message_id="uid-2")]
    assert calls == 3


def test_cache_isolated_per_adapter_instance() -> None:
    calls = {"a": 0, "b": 0}

    def _fetch_a() -> list[MailMessage]:
        calls["a"] += 1
        return [_message(message_id="uid-a")]

    def _fetch_b() -> list[MailMessage]:
        calls["b"] += 1
        return [_message(message_id="uid-b")]

    adapter_a = _adapter(fetch=_fetch_a)
    adapter_b = _adapter(fetch=_fetch_b)

    assert adapter_a.list_recent() == [_message(message_id="uid-a")]
    assert adapter_a.list_recent() == [_message(message_id="uid-a")]
    assert adapter_b.list_recent() == [_message(message_id="uid-b")]
    assert adapter_b.list_recent() == [_message(message_id="uid-b")]
    assert calls == {"a": 1, "b": 1}


def test_list_recent_failure_does_not_cache_and_retries() -> None:
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary")
        return [_message(message_id="uid-2")]

    adapter = _adapter(fetch=_fetch)
    with pytest.raises(RuntimeError):
        adapter.list_recent()

    messages = adapter.list_recent()

    assert calls == 2
    assert messages == [_message(message_id="uid-2")]


def test_list_recent_empty_payload_is_cached() -> None:
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        return []

    adapter = _adapter(fetch=_fetch)
    assert adapter.list_recent() == []
    assert adapter.list_recent() == []
    assert calls == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda adapter: setattr(adapter, "host", "other.example.invalid"),
        lambda adapter: setattr(adapter, "port", 119),
        lambda adapter: setattr(adapter, "user", "other@example.invalid"),
        lambda adapter: setattr(adapter, "password", "other-secret"),
        lambda adapter: setattr(adapter, "limit", 10),
        lambda adapter: setattr(adapter, "domains", {"alt.invalid": "project-id"}),
    ],
)
def test_list_recent_refreshes_on_adapter_identity_change(
    mutate: Callable[[HiworksMailAdapter], None],
) -> None:
    calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal calls
        calls += 1
        return [_message(message_id=f"uid-{calls}")]

    adapter = _adapter(fetch=_fetch)
    adapter.list_recent()
    mutate(adapter)
    adapter.list_recent()

    assert calls == 2


def test_mutation_isolated_between_calls_including_nested_attachments() -> None:
    source = _message_with_attachment(message_id="uid-1")

    def _fetch() -> list[MailMessage]:
        return [source]

    adapter = _adapter(fetch=_fetch)
    first = adapter.list_recent()

    # Caller mutation attempt on attachment should never change the cached snapshot.
    first_message = first[0]
    first_attachment = first_message.attachments[0]
    object.__setattr__(first_attachment, "filename", "mutated.txt")

    second = adapter.list_recent()
    assert second[0].attachments[0].filename == "a.txt"


def test_overlay_is_applied_fresh_each_list_call() -> None:
    adapter = _adapter(fetch=lambda: [_message(message_id="uid-1")])
    first = adapter.list_recent()[0]
    assert first.handled is False

    updated = replace(first, handled=True, note_id="note-1")
    adapter.replace_message(updated)
    second = adapter.list_recent()[0]
    assert second.handled is True
    assert second.note_id == "note-1"

    refreshed = replace(second, handled=False, note_id=None)
    adapter.replace_message(refreshed)
    third = adapter.list_recent()[0]
    assert third.handled is False
    assert third.note_id is None


def test_get_message_uses_full_fetch_and_bypasses_list_cache() -> None:
    list_calls = 0
    full_calls = 0

    def _fetch() -> list[MailMessage]:
        nonlocal list_calls
        list_calls += 1
        return [_message(message_id="uid-1")]

    def _fetch_full(message_id: str) -> MailMessage | None:
        nonlocal full_calls
        full_calls += 1
        assert message_id == "uid-1"
        return _message(message_id="uid-1")

    adapter = _adapter(fetch=_fetch, fetch_full=_fetch_full)
    assert adapter.list_recent() == [_message(message_id="uid-1")]
    adapter.get_message("uid-1")
    adapter.get_message("uid-1")

    assert list_calls == 1
    assert full_calls == 2
