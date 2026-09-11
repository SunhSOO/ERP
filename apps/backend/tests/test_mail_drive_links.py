"""WP-PKD-MAIL-DRIVE-20260909: approved mail attachment references (ADR-021).

Covers ``documents.public.register_mail_attachments`` — the sole write path
mail approval uses to connect an approved attachment to a project's drive —
and the visibility rule that merges those references into the drive list and
summary. No real mail/converter/vcs adapter is touched; everything here is
plain SQLite plus the ``documents`` and ``iam``/``projects`` services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from lep.common.db import as_utc, session_scope
from lep.common.problems import ProblemError
from lep.modules.documents.domain.entities import DriveCategory, MailAttachmentLinkInput
from lep.modules.documents.infrastructure import mail_links
from lep.modules.documents.public import get_document_service, register_mail_attachments
from lep.modules.iam.domain.entities import User, UserRole, UserStatus
from lep.modules.iam.infrastructure.models import UserRow
from lep.modules.projects.application.services import ProjectService

SHA_A = "a" * 64
SHA_B = "b" * 64
#: ADR-021: mailbox_key is itself a SHA-256 hex digest, so fixture values
#: must be well-formed 64-hex, not an arbitrary opaque string.
MBX_1 = "1" * 64
MBX_2 = "2" * 64


def _valid_input(*, part_index: int = 0, category: str = "report", sha256: str = SHA_A,
                  name: str = "report.pdf") -> MailAttachmentLinkInput:
    return MailAttachmentLinkInput(
        part_index=part_index,
        name=name,
        content_type="application/pdf",
        size_bytes=1024,
        sha256=sha256,
        category=category,
    )


# ── HTTP-level helpers (multi-user, cookie-scoped) ──────────────────────────


def _signup(client: Any, email: str) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "display_name": email.split("@")[0],
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    token = response.cookies.get("lep_session")
    assert token
    data: dict[str, Any] = response.json()["data"]
    return data, token


def _use_session(client: Any, token: str | None) -> None:
    """Per-request ``cookies=`` is deprecated on httpx's ``Client``. Reset the
    jar first so a stale cookie from an earlier actor is never still there,
    then set the one session cookie this call should send, if any."""

    client.cookies.clear()
    if token is not None:
        client.cookies.set("lep_session", token)


def _create_project(client: Any, token: str, *, code: str) -> dict[str, Any]:
    _use_session(client, token)
    response = client.post(
        "/api/v1/projects",
        json={"name": f"프로젝트 {code}", "code": code, "customer_name": "고객사"},
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


# ── persistence / exact replay / isolation ──────────────────────────────────


def test_register_persists_immutable_metadata(client: Any, signed_up: dict[str, str],
                                                project: dict[str, Any]) -> None:
    with session_scope() as db:
        refs = register_mail_attachments(
            db,
            project_id=project["id"],
            mailbox_key=MBX_1,
            message_id="msg-1",
            attachments=[_valid_input(part_index=0)],
            actor_id=signed_up["id"],
        )
        assert len(refs) == 1
        assert refs[0].part_index == 0

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert len(rows) == 1
        row = rows[0]
        assert row.id == refs[0].id
        assert row.project_id == project["id"]
        assert row.mailbox_key == MBX_1
        assert row.message_id == "msg-1"
        assert row.part_index == 0
        assert row.name == "report.pdf"
        assert row.content_type == "application/pdf"
        assert row.size_bytes == 1024
        assert row.sha256 == SHA_A
        assert row.category == "report"
        assert row.created_by == signed_up["id"]
        # SQLite gives back a naive datetime for the same TIMESTAMPTZ column
        # PostgreSQL returns aware; as_utc is the one place that difference is
        # normalised, so the assertion goes through it rather than the raw ORM
        # value.
        assert as_utc(row.created_at).tzinfo is not None


def test_exact_replay_returns_the_same_refs(client: Any, signed_up: dict[str, str],
                                              project: dict[str, Any]) -> None:
    attachments = [_valid_input(part_index=0), _valid_input(part_index=1, name="b.pdf")]
    with session_scope() as db:
        first = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=attachments, actor_id=signed_up["id"],
        )
    with session_scope() as db:
        second = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=attachments, actor_id=signed_up["id"],
        )
    assert [r.id for r in first] == [r.id for r in second]

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert len(rows) == 2


def test_empty_attachments_is_a_no_op_for_mail_only_approval(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    """A mail approval with nothing worth putting in the drive is not an
    error: the project and identity are still checked, but an empty batch
    just registers nothing."""

    with session_scope() as db:
        refs = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[], actor_id=signed_up["id"],
        )
    assert refs == []

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


def test_incremental_parts_preserve_earlier_references(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    """A later batch on the same message that adds new parts must not touch
    the refs already registered for earlier parts."""

    with session_scope() as db:
        first = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
    with session_scope() as db:
        second = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=1, name="b.pdf")], actor_id=signed_up["id"],
        )
    assert first[0].id != second[0].id

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert {row.id for row in rows} == {first[0].id, second[0].id}
        assert len(rows) == 2


def test_same_part_replayed_alongside_a_new_part_keeps_the_old_ref(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    """Re-approving a message that already has one part linked, together
    with a genuinely new part, must return the existing ref unchanged for
    the old part and a fresh one only for the new part."""

    with session_scope() as db:
        first = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )

    with session_scope() as db:
        second = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0), _valid_input(part_index=1, name="b.pdf")],
            actor_id=signed_up["id"],
        )
    assert second[0].id == first[0].id
    assert second[1].id != first[0].id

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert len(rows) == 2


def test_different_mailbox_key_is_a_separate_reference(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    """Identity is (mailbox_key, message_id, part_index); the same message_id
    in a different mailbox never collides."""

    with session_scope() as db:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_2, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert {row.mailbox_key for row in rows} == {MBX_1, MBX_2}
        assert len(rows) == 2


def test_replay_with_different_project_conflicts(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    # A second project owned by the same actor is enough to exercise the
    # project-mismatch branch without a second user.
    with session_scope() as db:
        second_project = ProjectService(db).create_project(
            name="다른 프로젝트", code="OTHER-1", customer_name="고객사",
            role="vendor", pm_name="pm", created_by=signed_up["id"],
        )
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
        second_project_id = second_project.id

    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=second_project_id, mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
    assert exc.value.code == "STATE_CONFLICT"


def test_replay_with_different_metadata_conflicts(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0, sha256=SHA_A)], actor_id=signed_up["id"],
        )

    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0, sha256=SHA_B)], actor_id=signed_up["id"],
        )
    assert exc.value.code == "STATE_CONFLICT"

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert len(rows) == 1
        assert rows[0].sha256 == SHA_A


# ── invalid metadata / duplicate parts ──────────────────────────────────────


@pytest.mark.parametrize(
    "attachment",
    [
        MailAttachmentLinkInput(0, "../secret.pdf", "application/pdf", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "a/b.pdf", "application/pdf", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "a\\b.pdf", "application/pdf", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "bad\x00name.pdf", "application/pdf", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "", "application/pdf", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "ok.pdf", "", 1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "ok.pdf", "application/pdf", -1, SHA_A, "report"),
        MailAttachmentLinkInput(0, "ok.pdf", "application/pdf", 1, "not-a-hash", "report"),
        MailAttachmentLinkInput(0, "ok.pdf", "application/pdf", 1, "a" * 63, "report"),
        MailAttachmentLinkInput(0, "ok.pdf", "application/pdf", 1, SHA_A, "unknown"),
        MailAttachmentLinkInput(-1, "ok.pdf", "application/pdf", 1, SHA_A, "report"),
    ],
)
def test_invalid_attachment_metadata_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any],
    attachment: MailAttachmentLinkInput,
) -> None:
    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[attachment], actor_id=signed_up["id"],
        )
    assert exc.value.code == "VALIDATION_FAILED"

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


@pytest.mark.parametrize(
    "bad_key",
    [
        "mbx-1",  # opaque, not a hash at all
        "a" * 63,  # one short
        "a" * 65,  # one long
        "A" * 64,  # uppercase hex is rejected outright, never normalised
        "g" * 64,  # non-hex character
        " " + "a" * 64,  # leading whitespace
        "a" * 64 + "\n",  # trailing control character
    ],
)
def test_invalid_mailbox_key_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any], bad_key: str,
) -> None:
    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=bad_key, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
    assert exc.value.code == "VALIDATION_FAILED"

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


@pytest.mark.parametrize("bad_content_type", ["\napplication/pdf", "application/pdf\r\n"])
def test_content_type_with_leading_or_trailing_newline_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any], bad_content_type: str,
) -> None:
    attachment = MailAttachmentLinkInput(
        0, "ok.pdf", bad_content_type, 1, SHA_A, "report"
    )
    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[attachment], actor_id=signed_up["id"],
        )
    assert exc.value.code == "VALIDATION_FAILED"

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


def test_duplicate_part_index_in_one_batch_is_rejected(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db, pytest.raises(ProblemError) as exc:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0), _valid_input(part_index=0, name="b.pdf")],
            actor_id=signed_up["id"],
        )
    assert exc.value.code == "VALIDATION_FAILED"

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


def test_all_four_categories_including_original_are_permitted(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    categories = ["original", "report", "deliverable", "source"]
    with session_scope() as db:
        refs = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[
                _valid_input(part_index=i, category=c) for i, c in enumerate(categories)
            ],
            actor_id=signed_up["id"],
        )
    assert len(refs) == 4


# ── transaction participation: no commit, no outer rollback ────────────────


def test_register_does_not_commit_the_outer_transaction(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )
        db.rollback()

    with session_scope() as db:
        assert mail_links.list_for_project(db, project["id"]) == []


def test_midbatch_conflict_rolls_back_only_this_call_via_savepoint(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    """A raw duplicate part_index inside one ``mail_links.register`` call
    forces a genuine ``IntegrityError`` at flush time (unlike the
    application-layer duplicate check, which never reaches the database).
    The whole call must roll back, and the caller's own transaction must
    still be usable afterward."""

    with session_scope() as db:
        clashing = [
            MailAttachmentLinkInput(1, "a.pdf", "application/pdf", 1, SHA_A, "report"),
            MailAttachmentLinkInput(1, "b.pdf", "application/pdf", 1, SHA_B, "report"),
        ]
        with pytest.raises(ProblemError) as exc:
            mail_links.register(
                db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
                actor_id=signed_up["id"], attachments=clashing,
            )
        assert exc.value.code == "STATE_CONFLICT"

        # the outer transaction is still usable: a second, valid registration
        # in the same session succeeds and is what ends up persisted.
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=2)], actor_id=signed_up["id"],
        )

    with session_scope() as db:
        rows = mail_links.list_for_project(db, project["id"])
        assert [row.part_index for row in rows] == [2]


# ── provenance: original stays a read-only direct-upload category ──────────


def test_direct_upload_of_original_is_still_read_only(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db, pytest.raises(ProblemError) as exc:
        get_document_service().add_file(
            db, project["id"], file_id=str(uuid.uuid4()), name="x.pdf",
            category=DriveCategory.ORIGINAL, origin="고객 제공", size_bytes=1,
        )
    assert exc.value.code == "STATE_CONFLICT"


def test_approved_mail_reference_may_use_original(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db:
        refs = register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0, category="original")],
            actor_id=signed_up["id"],
        )
    assert len(refs) == 1


# ── drive visibility: active admin or project creator only ─────────────────


def test_admin_and_creator_see_the_link_unrelated_member_and_noauth_do_not(
    client: Any,
) -> None:
    admin, admin_token = _signup(client, "admin@example.invalid")
    creator, creator_token = _signup(client, "creator@example.invalid")
    outsider, outsider_token = _signup(client, "outsider@example.invalid")

    project = _create_project(client, creator_token, code="MAIL-1")

    with session_scope() as db:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=creator["id"],
        )

    # The shared TestClient keeps a persistent cookie jar: each sign-up's
    # Set-Cookie response landed in it, so a stale cookie from an earlier
    # actor would linger unless cleared. ``_use_session`` resets the jar
    # before every actor switch so exactly one session cookie — or none — is
    # ever sent.
    _use_session(client, admin_token)
    admin_files = client.get(f"/api/v1/projects/{project['id']}/drive/files")
    assert admin_files.status_code == 200
    assert len(admin_files.json()["data"]) == 1
    assert admin_files.json()["data"][0]["source_kind"] == "mail_attachment"

    _use_session(client, creator_token)
    creator_files = client.get(f"/api/v1/projects/{project['id']}/drive/files")
    assert creator_files.status_code == 200
    assert len(creator_files.json()["data"]) == 1

    _use_session(client, outsider_token)
    outsider_files = client.get(f"/api/v1/projects/{project['id']}/drive/files")
    assert outsider_files.status_code == 200
    assert outsider_files.json()["data"] == []

    _use_session(client, None)
    noauth_files = client.get(f"/api/v1/projects/{project['id']}/drive/files")
    assert noauth_files.status_code == 401

    _use_session(client, admin_token)
    admin_summary = client.get(f"/api/v1/projects/{project['id']}/drive")
    report = next(c for c in admin_summary.json()["data"] if c["category"] == "report")
    assert report["count"] == 1

    _use_session(client, outsider_token)
    outsider_summary = client.get(f"/api/v1/projects/{project['id']}/drive")
    report_hidden = next(c for c in outsider_summary.json()["data"] if c["category"] == "report")
    assert report_hidden["count"] == 0


def test_inactive_actor_sees_no_linked_files_even_when_project_creator(
    client: Any, signed_up: dict[str, str], project: dict[str, Any]
) -> None:
    with session_scope() as db:
        register_mail_attachments(
            db, project_id=project["id"], mailbox_key=MBX_1, message_id="msg-1",
            attachments=[_valid_input(part_index=0)], actor_id=signed_up["id"],
        )

    # Impersonate the project's own creator, but with a suspended status: the
    # status check alone must be enough to hide the link, isolated from the
    # creator-match branch.
    suspended_creator = User(
        id=signed_up["id"],
        email="creator@example.invalid",
        display_name="정지된 사용자",
        role=UserRole.MEMBER,
        status=UserStatus.SUSPENDED,
        created_at=datetime.now(tz=UTC),
    )
    with session_scope() as db:
        files = get_document_service().list_files(db, project["id"], actor=suspended_creator)
        assert files == []


def test_inactive_session_is_rejected_at_the_http_layer(client: Any) -> None:
    """Belt and suspenders: a suspended user's cookie stops authenticating at
    all, before the drive's own actor check ever runs."""

    user, token = _signup(client, "later-suspended@example.invalid")
    project = _create_project(client, token, code="SUSP-1")

    with session_scope() as db:
        row = db.get(UserRow, user["id"])
        assert row is not None
        row.status = "suspended"

    _use_session(client, token)
    response = client.get(f"/api/v1/projects/{project['id']}/drive/files")
    assert response.status_code == 401
