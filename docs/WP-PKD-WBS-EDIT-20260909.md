# WP-PKD-WBS-EDIT-20260909 — 태스크 편집 규칙 준비

Work Package ID: WP-PKD-WBS-EDIT-20260909
Owned Module: delivery domain
Goal: 승인된 PKD 상태값을 사용하는 편집·전이 검증 규칙 준비
In Scope: 순수 상태 전이 그래프, 차단 사유·해소 담당 필수 검증, 제목·기간 검증 및 단위 테스트
Out of Scope: API/UI 연결, 권한 정책 결정, DB 변경, 배포, 외부 연동
Dependencies: DECISIONS.md ADR-016, 공통 권한·감사·낙관적 잠금 후속 계약
API/Event contracts used: 기존 TaskStatus 및 공통 ProblemError; 신규 HTTP/event 계약 없음
Tables owned: 이번 단계 변경 없음
Permissions affected: 없음; 실제 편집 endpoint는 아직 추가하지 않음
Migration needed: 이번 단계 없음; 후속 version 필드는 additive migration 필요
Tests required: 전이 25개 상태 조합, 차단 메타데이터, 제목 길이·공백, 날짜 순서; ruff/mypy/경계 검사
Risks/assumptions: 상태값은 ADR-016 정본. 전이 간선은 후속 연결용 최소 구현안이며 권한 정책 확정 전 API에 노출하지 않는다.

## 구현 내용

- `allowed_transitions(status)`는 변경 불가능한 순서 있는 튜플을 반환한다.
- 예정 → 진행/차단, 진행 → 차단/완료, 차단 → 예정/진행, 완료 → 진행을 허용한다. 같은 상태 및 일반 상태와 VCS_ONLY 간 수동 전이는 거절한다. 기존 VCS 채택 경로는 변경하지 않는다.
- 차단으로 전이할 때 공백을 제외한 사유와 해소 담당자가 필요하다. 전이 자체가 불가능하면 STATE_CONFLICT(409), 입력값이 잘못되면 VALIDATION_FAILED(422)를 사용한다.
- 제목을 trim하여 1~300자를 요구하고 종료일이 시작일보다 빠르면 거절한다. 같은 날 시작·종료는 허용한다.
- 공통 ProblemError가 FastAPI를 간접 참조하는 현재 구조를 재사용한다. 검증 로직 자체는 DB/네트워크를 호출하지 않는다. 공통 예외 계층 분리는 이번 범위에 포함하지 않는다.

## 검증 기록

- Claude Code `--model sonnet --effort medium`이 테스트 및 제품 코드를 작성했다. 실제 assistant model은 claude-sonnet-5이며 작성 결과는 조정자가 로컬에서 검사했다.
- TDD 첫 실행: transitions 모듈 미구현으로 ModuleNotFoundError 재현.
- 구현 후 pytest: 48 passed (0.23s).
- 초기 경계 검사: 통과.
- 초기 strict mypy: 테스트 타입 누락 등 32건, ruff: E501 1건. Claude 수정 및 최종 재검증 결과는 후속 기록한다.

## 제한 및 다음 단계

이 단계는 업무 화면에서 사용할 수 있는 태스크 편집 기능의 완료가 아니다. PATCH/transition endpoint, 프로젝트 접근 검사, 감사, atomic version 확인, DB migration, WBS 편집 폼 및 서버 응답 기반 허용 전이 표시가 아직 연결되지 않았다. 권한 정책 및 공통 계약이 확정된 뒤 이어서 구현한다. 운영 데이터·서버·외부 연동을 호출하지 않았다.

## 최종 로컬 검증 (2026-09-09)

- `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_task_transition_rules.py -q --basetemp=.audit-tmp/wbs-final --tb=short`: 48 passed (0.24s).
- `.venv/Scripts/python.exe -m mypy apps/backend/src/lep/modules/delivery/domain/transitions.py apps/backend/tests/test_task_transition_rules.py`: 2개 파일 오류 없음.
- `.venv/Scripts/python.exe -m ruff check apps/backend/src/lep/modules/delivery/domain/transitions.py apps/backend/tests/test_task_transition_rules.py`: 통과.
- `.venv/Scripts/python.exe scripts/check_boundaries.py`: 통과.
- 문서 담당 에이전트 독립 리뷰: 기능 결함 없음. 초기 타입 오류 지적은 Sonnet 수정 후 위 재검증으로 해소.

Completed Work Package: WP-PKD-WBS-EDIT-20260909의 독립 도메인 준비 단계만
Files/Modules changed: delivery/domain/transitions.py, tests/test_task_transition_rules.py, 이 문서
Behavior delivered: 호출 가능한 편집·전이 검증 함수. 기존 API/UI 동작은 변경되지 않음.
API/Event contracts: HTTP/event 변경 없음
Migrations: 없음
Permissions/Audit: 후속 공통 계약 대기, 실행 endpoint 미연결
Tests run and results: 위 48개 pytest 및 mypy/ruff/경계 검사 통과
Known limitations: 전체 태스크 편집·상태 변경 사용자 흐름 미완료, 운영/스테이징 미검증
Follow-up dependencies: 권한 정책, 감사 API, 원자 version 검사, additive migration, API/UI 연결
