"""WP-PKD-MAIL-RECOMMENDATIONS-20260909 — Project context recommendation scoring.

Task 4: Deterministic recommendations based on project code/name/customer and
message intent/milestone, with approved-mail context as secondary signal.
No LLM, embeddings, new database tables, auto-approval, automatic classification.
"""

from __future__ import annotations

from datetime import UTC, datetime

from lep.modules.mail.application.recommendations import recommend_projects
from lep.modules.mail.domain.entities import Classification, Confidence, MailMessage
from lep.modules.projects.public import ProjectContextRef


def _mail(
    subject: str = "", body: str = "", intent: str | None = None,
    milestone_code: str | None = None, classification: str = "unclassified",
) -> MailMessage:
    return MailMessage(
        id="test-mail",
        sender_name="발신자",
        sender_org="발신사",
        received_at=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
        subject=subject,
        body=body,
        classification=Classification(classification),
        project_id=None,
        intent=intent,
        confidence=None,
        milestone_code=milestone_code,
    )


def test_project_code_and_customer_match_triggers_high_confidence() -> None:
    """프로젝트 코드·고객사·마일스톤이 일치하면 high 추천."""
    message = _mail(subject="DAON M3 검토 요청", body="다온 정수장 일정 검토", milestone_code="M3")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
        ProjectContextRef(id="other", code="PRJ-OTHER", name="기타", customer_name="타사"),
    ]

    result = recommend_projects(message, projects, approved_contexts=[])

    assert len(result) > 0, f"Expected recommendations but got none. Subject: {message.subject}"
    assert result[0].project_id == "daon"
    assert result[0].confidence is Confidence.HIGH
    assert "프로젝트명: 다온 정수장" in result[0].reasons


def test_no_match_returns_empty() -> None:
    """일치하는 근거가 없으면 추천을 하지 않는다."""
    message = _mail(subject="일반 안내", body="")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
    ]

    result = recommend_projects(message, projects, approved_contexts=[])

    assert result == ()


def test_tied_top_score_returns_empty() -> None:
    """동점인 추천은 모호해서 제외한다."""
    message = _mail(subject="공통 M3 안내", body="")
    equally_matching_projects = [
        ProjectContextRef(
            id="proj1", code="PRJ-COMMON", name="공통 프로젝트1", customer_name="공통"
        ),
        ProjectContextRef(
            id="proj2", code="PRJ-COMMON", name="공통 프로젝트2", customer_name="공통"
        ),
    ]

    result = recommend_projects(message, equally_matching_projects, approved_contexts=[])

    assert result == ()


def test_approved_mail_context_boosts_confidence() -> None:
    """같은 프로젝트의 승인 메일 제목/의도 일치가 추천을 강화한다."""
    message = _mail(subject="DAON M3 검토 요청", body="다온 정수장 일정 검토", milestone_code="M3")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
    ]
    # 같은 프로젝트에서 승인된 메일의 (프로젝트 ID, 의도, 마일스톤)
    approved_contexts = [("daon", "일정 검토", "M3")]

    result = recommend_projects(message, projects, approved_contexts=approved_contexts)

    assert len(result) > 0
    assert result[0].project_id == "daon"


def test_unclassified_messages_only_get_recommendations() -> None:
    """미분류 메일만 추천을 계산한다."""
    classified = _mail(subject="DAON 일정", classification="project")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
    ]

    result = recommend_projects(classified, projects, approved_contexts=[])

    assert result == ()


def test_result_returns_up_to_three_unambiguous_candidates() -> None:
    """결과는 최대 3개의 명확한 후보를 반환한다."""
    message = _mail(subject="DAON 일정 M3", body="")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
        ProjectContextRef(id="other1", code="PRJ-OTHER", name="기타1", customer_name="타사1"),
        ProjectContextRef(id="other2", code="PRJ-OTHER", name="기타2", customer_name="타사2"),
        ProjectContextRef(id="other3", code="PRJ-OTHER", name="기타3", customer_name="타사3"),
        ProjectContextRef(id="other4", code="PRJ-OTHER", name="기타4", customer_name="타사4"),
    ]

    result = recommend_projects(message, projects, approved_contexts=[])

    assert len(result) <= 3


def test_single_project_code_match_does_not_include_unrelated_low_candidates() -> None:
    """프로젝트 코드 매칭만으로는 무관한 프로젝트를 낮은 신뢰도로 추천하지 않는다.

    일반적인 마일스톤(M3 등)이 메시지에 있어도, 그 프로젝트와 무관한
    프로젝트들을 점수 부여하면 안 된다. 점수는 프로젝트별로만 카운트되어야 한다.
    """
    # "DAON" 코드는 daon 프로젝트만 일치, "M3"는 일반적인 마일스톤
    message = _mail(subject="DAON M3 검토", body="", milestone_code="M3")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
        ProjectContextRef(id="other", code="PRJ-OTHER", name="기타", customer_name="타사"),
    ]

    result = recommend_projects(message, projects, approved_contexts=[])

    # 결과는 daon 프로젝트만 포함해야 하고, other 프로젝트는 포함되면 안 된다.
    assert len(result) == 1
    assert result[0].project_id == "daon"
    # other 프로젝트는 code/name/customer 매칭이 없으므로 점수가 0이어야 한다.


def test_intent_only_boosts_score_if_project_specific_approved_context_matches() -> None:
    """의도(intent)는 프로젝트의 승인된 컨텍스트에만 일치할 때만 점수를 준다.

    메시지의 의도가 일반적인 용어(e.g., '검토')라면, 이를 이유로
    모든 프로젝트를 추천하면 안 된다. 오직 그 프로젝트의 승인 이력에서
    같은 의도가 있을 때만 가산점을 준다.
    """
    # 일반적인 의도 "검토"를 가진 메시지
    message = _mail(subject="검토 부탁", body="", intent="검토")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온", customer_name="다온"),
        ProjectContextRef(id="other", code="PRJ-OTHER", name="기타", customer_name="타사"),
    ]

    # daon 프로젝트의 승인 이력에만 같은 의도가 있다
    approved_contexts = [("daon", "검토", None)]

    result = recommend_projects(message, projects, approved_contexts=approved_contexts)

    # 결과는 daon만 포함해야 한다
    assert len(result) == 1
    assert result[0].project_id == "daon"


def test_milestone_only_boosts_score_if_project_specific_approved_context_matches() -> None:
    """마일스톤(milestone)도 프로젝트 승인 컨텍스트에만 일치할 때만 점수를 준다.

    메시지의 마일스톤이 일반적인 단계(e.g., 'M1')라면, 모든 프로젝트를 추천하면 안 된다.
    """
    message = _mail(subject="M1 진행 보고", body="", milestone_code="M1")
    projects = [
        ProjectContextRef(id="daon", code="PRJ-DAON", name="다온", customer_name="다온"),
        ProjectContextRef(id="other", code="PRJ-OTHER", name="기타", customer_name="타사"),
    ]

    # daon 프로젝트의 승인 이력에만 같은 마일스톤이 있다
    approved_contexts = [("daon", None, "M1")]

    result = recommend_projects(message, projects, approved_contexts=approved_contexts)

    # 결과는 daon만 포함해야 한다
    assert len(result) == 1
    assert result[0].project_id == "daon"
