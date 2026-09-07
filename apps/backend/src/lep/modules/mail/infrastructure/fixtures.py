"""Fixture mail adapter (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.
도메인은 예약된 .invalid를 쓴다. 실재하는 주소로 오인되지 않게 하기 위해서다.

WP-PKD-034 adds the Hiworks adapter beside this one. Groupware API access often
needs a separate application, so an IMAP fallback is the planned alternative.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain.entities import Classification, Confidence, MailMessage

PRJ_DAON = "prj-daon"

_MESSAGES: list[MailMessage] = [
    MailMessage(
        id="mail-001",
        sender_name="이서영",
        sender_org="다온물산",
        received_at=datetime(2026, 9, 7, 5, 20, tzinfo=UTC),
        subject="M3 검수 일정 관련 회신 요청",
        body=(
            "안녕하세요 김서준 PM님,\n\n"
            "검수 일정이 09월 12일에서 다소 늦어질 수 있을 것 같습니다. "
            "저희 내부 승인 절차가 이번 주까지 걸릴 예정이라, "
            "1주일 정도 연기를 요청드리고 싶습니다.\n\n이서영"
        ),
        classification=Classification.UNCLASSIFIED,
        project_id=PRJ_DAON,
        intent="일정 변경",
        confidence=Confidence.MEDIUM,
        milestone_code="M3",
    ),
    MailMessage(
        id="mail-002",
        sender_name="WMS팀",
        sender_org="다온물산",
        received_at=datetime(2026, 9, 7, 2, 2, tzinfo=UTC),
        subject="필드 매핑 표 회신",
        body="요청하신 필드 매핑 표를 첨부합니다.",
        classification=Classification.PROJECT,
        project_id=PRJ_DAON,
        intent=None,
        confidence=Confidence.HIGH,
    ),
    MailMessage(
        id="mail-003",
        sender_name="박도윤",
        sender_org="루미노드",
        received_at=datetime(2026, 9, 6, 1, 0, tzinfo=UTC),
        subject="인터페이스 정의서 v2.1 공유",
        body="정의서 최신본을 공유드립니다.",
        classification=Classification.PROJECT,
        project_id=PRJ_DAON,
        intent=None,
        confidence=Confidence.HIGH,
    ),
    MailMessage(
        id="mail-004",
        sender_name="사내 총무팀",
        sender_org="루미노드",
        received_at=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        subject="09월 정기 점검 안내",
        body="09월 정기 점검 일정을 안내드립니다.",
        classification=Classification.UNRELATED,
        project_id=None,
        intent=None,
        confidence=None,
    ),
    MailMessage(
        id="mail-005",
        sender_name="이서영",
        sender_org="다온물산",
        received_at=datetime(2026, 9, 4, 7, 40, tzinfo=UTC),
        subject="검수 대상 범위 재확인 요청",
        body=(
            "검수 대상에 운영 안정화 지원이 포함되는지 확인 부탁드립니다. "
            "계약 조항 해석이 필요해 보입니다."
        ),
        classification=Classification.UNCLASSIFIED,
        project_id=PRJ_DAON,
        intent="범위 문의",
        confidence=Confidence.LOW,
    ),
    MailMessage(
        id="mail-006",
        sender_name="구매팀",
        sender_org="다온물산",
        received_at=datetime(2026, 9, 3, 2, 15, tzinfo=UTC),
        subject="검수 완료 후 정산 일정 문의",
        body="검수가 끝나면 정산 일정을 언제로 잡으면 좋을지 문의드립니다.",
        classification=Classification.UNCLASSIFIED,
        project_id=PRJ_DAON,
        intent="정산 문의",
        confidence=Confidence.MEDIUM,
    ),
]


class FixtureMailAdapter:
    def list_messages(self, project_id: str) -> list[MailMessage]:
        return [
            item
            for item in _MESSAGES
            if item.project_id == project_id or item.classification is Classification.UNRELATED
        ]

    def get_message(self, message_id: str) -> MailMessage | None:
        return next((item for item in _MESSAGES if item.id == message_id), None)

    def replace_message(self, message: MailMessage) -> MailMessage:
        for index, existing in enumerate(_MESSAGES):
            if existing.id == message.id:
                _MESSAGES[index] = message
                return message
        _MESSAGES.append(message)
        return message

    def unclassified_count(self, project_id: str) -> int:
        return len(
            [
                item
                for item in _MESSAGES
                if item.project_id == project_id
                and item.classification is Classification.UNCLASSIFIED
                and not item.handled
            ]
        )
