"""WP-PKD-MAIL-APPROVAL-20260909 — 메일 승인 워크플로 회귀 테스트.

ADR-021: 자동 분류 결과는 추천일 뿐이다. 사람이 명시적으로 승인해야만
``project_id``가 확정되고, 승인한 첨부만 문서 드라이브에 연결된다. 기존
overlay(재분류용 메모리 상태)는 승인의 대체물이 아니다.

``FakeMailAdapter``는 새 ``MailPort`` 계약(``mailbox_key``/``list_recent``/
``get_message``/``fetch_attachment``)을 구현하는 메모리 어댑터다. 외부 메일
서버를 부르지 않는다. 첨부 등록은 실제 ``documents`` 공개 서비스를 그대로
통과시킨다 — 등록 실패/롤백을 가리는 mock 성공을 쓰지 않는다.

픽스처 데이터는 전부 ``.invalid`` 도메인의 합성 값이다.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import urllib.parse
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select

from lep.common.db import session_scope
from lep.common.problems import ProblemError
from lep.modules.iam.infrastructure.models import UserRow
from lep.modules.mail.api.routes import _transport_message_id
from lep.modules.mail.domain.entities import (
    Classification,
    MailAttachment,
    MailMessage,
)
from lep.modules.mail.domain.ports import MailPort
from lep.modules.mail.infrastructure.hiworks_pop3 import HiworksMailAdapter
from lep.modules.mail.infrastructure.models import (
    MailAuditRow,
    MailIdempotencyRow,
    MailReviewAttachmentRow,
    MailReviewRow,
)

# ── 합성 데이터 헬퍼 ─────────────────────────────────────────────────────

_PDF_BYTES = b"%PDF-1.4 fake pdf bytes for a test fixture only"
_HWPX_BYTES = b"PK\x03\x04 fake hwpx bytes for a test fixture only"


@pytest.mark.parametrize("token", ["AA", "", "////", "A" + "A" * 400])
def test_encoded_uidl_rejects_malformed_or_unsafe_tokens(token: str) -> None:
    with pytest.raises(ProblemError):
        _transport_message_id(token, "base64url")


def test_encoded_uidl_restores_delimiters_and_preserves_raw_identity() -> None:
    raw = "uid/with?delim#hash"
    token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    assert _transport_message_id(token, "base64url") == raw


def test_encoded_uidl_http_detail_approve_download_preserves_raw_identity(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64

    raw = "uid/with?delim#hash"
    token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    adapter = _adapter_with_attachment(message_id=raw)
    _install_fake_mail_service(monkeypatch, adapter)

    detail = client.get(f"/api/v1/mail/{token}?id_encoding=base64url")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == raw
    body = {"project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}]}
    approved = client.post(
        f"/api/v1/mail/{token}/approve?id_encoding=base64url", json=body,
        headers={"Idempotency-Key": "encoded-uidl-approve"},
    )
    assert approved.status_code == 200, approved.text
    retry = client.post(
        f"/api/v1/mail/{token}/approve?id_encoding=base64url", json=body,
        headers={"Idempotency-Key": "encoded-uidl-approve"},
    )
    assert retry.status_code == 200
    downloaded = client.get(
        f"/api/v1/mail/{token}/attachments/0?id_encoding=base64url"
        f"&linked_file_id={approved.json()['data']['attachments'][0]['linked_file_id']}"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == _PDF_BYTES
    with session_scope() as db:
        rows = db.scalars(select(MailReviewRow).where(MailReviewRow.message_id == raw)).all()
        assert len(rows) == 1


@pytest.mark.parametrize(
    "token",
    [base64.urlsafe_b64encode(b"x" * 256).decode().rstrip("="), "AA", "__"],
)
def test_encoded_uidl_http_rejects_malformed_tokens(
    client: Any, signed_up: dict[str, str], token: str,
) -> None:
    response = client.get(f"/api/v1/mail/{token}?id_encoding=base64url")
    assert response.status_code == 422


def _mailbox_key(label: str) -> str:
    """documents.public.register_mail_attachments는 mailbox_key를 SHA-256
    64자 16진수로만 받는다(ADR-021 계약). 테스트 픽스처도 실제 어댑터처럼
    해시값을 쓴다 — 임의 문자열은 등록 단계에서 422로 막힌다."""

    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _attachment(part_index: int, filename: str = "약품_소독_공정.pdf") -> MailAttachment:
    return MailAttachment(
        filename=filename, content_type="application/pdf",
        size_bytes=len(_PDF_BYTES), part_index=part_index,
    )


def _pending_message(
    *,
    message_id: str = "uid-approve-1",
    attachments: tuple[MailAttachment, ...] = (),
    suggested_project_id: str | None = None,
) -> MailMessage:
    """승인 전 상태. ADR-021에 따라 project_id는 아직 정해지지 않는다."""

    return MailMessage(
        id=message_id,
        sender_name="이서영",
        sender_org="daon-corp.invalid",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
        subject="자료 공유",
        body="첨부드립니다.",
        classification=Classification.UNCLASSIFIED,
        project_id=None,
        intent=None,
        confidence=None,
        attachments=attachments,
        suggested_project_id=suggested_project_id,
    )


@dataclass
class FakeMailAdapter:
    """API 회귀 테스트용 메모리 ``MailPort``. 외부 메일 서버를 부르지 않는다."""

    messages: dict[str, MailMessage] = field(default_factory=dict)
    attachment_bytes: dict[tuple[str, int], bytes] = field(default_factory=dict)
    key: str = field(default_factory=lambda: _mailbox_key("fixture-mailbox-a"))
    list_recent_calls: int = 0

    @property
    def mailbox_key(self) -> str:
        return self.key

    def list_recent(self) -> list[MailMessage]:
        self.list_recent_calls += 1
        return list(self.messages.values())

    def get_message(self, message_id: str) -> MailMessage | None:
        return self.messages.get(message_id)

    def fetch_attachment(
        self, message_id: str, part_index: int
    ) -> tuple[str, str, bytes] | None:
        data = self.attachment_bytes.get((message_id, part_index))
        message = self.messages.get(message_id)
        if data is None or message is None:
            return None
        att = next((a for a in message.attachments if a.part_index == part_index), None)
        if att is None:
            return None
        return (att.filename, att.content_type, data)


def _install_fake_mail_service(
    monkeypatch: pytest.MonkeyPatch, adapter: MailPort
) -> None:
    """mail.api.routes.get_mail_service를 fake 어댑터로 바꾼다."""

    import lep.modules.mail.api.routes as mail_routes

    monkeypatch.setattr(mail_routes, "get_mail_service", lambda: adapter)


def _adapter_with_attachment(
    *, message_id: str = "uid-approve-1", part_index: int = 0, payload: bytes = _PDF_BYTES,
    filename: str = "약품_소독_공정.pdf",
) -> FakeMailAdapter:
    attachment = _attachment(part_index, filename)
    message = _pending_message(message_id=message_id, attachments=(attachment,))
    adapter = FakeMailAdapter({message.id: message})
    adapter.attachment_bytes[(message_id, part_index)] = payload
    return adapter


def _second_member(client: Any) -> dict[str, Any]:
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "member@example.invalid", "display_name": "일반 회원",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


# ── 승인 없이는 분류도 없다 ─────────────────────────────────────────────


def test_pending_mail_is_reported_as_unclassified_with_no_project(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=(_attachment(0),))
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    body = client.get(f"/api/v1/mail/{message.id}").json()["data"]

    assert body["project_id"] is None
    assert body["classification"] == "unclassified"
    assert body["suggested_project_id"] is None
    assert body["version"] == 0
    assert body["approved_by"] is None
    assert body["can_review"] is True  # 첫 가입자는 관리자다


def test_non_admin_cannot_view_the_shared_unclassified_queue(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    _second_member(client)

    response = client.get(f"/api/v1/projects/{project['id']}/mail?status=unclassified")

    assert response.status_code == 403


# ── 승인 ─────────────────────────────────────────────────────────────────


def test_approve_endpoint_requires_explicit_call_to_classify(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/v1/mail/{id}/approve 가 있어야 project_id가 확정된다."""

    message = _pending_message(attachments=(_attachment(0),))
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    response = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "approve-key-1"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["classification"] == "project"
    assert data["project_id"] == project["id"]
    assert data["version"] == 1
    assert data["approved_by"] == signed_up["id"]
    assert data["attachments"][0]["linked_file_id"] is None


def test_zero_selected_attachments_is_a_valid_mail_only_approval(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)

    response = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "approve-zero-1"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["attachments"][0]["linked_file_id"] is None


def test_only_selected_attachments_are_linked_via_the_real_documents_service(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """등록은 mock이 아니라 실제 documents.public 경로를 지난다."""

    adapter = FakeMailAdapter(
        {
            "uid-approve-1": _pending_message(
                attachments=(
                    _attachment(0, "보고서.pdf"),
                    _attachment(1, "원본.hwpx"),
                ),
            ),
        }
    )
    adapter.attachment_bytes[("uid-approve-1", 0)] = _PDF_BYTES
    adapter.attachment_bytes[("uid-approve-1", 1)] = _HWPX_BYTES
    _install_fake_mail_service(monkeypatch, adapter)

    response = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "approve-key-2"},
    )

    assert response.status_code == 200, response.text
    by_part = {a["part_index"]: a for a in response.json()["data"]["attachments"]}
    assert by_part[0]["linked_file_id"] is not None
    assert by_part[1]["linked_file_id"] is None


def test_a_member_without_admin_standing_cannot_approve(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """승인은 active admin만. 프로젝트 생성자라 해도 admin이 아니면 안 된다."""

    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    _second_member(client)

    response = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "approve-key-3"},
    )

    assert response.status_code == 403


def test_project_creator_member_can_view_approved_mail_but_not_approve(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """멤버가 만든 프로젝트라도 승인은 admin의 일이고, 승인된 뒤 조회만 된다."""

    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    _second_member(client)
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "회원 프로젝트", "code": "MEMBER-1", "customer_name": "고객사"},
    )
    assert project_response.status_code == 201, project_response.text
    member_project = project_response.json()["data"]

    forbidden = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": member_project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "member-approve-1"},
    )
    assert forbidden.status_code == 403

    # admin이 승인한다.
    client.cookies.clear()
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "correct-horse-battery"},
    )
    assert admin_login.status_code == 200, admin_login.text
    approved = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={
            "project_id": member_project["id"], "expected_version": 0, "attachments": [],
        },
        headers={"Idempotency-Key": "admin-approve-for-member-1"},
    )
    assert approved.status_code == 200, approved.text

    # 이제 멤버(프로젝트 생성자)가 조회는 할 수 있다.
    client.cookies.clear()
    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.invalid", "password": "correct-horse-battery"},
    )
    assert member_login.status_code == 200, member_login.text
    view = client.get(f"/api/v1/mail/{message.id}")
    assert view.status_code == 200, view.text
    assert view.json()["data"]["project_id"] == member_project["id"]
    assert view.json()["data"]["can_review"] is False


def test_without_approval_attachments_stay_unlinked_and_promotion_is_denied(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=(_attachment(0),))
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    body = client.get(f"/api/v1/mail/{message.id}").json()["data"]
    assert body["attachments"][0]["linked_file_id"] is None

    response = client.post(f"/api/v1/mail/{message.id}/promote-to-note")
    assert response.status_code == 409


def test_promoting_to_note_twice_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    setup = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "approve-for-note-1"},
    )
    assert setup.status_code == 200, setup.text

    first = client.post(f"/api/v1/mail/{message.id}/promote-to-note")
    assert first.status_code == 200, first.text

    second = client.post(f"/api/v1/mail/{message.id}/promote-to-note")
    assert second.status_code == 409


# ── CAS / 낙관적 잠금 ──────────────────────────────────────────────────────


def test_stale_expected_version_is_rejected_as_a_conflict(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    response = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 5, "attachments": []},
        headers={"Idempotency-Key": "stale-version-1"},
    )

    assert response.status_code == 409


def test_dismissed_mail_cannot_be_reapproved(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    dismissed = client.post(
        f"/api/v1/mail/{message.id}/dismiss",
        json={"expected_version": 0},
        headers={"Idempotency-Key": "dismiss-1"},
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["data"]["classification"] == "unrelated"

    reapprove = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 1, "attachments": []},
        headers={"Idempotency-Key": "reapprove-after-dismiss-1"},
    )
    assert reapprove.status_code == 409


# ── idempotency ────────────────────────────────────────────────────────────


def test_same_idempotency_key_and_payload_replays_the_original_result(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    request_body = {
        "project_id": project["id"], "expected_version": 0,
        "attachments": [{"part_index": 0, "category": "deliverable"}],
    }

    first = client.post(
        "/api/v1/mail/uid-approve-1/approve", json=request_body,
        headers={"Idempotency-Key": "replay-key-1"},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]

    second = client.post(
        "/api/v1/mail/uid-approve-1/approve", json=request_body,
        headers={"Idempotency-Key": "replay-key-1"},
    )
    assert second.status_code == 200, second.text
    second_data = second.json()["data"]

    assert second_data["version"] == first_data["version"] == 1
    assert second_data["attachments"][0]["linked_file_id"] == first_data["attachments"][0][
        "linked_file_id"
    ]


def test_same_key_with_a_different_payload_is_a_conflict(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    setup = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "conflict-key-1"},
    )
    assert setup.status_code == 200, setup.text
    conflicting = client.post(
        f"/api/v1/mail/{message.id}/dismiss",
        json={"expected_version": 0},
        headers={"Idempotency-Key": "conflict-key-1"},
    )

    assert conflicting.status_code == 409


def test_missing_idempotency_key_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    response = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
    )

    assert response.status_code == 422


# ── 승인 뒤 첨부 추가 (attachments/approve) ─────────────────────────────────


def test_attachments_approve_links_a_file_added_after_the_initial_approval(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FakeMailAdapter(
        {
            "uid-approve-1": _pending_message(
                attachments=(_attachment(0, "보고서.pdf"), _attachment(1, "원본.hwpx")),
            ),
        }
    )
    adapter.attachment_bytes[("uid-approve-1", 0)] = _PDF_BYTES
    adapter.attachment_bytes[("uid-approve-1", 1)] = _HWPX_BYTES
    _install_fake_mail_service(monkeypatch, adapter)

    approved = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "later-approve-base-1"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["version"] == 1

    later = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 1, "attachments": [{"part_index": 1, "category": "source"}]},
        headers={"Idempotency-Key": "later-approve-attach-1"},
    )

    assert later.status_code == 200, later.text
    data = later.json()["data"]
    assert data["version"] == 2
    by_part = {a["part_index"]: a for a in data["attachments"]}
    assert by_part[1]["linked_file_id"] is not None


def test_attachments_approve_rejects_an_already_linked_part_with_a_new_key(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)

    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "already-linked-base-1"},
    )
    assert setup.status_code == 200, setup.text

    conflict = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 1, "attachments": [{"part_index": 0, "category": "source"}]},
        headers={"Idempotency-Key": "already-linked-new-key-1"},
    )

    assert conflict.status_code == 409


def test_attachments_approve_stale_version_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)

    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "stale-attach-base-1"},
    )
    assert setup.status_code == 200, setup.text

    response = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 99, "attachments": [{"part_index": 0, "category": "source"}]},
        headers={"Idempotency-Key": "stale-attach-1"},
    )

    assert response.status_code == 409


def test_attachments_approve_same_key_replay_keeps_original_result_after_version_grows(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FakeMailAdapter(
        {
            "uid-approve-1": _pending_message(
                attachments=(_attachment(0, "보고서.pdf"), _attachment(1, "원본.hwpx")),
            ),
        }
    )
    adapter.attachment_bytes[("uid-approve-1", 0)] = _PDF_BYTES
    adapter.attachment_bytes[("uid-approve-1", 1)] = _HWPX_BYTES
    _install_fake_mail_service(monkeypatch, adapter)

    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "replay-base-1"},
    )
    assert setup.status_code == 200, setup.text
    first = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 1, "attachments": [{"part_index": 0, "category": "source"}]},
        headers={"Idempotency-Key": "replay-attach-1"},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["version"] == 2

    # 다른 커맨드로 버전을 더 올린다.
    version_bump = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 2, "attachments": [{"part_index": 1, "category": "source"}]},
        headers={"Idempotency-Key": "replay-attach-2"},
    )
    assert version_bump.status_code == 200, version_bump.text

    replay = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 1, "attachments": [{"part_index": 0, "category": "source"}]},
        headers={"Idempotency-Key": "replay-attach-1"},
    )
    assert replay.status_code == 200, replay.text
    replay_data = replay.json()["data"]
    assert replay_data["version"] == 2  # 이 커맨드가 끝났을 때의 버전 그대로
    by_part = {a["part_index"]: a for a in replay_data["attachments"]}
    assert by_part[0]["linked_file_id"] is not None
    # part 1은 이 커맨드가 아니라 나중 커맨드가 연결했다 — 재현 결과에는 없어야 한다.
    assert by_part[1]["linked_file_id"] is None


# ── 등록 실패는 승인 전체를 되돌린다 ────────────────────────────────────────


def test_a_documents_registration_conflict_rolls_back_the_whole_approval(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 (mailbox_key, message_id, part_index)가 다른 메타데이터로 이미
    등록돼 있으면 documents가 409를 낸다. 그 실패가 review row/첨부 row/
    idempotency row를 전부 되돌려야 한다 — 메일이 여전히 미분류로 남는다."""

    from lep.common.db import session_scope
    from lep.modules.documents.domain.entities import MailAttachmentLinkInput
    from lep.modules.documents.infrastructure import mail_links

    adapter = _adapter_with_attachment(message_id="uid-rollback-1")
    _install_fake_mail_service(monkeypatch, adapter)

    with session_scope() as db:
        mail_links.register(
            db, project_id=project["id"], mailbox_key=adapter.mailbox_key,
            message_id="uid-rollback-1", actor_id=signed_up["id"],
            attachments=[
                MailAttachmentLinkInput(
                    part_index=0, name="다른이름.pdf", content_type="application/pdf",
                    size_bytes=999, sha256="0" * 64, category="original",
                )
            ],
        )

    response = client.post(
        "/api/v1/mail/uid-rollback-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "rollback-key-1"},
    )

    assert response.status_code == 409

    # 롤백됐으므로 메일은 여전히 미분류다.
    still_pending = client.get("/api/v1/mail/uid-rollback-1").json()["data"]
    assert still_pending["classification"] == "unclassified"
    assert still_pending["version"] == 0


# ── 다운로드: 체크섬·헤더·404 ────────────────────────────────────────────


def test_download_of_a_linked_attachment_verifies_checksum_and_sets_nosniff(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "download-approve-1"},
    )
    assert setup.status_code == 200, setup.text

    response = client.get("/api/v1/mail/uid-approve-1/attachments/0")

    assert response.status_code == 200
    assert response.content == _PDF_BYTES
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-disposition" in response.headers


def test_download_preserves_attachment_filename_and_extension(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RFC5987 filename* with ASCII fallback preserves extension for all browsers."""
    adapter = _adapter_with_attachment(
        message_id="uid-filename-1",
        filename="검토 자료.xlsx",
    )
    _install_fake_mail_service(monkeypatch, adapter)
    setup = client.post(
        "/api/v1/mail/uid-filename-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "filename-approve-1"},
    )
    assert setup.status_code == 200, setup.text

    response = client.get("/api/v1/mail/uid-filename-1/attachments/0")

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert 'filename="attachment.xlsx"' in disposition
    assert "filename*=UTF-8''" in disposition
    assert urllib.parse.quote("검토 자료.xlsx") in disposition


def test_download_detects_source_content_changed_since_approval(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "download-changed-1"},
    )
    assert setup.status_code == 200, setup.text

    # 원본이 승인 시점 이후 바뀌었다고 가정한다.
    adapter.attachment_bytes[("uid-approve-1", 0)] = _PDF_BYTES + b"tampered"

    response = client.get("/api/v1/mail/uid-approve-1/attachments/0")

    assert response.status_code == 409


def test_download_of_a_missing_attachment_part_is_not_found(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    response = client.get(f"/api/v1/mail/{message.id}/attachments/0")

    assert response.status_code == 404


# ── 메일함 격리 ──────────────────────────────────────────────────────────


def test_switching_mailbox_key_cannot_see_the_other_mailbox_review(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UIDL이 같아도 mailbox_key가 다르면 다른 메일이다(ADR-021)."""

    adapter_a = _adapter_with_attachment(message_id="uid-shared")
    adapter_a.key = _mailbox_key("mailbox-a")
    _install_fake_mail_service(monkeypatch, adapter_a)

    approved = client.post(
        "/api/v1/mail/uid-shared/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "isolation-key-1"},
    )
    assert approved.status_code == 200, approved.text

    adapter_b = _adapter_with_attachment(message_id="uid-shared")
    adapter_b.key = _mailbox_key("mailbox-b")
    _install_fake_mail_service(monkeypatch, adapter_b)

    # 다른 메일함에서는 같은 UIDL이 여전히 미분류로 보인다 — 같은 키로도
    # 재사용할 수 없다(actor-scoped, mailbox-scoped 검증).
    view = client.get("/api/v1/mail/uid-shared")
    assert view.status_code == 200
    assert view.json()["data"]["classification"] == "unclassified"
    assert view.json()["data"]["version"] == 0


# ── 원본이 사라져도 승인 목록은 남는다 ──────────────────────────────────────


def test_approved_mail_stays_listed_after_the_source_disappears_from_the_window(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(message_id="uid-window-1", attachments=())
    adapter = FakeMailAdapter({message.id: message})
    _install_fake_mail_service(monkeypatch, adapter)

    approved = client.post(
        "/api/v1/mail/uid-window-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "window-approve-1"},
    )
    assert approved.status_code == 200, approved.text

    # POP3의 읽기 창을 벗어나 더는 원본을 못 찾는 상황을 흉내 낸다.
    adapter.messages.clear()

    listing = client.get(f"/api/v1/projects/{project['id']}/mail?status=project")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["data"]]
    assert "uid-window-1" in ids


# ── 목록/카운트 ─────────────────────────────────────────────────────────


def test_counts_are_zero_for_non_admin_and_populated_for_admin(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    admin_counts = client.get(f"/api/v1/projects/{project['id']}/mail/counts").json()["data"]
    assert admin_counts["unclassified"] == 1

    _second_member(client)
    member_counts = client.get(f"/api/v1/projects/{project['id']}/mail/counts").json()["data"]
    assert member_counts["unclassified"] == 0
    assert member_counts["unrelated"] == 0
    assert member_counts["project"] == 0


def test_list_pagination_reports_total_and_has_more(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    messages = {
        f"uid-page-{i}": dataclasses.replace(
            _pending_message(message_id=f"uid-page-{i}"),
            received_at=datetime(2026, 9, 9, 9, i, tzinfo=UTC),
        )
        for i in range(3)
    }
    _install_fake_mail_service(monkeypatch, FakeMailAdapter(messages))

    page = client.get(f"/api/v1/projects/{project['id']}/mail?status=unclassified&offset=0&limit=2")

    assert page.status_code == 200
    body = page.json()
    assert body["meta"]["total"] == 3
    assert body["meta"]["has_more"] is True
    assert len(body["data"]) == 2


def test_unclassified_mail_includes_suggestions_and_suggested_project_id(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    """Unclassified mail carries suggestions, the top one as suggested_project_id."""
    base_msg = _pending_message(message_id="uid-suggest-1")
    message = dataclasses.replace(
        base_msg,
        subject="다온 M3 검토",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
    )
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    # Get unclassified list; should have suggestions
    response = client.get(f"/api/v1/projects/{project['id']}/mail?status=unclassified")

    assert response.status_code == 200
    mail = response.json()["data"][0]
    assert "suggestions" in mail
    assert isinstance(mail["suggestions"], list)
    assert len(mail["suggestions"]) <= 3
    if mail["suggestions"]:
        assert "project_id" in mail["suggestions"][0]
        assert "project_name" in mail["suggestions"][0]
        assert "confidence" in mail["suggestions"][0]
        assert "reasons" in mail["suggestions"][0]


def test_unclassified_mail_with_project_match_sets_suggested_project_id(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    """HTTP-level: project code/name/customer match produces nonempty suggestions with
    matching project first. Verify suggested_project_id equals top suggestion and
    suggested=yes/no filters apply before pagination."""

    # Create message matching project code, name, and customer
    message = dataclasses.replace(
        _pending_message(message_id="uid-match-1"),
        subject=f"Re: {project['code']} {project['name']} 진행상황",
        body=f"고객사: {project['customer_name']}\n상세 내용 첨부",
        received_at=datetime(2026, 9, 9, 10, 0, tzinfo=UTC),
    )
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    # Test nonempty suggestions with matching project first
    response = client.get(f"/api/v1/projects/{project['id']}/mail?status=unclassified")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    mail = data[0]

    # Verify nonempty suggestions list
    assert mail["suggestions"], "Should have suggestions for matching project/customer"
    assert len(mail["suggestions"]) > 0, "At least one suggestion must exist"

    # Verify top suggestion is the matching project
    top_suggestion = mail["suggestions"][0]
    assert top_suggestion["project_id"] == project["id"], "Top suggestion must match the project"
    assert "project_name" in top_suggestion, "Suggestion must include project_name"
    assert "confidence" in top_suggestion, "Suggestion must include confidence score"
    assert "reasons" in top_suggestion, "Suggestion must include reasoning"
    assert isinstance(top_suggestion["reasons"], list), "Reasons must be a list"

    # Verify suggested_project_id consistency
    assert mail["suggested_project_id"] == project["id"], (
        "suggested_project_id must equal project id"
    )
    assert mail["suggested_project_id"] == top_suggestion["project_id"], "Must match top suggestion"

    # Test suggested=yes filter includes this message before pagination
    response_yes = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=yes"
    )
    assert response_yes.status_code == 200
    yes_data = response_yes.json()["data"]
    assert len(yes_data) == 1, "Message with suggestions must be included"
    assert yes_data[0]["id"] == message.id
    assert yes_data[0]["suggestions"], "Filtered message must have suggestions"

    # Test suggested=no filter excludes this message before pagination
    response_no = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=no"
    )
    assert response_no.status_code == 200
    no_data = response_no.json()["data"]
    assert len(no_data) == 0, "Message with suggestions must be excluded from suggested=no"

    # Test that filtering applies before pagination
    with_suggestions = [
        dataclasses.replace(
            _pending_message(message_id=f"uid-paginate-yes-{i}"),
            subject=f"{project['code']} 문서-{i}",
            received_at=datetime(2026, 9, 9, 9, i, tzinfo=UTC),
        )
        for i in range(3)
    ]
    without_suggestions = [
        dataclasses.replace(
            _pending_message(message_id=f"uid-paginate-no-{i}"),
            subject=f"무관한 주제-{i}",
            received_at=datetime(2026, 9, 9, 9, 10 + i, tzinfo=UTC),
        )
        for i in range(5)
    ]

    all_msgs = {msg.id: msg for msg in [message] + with_suggestions + without_suggestions}
    _install_fake_mail_service(monkeypatch, FakeMailAdapter(all_msgs))

    # Pagination with limit=2 on suggested=yes should return exactly 2 (from the filtered set)
    paginated = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=yes&limit=2&offset=0"
    )
    assert paginated.status_code == 200
    paging_body = paginated.json()
    paging_data = paging_body["data"]
    paging_meta = paging_body["meta"]

    # Filter applied before pagination: verify behavior
    assert len(paging_data) == 2, "Pagination limit should be respected after filtering"
    total_filtered = paging_meta["total"]
    total_all_msgs = len(all_msgs)
    assert total_filtered < total_all_msgs, "Filter must reduce total count"
    assert total_filtered > 2, "More than 2 suggested messages should exist"
    assert paging_meta["has_more"] is True, "Should have more filtered results when limit=2"

    # All returned must have suggestions
    for msg in paging_data:
        assert msg["suggestions"], "All filtered results must have suggestions"


def test_suggested_yes_filter_returns_only_messages_with_suggestions(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    """Filter suggested=yes returns only messages with nonempty suggestions."""
    # Create two messages: one matches project, one doesn't
    matching = dataclasses.replace(
        _pending_message(message_id="uid-has-suggest-1"),
        subject=f"{project['code']} 회의록",
        received_at=datetime(2026, 9, 9, 10, 0, tzinfo=UTC),
    )
    non_matching = dataclasses.replace(
        _pending_message(message_id="uid-no-suggest-1"),
        subject="무관한 주제",
        received_at=datetime(2026, 9, 9, 10, 1, tzinfo=UTC),
    )

    adapter = FakeMailAdapter({matching.id: matching, non_matching.id: non_matching})
    _install_fake_mail_service(monkeypatch, adapter)

    # Get with suggested=yes filter
    response = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=yes"
    )

    assert response.status_code == 200
    data = response.json()["data"]

    # Should only have the matching message
    assert len(data) == 1
    assert data[0]["id"] == matching.id
    assert data[0]["suggestions"]


def test_suggested_no_filter_returns_only_messages_without_suggestions(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    """Filter suggested=no returns only messages with empty suggestions."""
    # Create two messages: one matches project, one doesn't
    matching = dataclasses.replace(
        _pending_message(message_id="uid-has-suggest-2"),
        subject=f"{project['code']} 회의록",
        received_at=datetime(2026, 9, 9, 10, 0, tzinfo=UTC),
    )
    non_matching = dataclasses.replace(
        _pending_message(message_id="uid-no-suggest-2"),
        subject="무관한 주제",
        received_at=datetime(2026, 9, 9, 10, 1, tzinfo=UTC),
    )

    adapter = FakeMailAdapter({matching.id: matching, non_matching.id: non_matching})
    _install_fake_mail_service(monkeypatch, adapter)

    # Get with suggested=no filter
    response = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=no"
    )

    assert response.status_code == 200
    data = response.json()["data"]

    # Should only have the non-matching message
    assert len(data) == 1
    assert data[0]["id"] == non_matching.id
    assert not data[0]["suggestions"]


def test_suggested_filter_applies_before_pagination(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    project: dict[str, Any],
) -> None:
    """Suggested filter applies before pagination, not after."""
    # Create messages: some match project code, some don't
    matching = dataclasses.replace(
        _pending_message(message_id="uid-match-pag"),
        subject=f"{project['code']} 회의록",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
    )
    non_matching = dataclasses.replace(
        _pending_message(message_id="uid-nomatch-pag"),
        subject="완전히 다른 주제입니다",
        body="제목과 본문 모두 무관합니다",
        received_at=datetime(2026, 9, 9, 9, 1, tzinfo=UTC),
    )

    all_msgs = {matching.id: matching, non_matching.id: non_matching}
    adapter = FakeMailAdapter(all_msgs)
    _install_fake_mail_service(monkeypatch, adapter)

    # Get with suggested=yes filter - should only include message with suggestions
    response = client.get(
        f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=yes"
    )

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    meta = body["meta"]

    # Only the matching message should be returned
    assert len(data) >= 1
    assert all(msg["suggestions"] for msg in data)
    # Total should reflect only filtered messages
    assert meta["total"] >= 1
    assert meta["has_more"] is False


# ── overlay는 승인 근거가 아니다 ──────────────────────────────────────────


def test_overlay_replace_never_produces_an_approved_classification() -> None:
    """ADR-021: 발신 도메인 추천과 overlay 재기록은 사람 승인을 대체하지 않는다.

    ``HiworksMailAdapter``의 overlay는 처리 표시(지식화됨 등)를 보관하는
    자리였다. 실제 상태(``classification``/``approved_by``)는 DB 승인
    유스케이스를 거쳐야만 채워진다. overlay에 직접 쓰는 것으로는 안 된다.
    """

    adapter = HiworksMailAdapter(
        host="pop3.invalid", port=995, user="pm@example.invalid",
        password="not-a-real-password", domains={"daon-corp.example": "prj-daon"},
    )
    raw = EmailMessage()
    raw["From"] = "이서영 <lee@daon-corp.example>"
    raw["Subject"] = "자료 공유"
    raw["Date"] = "Mon, 07 Sep 2026 14:20:00 +0900"
    raw.set_content("첨부드립니다.")

    original = adapter._to_message(raw, "uid-overlay-1")
    assert original is not None
    assert original.project_id is None  # ADR-021: 추천일 뿐, 확정 아님
    assert original.suggested_project_id == "prj-daon"

    adapter.replace_message(
        dataclasses.replace(original, classification=Classification.PROJECT)
    )
    overlaid = adapter._with_overlay(original)

    # overlay는 classification을 절대 덧입히지 않는다.
    assert overlaid.classification is Classification.UNCLASSIFIED
    assert overlaid.approved_by is None
    assert overlaid.project_id is None


# ── 인증/권한 회귀 ─────────────────────────────────────────────────────────


def _session_token(client: Any) -> str:
    token = client.cookies.get("lep_session")
    assert token
    return str(token)


def test_unauthenticated_requests_are_rejected(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    assert client.get(f"/api/v1/mail/{message.id}").status_code == 401
    assert (
        client.post(
            f"/api/v1/mail/{message.id}/approve",
            json={"project_id": "any", "expected_version": 0, "attachments": []},
            headers={"Idempotency-Key": "no-auth-1"},
        ).status_code
        == 401
    )


def test_suspended_users_session_is_rejected_at_the_http_layer(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정지된 사용자의 세션 쿠키는 애초에 인증되지 않는다. 실제 사용자가
    아니라, 픽스처 설정을 위해 IAM 테이블을 직접 건드리는 것만 허용된다."""

    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    with session_scope() as db:
        row = db.get(UserRow, signed_up["id"])
        assert row is not None
        row.status = "suspended"

    response = client.get(f"/api/v1/mail/{message.id}")
    assert response.status_code == 401


def test_nonowner_member_cannot_view_approved_mail_detail_or_linked_attachment(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    approved = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "nonowner-setup-1"},
    )
    assert approved.status_code == 200, approved.text

    _second_member(client)  # 다른 프로젝트를 만든 적 없는, 무관한 멤버다.

    detail = client.get("/api/v1/mail/uid-approve-1")
    assert detail.status_code == 403

    download = client.get("/api/v1/mail/uid-approve-1/attachments/0")
    assert download.status_code == 403


def test_owner_member_cannot_download_an_unselected_attachment(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """프로젝트 생성자라도 선택되지 않은(연결 안 된) 첨부는 admin 미리보기
    권한이 없는 한 볼 수 없다 — 조회 권한이 곧 미승인 첨부 접근권은 아니다."""

    adapter = FakeMailAdapter(
        {"uid-approve-1": _pending_message(attachments=(_attachment(0), _attachment(1)))}
    )
    adapter.attachment_bytes[("uid-approve-1", 0)] = _PDF_BYTES
    adapter.attachment_bytes[("uid-approve-1", 1)] = _HWPX_BYTES
    _install_fake_mail_service(monkeypatch, adapter)

    _second_member(client)
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "회원 프로젝트", "code": "OWNER-MEM-1", "customer_name": "고객사"},
    )
    assert project_response.status_code == 201, project_response.text
    member_project = project_response.json()["data"]
    member_token = _session_token(client)

    client.cookies.clear()
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "correct-horse-battery"},
    )
    assert admin_login.status_code == 200, admin_login.text
    approved = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": member_project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "owner-mem-approve-1"},
    )
    assert approved.status_code == 200, approved.text

    client.cookies.clear()
    client.cookies.set("lep_session", member_token)
    unselected = client.get("/api/v1/mail/uid-approve-1/attachments/1")
    # 존재는 확인되지만 admin만 미승인 첨부를 미리 볼 수 있다 — 소유자라 해도
    # 다른 첨부 목록/내용을 흘리지 않도록 404로 감춘다(다른 not_found와 일관).
    assert unselected.status_code == 404


def test_forged_admin_headers_do_not_elevate_a_member(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    _second_member(client)

    response = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={
            "Idempotency-Key": "forged-header-1",
            "X-Admin": "true",
            "X-Acting-User": "pm@example.invalid",
            "X-Role": "admin",
        },
    )
    assert response.status_code == 403


def test_member_cannot_dismiss(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    _second_member(client)

    response = client.post(
        f"/api/v1/mail/{message.id}/dismiss",
        json={"expected_version": 0},
        headers={"Idempotency-Key": "member-dismiss-1"},
    )
    assert response.status_code == 403


# ── 입력 검증 ─────────────────────────────────────────────────────────────


def test_invalid_category_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)

    response = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "not-a-real-category"}],
        },
        headers={"Idempotency-Key": "bad-category-1"},
    )
    assert response.status_code == 422


def test_duplicate_part_index_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)

    response = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [
                {"part_index": 0, "category": "deliverable"},
                {"part_index": 0, "category": "source"},
            ],
        },
        headers={"Idempotency-Key": "dup-part-1"},
    )
    assert response.status_code == 422


def test_attachments_approve_with_an_empty_selection_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    setup = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "empty-additional-base-1"},
    )
    assert setup.status_code == 200, setup.text

    response = client.post(
        "/api/v1/mail/uid-approve-1/attachments/approve",
        json={"expected_version": 1, "attachments": []},
        headers={"Idempotency-Key": "empty-additional-1"},
    )
    assert response.status_code == 422


def test_approving_a_message_the_source_no_longer_has_is_not_found(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({}))

    response = client.post(
        "/api/v1/mail/uid-gone-1/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "source-gone-1"},
    )
    assert response.status_code == 404


def test_a_new_idempotency_key_against_an_already_finalized_mail_is_a_conflict(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    first = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "finalized-first-key-1"},
    )
    assert first.status_code == 200, first.text

    retry_with_new_key = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "finalized-different-key-1"},
    )
    assert retry_with_new_key.status_code == 409


# ── 감사 로그 ───────────────────────────────────────────────────────────────


def test_downloads_write_an_audit_row(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_attachment()
    _install_fake_mail_service(monkeypatch, adapter)
    approved = client.post(
        "/api/v1/mail/uid-approve-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "audit-approve-1"},
    )
    assert approved.status_code == 200, approved.text

    response = client.get("/api/v1/mail/uid-approve-1/attachments/0")
    assert response.status_code == 200

    with session_scope() as db:
        downloads = db.scalar(
            select(func.count()).select_from(MailAuditRow).where(
                MailAuditRow.mailbox_key == adapter.mailbox_key,
                MailAuditRow.message_id == "uid-approve-1",
                MailAuditRow.action == "download",
            )
        )
    assert downloads == 1


# ── linked_file_id 쿼리: 계정 교체·UIDL 재사용 방어 ─────────────────────────


def test_linked_file_id_query_rejects_a_stale_link_from_a_different_mailbox(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계정 A에서 승인한 (UIDL, part)의 linked_file_id로 만든 드라이브 링크가,
    같은 UIDL/part를 재사용하는 계정 B로 설정이 바뀐 뒤에도 그대로 통하면 안
    된다 — query만으로 actor/hash 검증을 우회할 수 없다."""

    adapter_a = _adapter_with_attachment(message_id="uid-switch")
    adapter_a.key = _mailbox_key("switch-mailbox-a")
    _install_fake_mail_service(monkeypatch, adapter_a)
    approved_a = client.post(
        "/api/v1/mail/uid-switch/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "switch-approve-a-1"},
    )
    assert approved_a.status_code == 200, approved_a.text
    link_a = approved_a.json()["data"]["attachments"][0]["linked_file_id"]
    assert link_a is not None

    adapter_b = _adapter_with_attachment(
        message_id="uid-switch", payload=_HWPX_BYTES, filename="다른파일.hwpx",
    )
    adapter_b.key = _mailbox_key("switch-mailbox-b")
    _install_fake_mail_service(monkeypatch, adapter_b)
    approved_b = client.post(
        "/api/v1/mail/uid-switch/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "switch-approve-b-1"},
    )
    assert approved_b.status_code == 200, approved_b.text
    link_b = approved_b.json()["data"]["attachments"][0]["linked_file_id"]
    assert link_b is not None
    assert link_b != link_a

    # 여전히 mailbox B로 설정된 채, mailbox A 시절의 linked_file_id로 요청한다.
    stale = client.get(
        "/api/v1/mail/uid-switch/attachments/0", params={"linked_file_id": link_a}
    )
    assert stale.status_code == 404
    assert stale.content != adapter_b.attachment_bytes[("uid-switch", 0)]

    correct = client.get(
        "/api/v1/mail/uid-switch/attachments/0", params={"linked_file_id": link_b}
    )
    assert correct.status_code == 200
    assert correct.content == adapter_b.attachment_bytes[("uid-switch", 0)]


# ── 성능: counts는 어댑터를 한 번만 부른다 ───────────────────────────────────


def test_counts_calls_the_adapter_at_most_once_per_request(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FakeMailAdapter(
        {f"uid-count-{i}": _pending_message(message_id=f"uid-count-{i}") for i in range(3)}
    )
    _install_fake_mail_service(monkeypatch, adapter)

    response = client.get(f"/api/v1/projects/{project['id']}/mail/counts")

    assert response.status_code == 200
    assert response.json()["data"]["unclassified"] == 3
    assert adapter.list_recent_calls == 1


def test_counts_for_a_project_only_scope_never_touch_the_adapter(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """멤버가 자신의 프로젝트 승인건 개수만 볼 때는 어댑터를 전혀 부르지
    않는다 — 하이웍스 POP3 재조회(약 25초)가 이 경로에 끼어들 이유가 없다."""

    class RaisingAdapter:
        key = _mailbox_key("raising-mailbox")

        @property
        def mailbox_key(self) -> str:
            return self.key

        def list_recent(self) -> list[MailMessage]:
            raise AssertionError("list_recent가 호출되면 안 된다")

        def get_message(self, message_id: str) -> MailMessage | None:
            raise AssertionError("get_message가 호출되면 안 된다")

        def fetch_attachment(
            self, message_id: str, part_index: int
        ) -> tuple[str, str, bytes] | None:
            raise AssertionError("fetch_attachment가 호출되면 안 된다")

    _install_fake_mail_service(monkeypatch, RaisingAdapter())
    _second_member(client)
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "회원 프로젝트", "code": "COUNT-MEM-1", "customer_name": "고객사"},
    )
    assert project_response.status_code == 201, project_response.text
    member_project = project_response.json()["data"]

    response = client.get(f"/api/v1/projects/{member_project['id']}/mail/counts")
    assert response.status_code == 200
    assert response.json()["data"] == {
        "unclassified": 0, "project": 0, "unrelated": 0, "all": 0,
    }


# ── SQLite 롤백: 첫 SAVEPOINT가 outer rollback을 이겨 먹지 않는다 ────────────


def test_registration_failure_leaves_no_rows_behind_in_any_mail_table(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """documents 등록 실패로 전체 승인이 롤백되면, 실제 SQLite에 review/첨부/
    idempotency/audit 행이 단 하나도 남지 않는다 — mock으로 가려진 성공이
    아니라 진짜 트랜잭션 경계를 확인한다."""

    from lep.modules.documents.domain.entities import MailAttachmentLinkInput
    from lep.modules.documents.infrastructure import mail_links

    adapter = _adapter_with_attachment(message_id="uid-rollback-2")
    _install_fake_mail_service(monkeypatch, adapter)

    with session_scope() as db:
        mail_links.register(
            db, project_id=project["id"], mailbox_key=adapter.mailbox_key,
            message_id="uid-rollback-2", actor_id=signed_up["id"],
            attachments=[
                MailAttachmentLinkInput(
                    part_index=0, name="다른이름.pdf", content_type="application/pdf",
                    size_bytes=999, sha256="0" * 64, category="original",
                )
            ],
        )

    response = client.post(
        "/api/v1/mail/uid-rollback-2/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "rollback-table-check-1"},
    )
    assert response.status_code == 409

    with session_scope() as db:
        review_count = db.scalar(
            select(func.count()).select_from(MailReviewRow).where(
                MailReviewRow.message_id == "uid-rollback-2"
            )
        )
        attachment_count = db.scalar(
            select(func.count()).select_from(MailReviewAttachmentRow)
        )
        idempotency_count = db.scalar(
            select(func.count()).select_from(MailIdempotencyRow).where(
                MailIdempotencyRow.idempotency_key == "rollback-table-check-1"
            )
        )
        audit_count = db.scalar(
            select(func.count()).select_from(MailAuditRow).where(
                MailAuditRow.message_id == "uid-rollback-2"
            )
        )
    assert review_count == 0
    assert attachment_count == 0
    assert idempotency_count == 0
    assert audit_count == 0


# ── 제외(dismiss) 스냅샷은 첨부 메타데이터도 남긴다 ──────────────────────────


def test_dismiss_snapshots_attachment_metadata_without_linking_anything(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    message = _pending_message(attachments=(_attachment(0, "제외될파일.pdf"),))
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    response = client.post(
        f"/api/v1/mail/{message.id}/dismiss",
        json={"expected_version": 0},
        headers={"Idempotency-Key": "dismiss-snapshot-1"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["attachments"]) == 1
    attachment = data["attachments"][0]
    assert attachment["filename"] == "제외될파일.pdf"
    assert attachment["linked_file_id"] is None


# ── 지식화 승격: 예약이 vault 쓰기보다 먼저 경쟁을 해소한다 ──────────────────


def test_promote_to_note_loses_the_race_before_calling_the_note_writer(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))
    setup = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "promote-race-approve-1"},
    )
    assert setup.status_code == 200, setup.text

    import lep.modules.mail.application.services as mail_services

    calls: list[str] = []

    def _never(*args: Any, **kwargs: Any) -> str:
        calls.append("called")
        return "should-not-be-reached"

    monkeypatch.setattr(mail_services, "create_note_from", _never)

    # 동시 요청의 승자를 흉내 낸다: 이 요청이 예약(버전 증가 + note_id 채움)을
    # 먼저 커밋해 둔다.
    with session_scope() as db:
        row = db.scalar(
            select(MailReviewRow).where(MailReviewRow.message_id == message.id)
        )
        assert row is not None
        row.note_id = "__promoting__:concurrent-winner"
        row.version = row.version + 1

    response = client.post(f"/api/v1/mail/{message.id}/promote-to-note")

    assert response.status_code == 409
    assert calls == []  # 패자는 vault를 절대 부르지 않는다.


# ── 멤버의 status=all은 자신의 승인된 프로젝트 메일만 본다 ───────────────────


def test_member_status_all_returns_only_their_approved_project_mail(
    client: Any, signed_up: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    unclassified_msg = _pending_message(message_id="uid-all-unclassified")
    _install_fake_mail_service(
        monkeypatch, FakeMailAdapter({unclassified_msg.id: unclassified_msg})
    )

    _second_member(client)
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "회원 프로젝트", "code": "ALL-MEM-1", "customer_name": "고객사"},
    )
    assert project_response.status_code == 201, project_response.text
    member_project = project_response.json()["data"]
    member_token = _session_token(client)

    client.cookies.clear()
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "correct-horse-battery"},
    )
    assert admin_login.status_code == 200, admin_login.text
    approved = client.post(
        f"/api/v1/mail/{unclassified_msg.id}/approve",
        json={"project_id": member_project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "all-mem-approve-1"},
    )
    assert approved.status_code == 200, approved.text

    client.cookies.clear()
    client.cookies.set("lep_session", member_token)
    all_view = client.get(f"/api/v1/projects/{member_project['id']}/mail?status=all")
    assert all_view.status_code == 200, all_view.text
    ids = [item["id"] for item in all_view.json()["data"]]
    assert ids == [unclassified_msg.id]

    # (다른 관리자 프로젝트의 status=all은 여전히 403이다.)
    client.cookies.clear()
    admin_login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "correct-horse-battery"},
    )
    assert admin_login2.status_code == 200, admin_login2.text
    admin_project = client.post(
        "/api/v1/projects",
        json={"name": "관리자 프로젝트", "code": "ALL-ADMIN-1", "customer_name": "고객사"},
    ).json()["data"]

    client.cookies.clear()
    client.cookies.set("lep_session", member_token)
    forbidden = client.get(f"/api/v1/projects/{admin_project['id']}/mail?status=all")
    assert forbidden.status_code == 403


# ── 동시성: idempotency 경쟁은 500이 아니라 409 또는 승자의 결과다 ──────────


def test_concurrent_same_key_different_message_is_a_409_not_a_500(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 Idempotency-Key를 다른 메일에 동시에 쓰면 진짜 충돌이다 — 원시
    unique 제약 위반이 그대로 500으로 새면 안 된다."""

    message_a = _pending_message(message_id="uid-race-a")
    message_b = _pending_message(message_id="uid-race-b")
    adapter = FakeMailAdapter({message_a.id: message_a, message_b.id: message_b})
    _install_fake_mail_service(monkeypatch, adapter)

    shared_key = "race-different-message-1"
    injected = {"done": False}
    real_get_message = adapter.get_message

    def _racing_get_message(message_id: str) -> MailMessage | None:
        if message_id == "uid-race-a" and not injected["done"]:
            injected["done"] = True
            with session_scope() as db:
                winner_row = MailReviewRow(
                    id=str(uuid.uuid4()), mailbox_key=adapter.mailbox_key,
                    message_id="uid-race-b", status="unrelated", project_id=None,
                    version=1, approved_by=signed_up["id"], approved_at=datetime.now(tz=UTC),
                    sender_name="", sender_org="", received_at=None, subject="", body="",
                )
                db.add(winner_row)
                db.flush()
                db.add(
                    MailIdempotencyRow(
                        id=str(uuid.uuid4()), mailbox_key=adapter.mailbox_key,
                        message_id="uid-race-b", idempotency_key=shared_key,
                        actor_id=signed_up["id"], action="dismiss",
                        payload_hash="does-not-match-anything", review_id=winner_row.id,
                        result_version=1,
                    )
                )
        return real_get_message(message_id)

    monkeypatch.setattr(adapter, "get_message", _racing_get_message)

    response = client.post(
        "/api/v1/mail/uid-race-a/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": shared_key},
    )

    assert response.status_code == 409


def test_concurrent_same_key_same_message_race_returns_the_winners_result(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 메일에 같은 키·같은 내용으로 동시에 재시도하면, 진 쪽도 이긴 쪽의
    결과를 그대로 돌려받는다 — 리뷰 행 unique 제약 충돌을 곧장 409로 답하지
    않고, 그 사이 커밋된 idempotency 기록이 있으면 그것을 재현한다."""

    message = _pending_message(message_id="uid-race-same")
    adapter = FakeMailAdapter({message.id: message})
    _install_fake_mail_service(monkeypatch, adapter)

    shared_key = "race-same-message-1"
    request_body = {"project_id": project["id"], "expected_version": 0, "attachments": []}
    injected = {"done": False}
    real_get_message = adapter.get_message

    def _racing_get_message(message_id: str) -> MailMessage | None:
        if not injected["done"]:
            injected["done"] = True
            from lep.modules.mail.application.services import payload_hash

            phash = payload_hash(
                action="approve", mailbox_key=adapter.mailbox_key,
                message_id="uid-race-same", project_id=project["id"],
                expected_version=0, attachments=[],
            )
            with session_scope() as db:
                winner_row = MailReviewRow(
                    id=str(uuid.uuid4()), mailbox_key=adapter.mailbox_key,
                    message_id="uid-race-same", status="project", project_id=project["id"],
                    version=1, approved_by=signed_up["id"], approved_at=datetime.now(tz=UTC),
                    sender_name="", sender_org="", received_at=None, subject="", body="",
                )
                db.add(winner_row)
                db.flush()
                db.add(
                    MailIdempotencyRow(
                        id=str(uuid.uuid4()), mailbox_key=adapter.mailbox_key,
                        message_id="uid-race-same", idempotency_key=shared_key,
                        actor_id=signed_up["id"], action="approve", payload_hash=phash,
                        review_id=winner_row.id, result_version=1, result_note_id=None,
                    )
                )
        return real_get_message(message_id)

    monkeypatch.setattr(adapter, "get_message", _racing_get_message)

    response = client.post(
        "/api/v1/mail/uid-race-same/approve", json=request_body,
        headers={"Idempotency-Key": shared_key},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["version"] == 1
    assert data["classification"] == "project"


# ── documents 응답 검증: 훼손된 결과는 절대 조용히 통과하지 않는다 ───────────


def test_a_malformed_register_result_rolls_back_both_mail_and_documents_state(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """documents.public.register_mail_attachments이 실제로 링크를 기록한
    뒤에도, 돌려주는 참조 개수가 요청과 다르면 전체를 되돌린다 — 절대
    linked_file_id=None으로 selected=true를 조용히 저장하지 않는다."""

    import lep.modules.mail.application.services as mail_services
    from lep.modules.documents.infrastructure.mail_link_models import MailAttachmentLinkRow
    from lep.modules.documents.public import register_mail_attachments as real_register

    adapter = _adapter_with_attachment(message_id="uid-malformed-1")
    _install_fake_mail_service(monkeypatch, adapter)

    def _malformed_register(db: Any, **kwargs: Any) -> list[Any]:
        refs = real_register(db, **kwargs)
        return refs[:-1]  # 실제로는 기록해 놓고, 훼손된(개수가 모자란) 결과를 돌려준다.

    monkeypatch.setattr(mail_services, "register_mail_attachments", _malformed_register)

    response = client.post(
        "/api/v1/mail/uid-malformed-1/approve",
        json={
            "project_id": project["id"], "expected_version": 0,
            "attachments": [{"part_index": 0, "category": "deliverable"}],
        },
        headers={"Idempotency-Key": "malformed-register-1"},
    )

    assert response.status_code == 502

    with session_scope() as db:
        review_count = db.scalar(
            select(func.count()).select_from(MailReviewRow).where(
                MailReviewRow.message_id == "uid-malformed-1"
            )
        )
        link_count = db.scalar(
            select(func.count()).select_from(MailAttachmentLinkRow).where(
                MailAttachmentLinkRow.message_id == "uid-malformed-1"
            )
        )
    assert review_count == 0
    assert link_count == 0


# ── idempotency 재현: note_id 스냅샷도 커맨드 완료 시점 그대로다 ────────────


def test_replaying_the_initial_approve_key_after_promotion_shows_the_original_snapshot(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _pending_message(message_id="uid-promote-replay-1", attachments=())
    _install_fake_mail_service(monkeypatch, FakeMailAdapter({message.id: message}))

    approved = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "promote-replay-initial-1"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["version"] == 1
    assert approved.json()["data"]["note_id"] is None

    promoted = client.post(f"/api/v1/mail/{message.id}/promote-to-note")
    assert promoted.status_code == 200, promoted.text
    note_id = promoted.json()["data"]["note_id"]
    assert note_id

    replay = client.post(
        f"/api/v1/mail/{message.id}/approve",
        json={"project_id": project["id"], "expected_version": 0, "attachments": []},
        headers={"Idempotency-Key": "promote-replay-initial-1"},
    )
    assert replay.status_code == 200, replay.text
    replay_data = replay.json()["data"]
    assert replay_data["version"] == 1  # 원래 approve가 끝났을 때의 버전 그대로
    assert replay_data["note_id"] is None  # 승격 이전 스냅샷

    fresh = client.get(f"/api/v1/mail/{message.id}")
    assert fresh.status_code == 200, fresh.text
    fresh_data = fresh.json()["data"]
    assert fresh_data["note_id"] == note_id
    assert fresh_data["version"] == 2  # promote-to-note가 버전을 올렸다


# ── 마이그레이션 스크립트: DSN을 새지 않고, 6개 테이블만 additive로 늘린다 ──


def test_migration_script_never_leaks_dsn_or_traceback_on_engine_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret_marker = "SECRET-MARKER-DO-NOT-LEAK"

    def _raising_engine() -> None:
        raise RuntimeError(
            f"could not connect to postgresql://user:{secret_marker}@bad-host/db"
        )

    import lep.common.db as db_module

    monkeypatch.setattr(db_module, "engine", _raising_engine)

    from scripts.migrate_mail_review import main

    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert secret_marker not in captured.out
    assert secret_marker not in captured.err


def test_migration_script_dry_run_apply_reapply_adds_only_six_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """로컬 SQLite에서: dry-run은 아무것도 만들지 않고, apply는 6개
    테이블만(기존 core 테이블은 그대로 두고) 추가하며, 재실행은 no-op이다."""

    from sqlalchemy import inspect
    from sqlalchemy.orm import Session

    db_path = tmp_path / "migrate-fixture.db"
    monkeypatch.setenv("LEP_DATABASE_URL", f"sqlite:///{db_path}")

    import lep.common.db as db_module

    db_module._engine = None
    db_module._session_factory = None

    from scripts.migrate_mail_review import _OWNED_TABLES, main

    from lep.common.db import Base
    from lep.common.schema import load_all_models
    from lep.modules.iam.infrastructure.models import UserRow

    load_all_models()
    bound = db_module.engine()
    core_tables = [
        table for name, table in Base.metadata.tables.items() if name not in _OWNED_TABLES
    ]
    Base.metadata.create_all(bind=bound, tables=core_tables)

    before = set(inspect(bound).get_table_names())
    assert before.isdisjoint(_OWNED_TABLES)

    # 기존 core 테이블에 표식 행을 하나 심어, 마이그레이션이 그 테이블을
    # 건드리지 않았는지 나중에 확인한다.
    with Session(bound) as session:
        session.add(
            UserRow(
                id="probe-user", email="probe@example.invalid", display_name="표식",
                password_hash="x", role="admin", status="active",
                created_at=datetime.now(tz=UTC),
            )
        )
        session.commit()

    dry_run_exit = main([])
    assert dry_run_exit == 0
    dry_output = capsys.readouterr().out
    for table_name in sorted(_OWNED_TABLES):
        assert table_name in dry_output
    assert set(inspect(bound).get_table_names()) == before

    apply_exit = main(["--apply"])
    assert apply_exit == 0
    after_apply = set(inspect(bound).get_table_names())
    assert _OWNED_TABLES <= after_apply
    assert after_apply - before == _OWNED_TABLES

    reapply_exit = main(["--apply"])
    assert reapply_exit == 0
    reapply_output = capsys.readouterr().out
    assert "already present" in reapply_output
    assert set(inspect(bound).get_table_names()) == after_apply

    with Session(bound) as session:
        probe = session.get(UserRow, "probe-user")
        assert probe is not None
        assert probe.display_name == "표식"
