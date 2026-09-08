# API 및 이벤트 계약 상세설계

## 1. 기본 원칙

- 외부/프론트엔드 API는 REST + JSON을 기본으로 한다.
- OpenAPI 문서를 코드와 함께 생성하고 CI에서 변경을 검증한다.
- 실시간 상태는 WebSocket 또는 SSE를 제한적으로 사용한다.
- 모듈 간 직접 DB 쓰기를 금지하고 애플리케이션 서비스 또는 이벤트를 사용한다.
- AI 에이전트도 동일한 업무 API를 도구로 호출한다.
- API는 권한, 상태 전이, 유효성 검증, 감사 로깅을 우회할 수 없다.

## 2. 기본 URL

```text
/api/v1/<resources>
/api/v1/admin/<resources>
/api/v1/integrations/<provider>/webhooks
/api/v1/ai/<resources>
```

`v1` 내 호환 가능한 필드 추가는 허용하되 의미 변경이나 삭제는 새 버전을 사용한다.

## 3. 리소스 명명

- 복수형 kebab-case 또는 프로젝트 표준 하나로 통일
- URL에 동사 남용 금지
- 상태 전이처럼 명시적 행위는 action endpoint 허용

예:

```text
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
POST   /api/v1/projects/{project_id}/transitions
POST   /api/v1/projects/{project_id}/archive
GET    /api/v1/projects/{project_id}/timeline
```

## 4. 인증 헤더

```text
Authorization: Bearer <token>
X-Request-ID: <client-generated optional id>
Idempotency-Key: <required for selected create/execute endpoints>
If-Match: "<entity-version>"
```

서버는 모든 응답에 `X-Trace-ID`를 반환한다.

## 5. 응답 형식

### 5.1 단일 리소스

```json
{
  "data": {
    "id": "uuid",
    "project_code": "PRJ-2026-001",
    "name": "광주 AI 정수장",
    "status": "ACTIVE",
    "version": 7,
    "created_at": "2026-08-05T02:00:00Z",
    "updated_at": "2026-08-05T03:00:00Z"
  },
  "meta": {
    "trace_id": "..."
  }
}
```

### 5.2 목록

커서 기반 페이지네이션을 기본으로 하고 관리용 소규모 목록은 offset 방식을 선택적으로 허용한다.

```json
{
  "data": [],
  "meta": {
    "next_cursor": "...",
    "has_more": true,
    "total": 125,
    "trace_id": "..."
  }
}
```

`total` 계산 비용이 큰 경우 요청 파라미터로 선택한다.

## 6. 필터·정렬·검색

예:

```text
GET /api/v1/tasks?project_id=...&status=TODO,IN_PROGRESS
    &assignee_id=me&due_before=2026-08-12T00:00:00Z
    &sort=due_at,-priority&limit=50
```

- 필터 이름은 데이터 모델과 일관되게 유지
- 임의 SQL 표현식을 받지 않음
- 정렬 가능 필드를 allowlist로 제한
- `q`는 간단한 검색어, 복잡한 검색은 `/search` 사용
- 날짜 범위는 `*_from`, `*_to`, `*_before`, `*_after` 규칙 사용

## 7. 필드 선택과 포함

과도한 N+1 호출을 줄이기 위해 제한된 `include`를 지원한다.

```text
GET /api/v1/projects/{id}?include=members,contract,health-summary
```

- 허용 가능한 관계만 포함
- 깊이 제한 1~2단계
- 대용량 컬렉션은 링크와 건수만 반환
- 권한이 없는 포함 데이터는 누락 또는 명시적 403 정책 중 하나로 일관되게 처리

## 8. 생성·수정

### 8.1 생성

```json
POST /api/v1/projects
{
  "project_code": "PRJ-2026-001",
  "name": "광주 AI 정수장",
  "customer_account_id": "uuid",
  "pm_employee_id": "uuid",
  "planned_start_date": "2026-08-10",
  "planned_end_date": "2027-02-28",
  "template_id": "uuid"
}
```

반환: `201 Created`, `Location` 헤더.

### 8.2 부분 수정

`PATCH`는 명시된 필드만 변경한다. `null` 의미를 스키마에 명확히 정의한다.

### 8.3 낙관적 잠금

클라이언트는 `If-Match` 또는 body의 `version`을 전달한다. 충돌 시:

- `409 Conflict` 또는 `412 Precondition Failed`
- 현재 서버 버전과 충돌 필드 제공
- 자동 덮어쓰기 금지

## 9. 상태 전이 API

상태를 단순 PATCH하지 않고 전이 의도와 사유를 받는다.

```json
POST /api/v1/contracts/{id}/transitions
{
  "action": "ACTIVATE",
  "reason": "서명본 등록 및 내부 결재 완료",
  "expected_version": 5
}
```

서버는 가능한 전이, 필요 권한, 필수 조건을 검증한다.

조회:

```text
GET /api/v1/contracts/{id}/available-transitions
```

## 10. 일괄 작업

대량 변경은 비동기 job으로 처리한다.

```json
POST /api/v1/tasks/bulk-jobs
{
  "operation": "CHANGE_DUE_DATE",
  "task_ids": ["..."],
  "parameters": {"due_at": "..."},
  "dry_run": true
}
```

흐름:

1. dry-run으로 대상·권한·오류 미리보기
2. 사용자 승인
3. 실행 job 생성
4. 항목별 성공/실패 결과 제공
5. AI 실행이면 추가 승인 정책 적용

## 11. 오류 계약

RFC 7807 계열 Problem Details 형식을 사용한다.

```json
{
  "type": "https://erp.local/problems/forbidden",
  "title": "이 작업을 수행할 권한이 없습니다.",
  "status": 403,
  "code": "PROJECT_UPDATE_FORBIDDEN",
  "detail": "프로젝트 관리자 또는 지정 편집자만 변경할 수 있습니다.",
  "instance": "/api/v1/projects/...",
  "trace_id": "..."
}
```

표준 오류 코드:

| HTTP | 코드 예 | 의미 |
|---|---|---|
| 400 | BAD_REQUEST | 형식은 맞지만 처리 불가 |
| 401 | AUTHENTICATION_REQUIRED | 로그인/토큰 문제 |
| 403 | FORBIDDEN | 권한 없음 |
| 404 | NOT_FOUND | 존재하지 않거나 노출 불가 |
| 409 | STATE_CONFLICT | 상태/동시성 충돌 |
| 412 | VERSION_MISMATCH | 예상 버전 불일치 |
| 422 | VALIDATION_FAILED | 필드 유효성 실패 |
| 429 | RATE_LIMITED | 요청 제한 |
| 500 | INTERNAL_ERROR | 예상치 못한 오류 |
| 502 | INTEGRATION_ERROR | 외부 연동 오류 |
| 503 | TEMPORARILY_UNAVAILABLE | 일시 장애/과부하 |

## 12. 파일 API

### 12.1 업로드 세션

```text
POST /api/v1/file-uploads
POST /api/v1/file-uploads/{id}/parts
POST /api/v1/file-uploads/{id}/complete
DELETE /api/v1/file-uploads/{id}
```

### 12.2 문서 버전 생성

업로드 완료된 file object를 문서 버전에 연결한다.

```json
POST /api/v1/documents/{document_id}/versions
{
  "upload_id": "uuid",
  "change_summary": "원청 피드백 반영"
}
```

### 12.3 다운로드

다운로드 권한 검사 후 짧은 만료의 사전 서명 URL 또는 스트리밍 응답을 제공한다. 민감 문서 다운로드는 감사 로그를 남긴다.

## 13. 보고서/장기 작업 API

```text
POST /api/v1/report-runs
GET  /api/v1/report-runs/{id}
POST /api/v1/report-runs/{id}/cancel
GET  /api/v1/report-runs/{id}/result
```

상태:

`QUEUED → RUNNING → SUCCEEDED | FAILED | CANCELLED`

진행률과 현재 단계를 제공한다.

## 14. 실시간 이벤트

SSE 또는 WebSocket으로 다음만 전달한다.

- 알림 도착
- 장기 작업 진행률
- AI 실행/승인 상태
- 협업 댓글 갱신
- 대시보드 중요 경보

업무 데이터의 진실원천은 REST 조회 결과다. 연결 끊김 후 재연결 시 마지막 이벤트 ID를 사용한다.

---

# 15. 내부 도메인 이벤트 표준

## 15.1 이벤트 envelope

```json
{
  "event_id": "uuid",
  "event_type": "project.project_created.v1",
  "schema_version": 1,
  "occurred_at": "2026-08-05T03:00:00Z",
  "producer": "project",
  "company_id": "uuid",
  "actor": {
    "type": "USER",
    "id": "uuid"
  },
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "aggregate": {
    "type": "PROJECT",
    "id": "uuid",
    "version": 1
  },
  "payload": {}
}
```

## 15.2 명명 규칙

```text
<domain>.<past_tense_event>.<version>
```

예:

- `sales.opportunity_won.v1`
- `contract.contract_activated.v1`
- `project.project_created.v1`
- `project.task_completed.v1`
- `dms.deliverable_submitted.v1`
- `workflow.approval_completed.v1`

## 15.3 이벤트 계약 규칙

- 과거 사실을 표현한다.
- 소비자가 DB를 다시 읽을 수 있도록 aggregate ID 포함
- 민감 원문을 과도하게 payload에 넣지 않음
- 필드 삭제/의미 변경은 새 schema version
- 이벤트 처리 실패가 원 트랜잭션을 되돌리지 않음
- 순서가 중요한 경우 aggregate version을 검증

## 16. 핵심 이벤트 카탈로그

### Core/IAM

- `iam.user_invited.v1`
- `iam.user_activated.v1`
- `iam.user_deactivated.v1`
- `iam.role_assignment_changed.v1`

### CRM/Sales

- `crm.account_created.v1`
- `crm.lead_converted.v1`
- `sales.opportunity_stage_changed.v1`
- `sales.opportunity_won.v1`
- `sales.quote_approved.v1`
- `sales.quote_sent.v1`
- `sales.quote_accepted.v1`

### Contract

- `contract.contract_approved.v1`
- `contract.contract_activated.v1`
- `contract.contract_expiring.v1`
- `contract.contract_completed.v1`
- `contract.contract_terminated.v1`

### Project

- `project.project_created.v1`
- `project.project_activated.v1`
- `project.member_added.v1`
- `project.milestone_delayed.v1`
- `project.task_assigned.v1`
- `project.task_blocked.v1`
- `project.task_completed.v1`
- `project.risk_escalated.v1`
- `project.project_health_changed.v1`
- `project.project_completed.v1`

### Meeting/DMS

- `calendar.meeting_scheduled.v1`
- `meeting.minutes_reviewed.v1`
- `meeting.action_item_confirmed.v1`
- `dms.document_version_created.v1`
- `dms.document_approved.v1`
- `dms.deliverable_due_soon.v1`
- `dms.deliverable_submitted.v1`

### Workflow/Finance/Purchase

- `workflow.approval_submitted.v1`
- `workflow.approval_completed.v1`
- `workflow.approval_rejected.v1`
- `procurement.purchase_request_approved.v1`
- `procurement.purchase_order_sent.v1`
- `procurement.goods_received.v1`
- `finance.expense_approved.v1`
- `finance.revenue_overdue.v1`
- `finance.budget_threshold_crossed.v1`

### Asset/HR/Infra/AI

- `asset.asset_assigned.v1`
- `asset.asset_due_for_inspection.v1`
- `hr.leave_approved.v1`
- `hr.employee_resigned.v1`
- `infra.incident_opened.v1`
- `infra.incident_resolved.v1`
- `ai.approval_requested.v1`
- `ai.tool_execution_completed.v1`
- `ai.tool_execution_failed.v1`

## 17. 이벤트 소비 예시

### 계약 활성화 → 프로젝트 생성 제안

`contract.contract_activated.v1` 소비:

- 동일 계약에 프로젝트가 없으면 생성 제안
- 계약 의무사항을 산출물 후보로 변환
- 지급 일정을 매출 계획 후보로 생성
- PM/관리자에게 알림

자동 생성 여부는 회사 정책으로 설정하되 초기에는 사용자 확인형을 권장한다.

### 입고 완료 → 자산 등록 제안

`procurement.goods_received.v1` 소비:

- 자산 후보 품목 식별
- 수량만큼 자산 초안 생성
- 시리얼/보유자/위치 입력 요청
- 확정 후 자산번호 채번

## 18. Webhook 발신

회사에서 승인한 이벤트만 외부 발송한다.

- HMAC 서명
- delivery ID
- 타임스탬프와 재전송 공격 방지
- 지수 백오프 재시도
- 대상별 실패 보관함
- payload 최소화
- 테스트 전송 기능

## 19. Webhook 수신

- provider별 서명 검증
- delivery ID 중복 방지
- 원본 payload 암호화/보존 정책
- 빠른 2xx 응답 후 비동기 처리
- 알 수 없는 이벤트는 무시하되 기록
- 외부 ID 매핑 검증

---

# 20. AI 도구 API 계약

## 20.1 도구 정의 예

```json
{
  "name": "project.create_task",
  "version": "1.0",
  "description": "프로젝트에 업무 초안을 만들거나 승인 후 생성한다.",
  "required_permissions": ["project.task.create"],
  "risk_level": "MEDIUM",
  "approval_policy": "REQUIRED_WHEN_EXTERNAL_OR_BULK",
  "input_schema": {
    "type": "object",
    "required": ["project_id", "title"],
    "properties": {
      "project_id": {"type": "string", "format": "uuid"},
      "title": {"type": "string", "maxLength": 200},
      "description": {"type": "string"},
      "assignee_employee_id": {"type": ["string", "null"]},
      "due_at": {"type": ["string", "null"], "format": "date-time"},
      "source_reference": {"type": ["object", "null"]}
    }
  }
}
```

## 20.2 실행 흐름

1. 도구 스키마 검증
2. acting user와 범위 권한 확인
3. 위험 정책 판정
4. dry-run/preview 생성
5. 필요 시 승인 요청
6. 승인된 payload 고정
7. idempotency key로 실행
8. 결과와 변경된 엔터티 기록
9. 사용자에게 원본 링크 제공

## 20.3 AI 전용 금지사항

- 범용 SQL 실행 도구 제공 금지
- 파일시스템 임의 경로 접근 금지
- 관리자 API 범용 프록시 금지
- 비밀정보 조회 도구 금지
- 동적 코드 실행 도구는 ERP 업무 에이전트에 제공하지 않음
- 사용자가 접근할 수 없는 정보를 요약 결과에 포함하지 않음

## 21. API 변경 관리

- OpenAPI diff를 CI에서 검사
- breaking change는 명시적 승인 필요
- 프론트와 백엔드가 공유하는 스키마 또는 생성 타입 사용
- deprecated 필드는 최소 한 릴리스 주기 유지
- 이벤트 스키마는 계약 테스트 제공
- 샘플 payload와 오류 사례 문서화

## 22. API 수용 기준

모든 신규 API는 다음을 충족해야 한다.

- 인증/권한 테스트
- 성공·검증 실패·상태 충돌·동시성 충돌 테스트
- 감사 로그 검증
- OpenAPI 예제
- idempotency 필요 여부 명시
- 민감정보 마스킹 검증
- 목록 pagination/filter/sort 규칙 준수
- trace ID와 구조화 로그

---
