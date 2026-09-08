# 개발 에이전트 오케스트레이션 운영서

- 적용 프로젝트: Luminode ERP Platform
- 적용일: 2026-08-05
- 목적: 여러 코딩 에이전트가 동일 저장소에서 병렬 작업할 때 범위·권한·migration·공유 파일 충돌을 통제한다.

## 1. 기본 운영 모델

에이전트는 “ERP 전체를 만들어라”라는 하나의 프롬프트로 실행하지 않는다. 반드시 `work_packages.yaml`의 한 작업 패키지만 맡긴다.

```text
사람/제품 책임자
        │
Coordinator Agent
        ├── Architect Agent
        ├── Implementation Agent A
        ├── Implementation Agent B
        ├── Implementation Agent C
        ├── QA·Security Agent
        └── Integration Agent
```

사람은 제품 범위와 중요 결정을 승인한다. Coordinator는 작업 상태와 의존성을 관리한다. Architect는 계약을 고정한다. 구현 에이전트는 자신의 worktree에서만 작업한다. QA·Security는 독립 검증한다. Integration Agent만 공유 산출물을 최종 병합한다.

## 2. 저장소 최초 준비

구현을 시작하기 전에 기본 브랜치에 다음 문서를 둔다.

- `AGENTS.md`
- `DECISIONS.md`
- `docs/specs/00_MASTER_DESIGN.md`부터 `13_AGENT_PROMPT_TEMPLATES.md`
- `docs/specs/APPROVAL_RECORD.md`
- `docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md`
- `docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`
- `docs/work-packages/work_packages.yaml`

Coordinator는 작업 패키지 상태 파일을 별도로 관리한다.

```yaml
work_package: WP-PLT-001
state: ready
owner: platform-agent-01
branch: feature/WP-PLT-001-repository-bootstrap
base_commit: <기본 브랜치 커밋>
dependencies: []
contract_revision: 1
started_at: <기록 시각>
last_handoff: null
```

시간값은 실행 도구가 실제 시각을 기록한다. 문서에 임의 시각을 미리 채우지 않는다.

## 3. 에이전트별 권한

### Coordinator Agent

할 수 있는 일:

- 작업 패키지 상태 변경
- worktree와 브랜치 할당
- 의존성 확인
- shared-file lock 부여
- 리뷰어 배정
- 통합 순서 결정
- 차단 사유와 결정 요청 기록

하지 않는 일:

- 대량 기능 구현
- 테스트 없이 충돌을 임의 해결
- 설계 밖 기능을 다음 작업에 끼워 넣기

### Architect Agent

할 수 있는 일:

- 모듈 경계·상태 머신·API·이벤트·권한 검토
- ADR 제안
- breaking change 승인 또는 반려
- 작업 패키지의 범위 축소

하지 않는 일:

- 제품 책임자 승인 없이 핵심 설계 변경
- 다른 모듈 직접 DB 쓰기 승인
- 구현 편의를 이유로 감사·권한 생략

### Implementation Agent

할 수 있는 일:

- 지정된 경로·테이블·API·테스트 수정
- 작업 패키지 acceptance criteria 달성
- 필요한 최소 문서 갱신
- 범위 안의 작은 리팩터링

하지 않는 일:

- 다른 worktree 수정
- 다른 모듈 테이블 직접 변경
- shared-file lock 없이 lockfile·공통 schema 변경
- 테스트 제거 또는 우회
- 실제 개인정보·비밀 사용

### QA·Security Agent

할 수 있는 일:

- 독립 환경에서 테스트
- 공격·권한·복구 시나리오 추가
- 출시 차단 결함 선언
- 회귀 테스트 MR 생성

하지 않는 일:

- 실패 테스트를 비활성화해 승인
- 제품 코드를 대량 수정해 구현자 리뷰를 우회

### Integration Agent

할 수 있는 일:

- 승인된 MR 순차 병합
- Alembic merge revision
- OpenAPI client 재생성
- lockfile 충돌 해결
- 기본 브랜치 통합 테스트와 태그

하지 않는 일:

- 의미가 다른 코드 충돌을 추측으로 해결
- 실패한 CI를 무시하고 병합

## 4. worktree 운용

### 4.1 생성

```bash
git fetch --all --prune
git switch main
git pull --ff-only
git worktree add ../lep-WP-PLT-001 -b feature/WP-PLT-001-repository-bootstrap main
```

각 worktree 안에 다음 파일을 생성한다.

```text
.agent/
├── assignment.md
├── contract.md
├── decisions.md
├── test-evidence.md
└── handoff.md
```

`.agent`는 MR에 포함할지 여부를 저장소 정책으로 결정하되, 최종 문서와 테스트 증거는 반드시 `docs/work-packages` 또는 MR 설명에 남긴다.

### 4.2 종료

```bash
git worktree remove ../lep-WP-PLT-001
git branch -d feature/WP-PLT-001-repository-bootstrap
git worktree prune
```

브랜치는 병합과 통합 CI 확인 후에만 삭제한다.

## 5. 작업 시작 계약

구현 에이전트는 첫 응답에서 아래 형식을 작성하고 코드 변경 전에 Architect 또는 Coordinator 승인을 받는다.

```text
Work Package:
Base Commit:
Goal:
In Scope:
Out of Scope:
Owned Paths:
Owned Tables:
API Contracts:
Events:
Permissions:
State Transitions:
Migration Plan:
Tests:
Shared Files Needed:
Risks and Assumptions:
```

다음 중 하나라도 불명확하면 코드를 넓게 작성하지 않는다.

- 어느 모듈이 테이블을 소유하는가
- 누가 이 API를 호출할 수 있는가
- 상태를 어떻게 변경하는가
- 감사가 필요한가
- 같은 요청이 반복될 수 있는가
- 실패 시 무엇을 되돌리는가
- 외부 연동이 중단되면 핵심 transaction은 유지되는가

## 6. 컨텍스트 패키지

Coordinator는 모든 에이전트에게 전체 문서를 무작정 넣지 않는다. 다음 순서의 최소 컨텍스트를 제공한다.

1. `AGENTS.md`
2. `DECISIONS.md`
3. 해당 작업 패키지 YAML
4. 관련 모듈 설계 절
5. 관련 데이터 모델 절
6. 관련 API·이벤트 절
7. 보안·테스트 공통 규칙
8. 선행 작업의 handoff와 공개 계약
9. 현재 저장소 트리와 관련 코드
10. 실패 중인 CI 또는 알려진 결함

에이전트가 읽지 않은 문서를 읽었다고 가정하지 않는다. 프롬프트에 실제 경로를 명시한다.

## 7. 공유 파일 잠금

Coordinator는 아래 형식으로 잠금을 기록한다.

```yaml
resource: alembic-head
owner: WP-PLT-003
scope:
  - apps/backend/migrations
expires_when: merge
reason: organization schema migration
```

잠금 대상:

- `pyproject.toml`, `uv.lock`
- `package.json`, `pnpm-lock.yaml`
- Alembic revision chain
- OpenAPI snapshot
- generated API client
- `packages/ui` 핵심 토큰
- Compose 공통 network/volume
- permission catalog
- event envelope
- 공통 error code catalog

잠금이 필요한 수정은 구현 에이전트가 직접 선점하지 않고 Coordinator에게 요청한다.

## 8. migration 병렬 작업

1. Coordinator가 파동별 migration 순서를 정한다.
2. 각 agent는 최신 기본 브랜치에서 revision을 만든다.
3. 이미 병합된 revision을 수정하지 않는다.
4. 병렬 branch가 모두 migration을 만들면 Integration Agent가 merge revision 또는 rebase 전략을 선택한다.
5. destructive change는 expand → backfill → switch → contract 순서를 따른다.
6. backfill은 중단 후 재실행 가능해야 한다.
7. 운영 lock 위험과 예상 SQL 범위를 MR에 기록한다.
8. rollback이 안전하지 않으면 forward-fix 절차를 문서화한다.

Phase 0 권장 migration 순서:

```text
IAM auth
→ organization
→ RBAC
→ audit/outbox
→ file objects
→ collaboration
```

## 9. API·이벤트 계약 변경

### 호환 변경

- optional response field 추가
- 새 endpoint 추가
- 새 event version 추가
- 기존 enum의 소비자가 unknown 값을 처리하도록 보장된 확장

### breaking change

- field 삭제 또는 의미 변경
- required field 추가
- 상태 값 재해석
- permission code 변경
- event payload 필수 필드 변경
- table owner 변경

breaking change 절차:

1. Architect Agent가 영향 범위를 작성한다.
2. `DECISIONS.md` 또는 계약 변경 기록을 만든다.
3. producer와 consumer migration 계획을 작성한다.
4. contract test를 먼저 변경한다.
5. 호환 기간 또는 동시 배포 전략을 정한다.
6. Integration Agent가 한 순서로 병합한다.

## 10. 에이전트 구현 루프

```text
Read
→ Contract
→ Failing Test
→ Minimal Implementation
→ Local Verify
→ Self Review
→ Documentation
→ Handoff
→ Independent Review
```

### Self Review 질문

- 설계 밖 기능을 넣었는가?
- 다른 모듈 내부 구현에 의존했는가?
- object-level 권한을 빠뜨렸는가?
- 상태를 일반 PATCH로 우회했는가?
- 실패·재시도·중복 실행을 고려했는가?
- 민감정보가 로그·오류·fixture에 있는가?
- migration을 재실행하거나 forward-fix할 수 있는가?
- UI에 loading/empty/error/forbidden/conflict가 있는가?
- 실제로 실행한 테스트 명령과 결과가 있는가?

## 11. MR 규칙

제목:

```text
[WP-PLT-005] 감사 로그·Outbox 기반
```

설명:

```text
Work Package:
Base Commit:
Summary:
In Scope:
Out of Scope:
Owned Paths:
API/Event Changes:
Database Migration:
Permissions:
Audit/Privacy:
Idempotency/Concurrency:
Tests Executed:
Test Evidence:
Screenshots:
Deployment Notes:
Known Limitations:
Follow-up Packages:
```

필수 label 예시:

```text
phase::0
stream::platform
risk::critical
review::architecture
review::security
migration::yes
```

MR은 기능 구현과 무관한 대규모 포맷 변경을 포함하지 않는다.

## 12. 리뷰 순서

1. **Domain Review**: 유스케이스·상태·데이터 무결성
2. **Architecture Review**: 모듈 경계·API·이벤트·migration
3. **Security Review**: 인증·권한·민감정보·감사·파일
4. **QA Review**: acceptance criteria·회귀·E2E
5. **Integration Review**: 공유 파일·병합 순서·기본 브랜치 CI

Critical 위험 작업은 다섯 단계를 모두 거친다. Medium 위험의 단순 UI는 Domain + QA + Integration으로 줄일 수 있다.

## 13. 결함 처리

| 등급 | 기준 | 처리 |
|---|---|---|
| Critical | 인증 우회, 전사 데이터 노출, 감사 삭제, 복원 불가 | 즉시 차단, 병합 금지 |
| High | IDOR, 상태 무결성 파괴, 파일 보안 우회, 금액 오류 | 단계 게이트 차단 |
| Medium | 일부 흐름 실패, 우회 가능한 UX/성능 문제 | owner·기한 없이 다음 단계로 넘기지 않음 |
| Low | 사소한 표시·문구·개선 | backlog로 전환 가능 |

버그 수정은 재현 테스트를 먼저 추가하고 같은 유형의 회귀 범위를 확장한다.

## 14. 에이전트 실패·중단 복구

에이전트가 중단되거나 방향을 잃으면 Coordinator는 다음만 회수한다.

- 현재 commit
- 변경 파일 목록
- 실행한 테스트와 실패
- 남은 작업
- 미확정 결정
- migration 적용 여부
- shared-file lock
- 위험한 임시 코드 여부

새 에이전트는 이전 대화 전체 대신 `assignment.md`, `contract.md`, `handoff.md`, Git diff와 테스트 결과를 받는다.

중단된 branch에 다음 패턴이 있으면 새 작업 전에 제거한다.

- 권한 우회 flag
- hard-coded admin
- debug token
- 임시 CORS `*`
- 검사 없는 파일 READY 처리
- `skip`된 보안 테스트
- 실제 비밀·개인정보
- 적용된 migration 수정

## 15. 사람 승인 지점

사람의 명시적 승인 없이 다음을 확정하지 않는다.

- 제품 범위 추가 또는 제거
- 계약·금액·인사·권한의 업무 규칙 변경
- 법정 회계·급여 자체 구현
- 외부 인터넷 공개
- 백업 보존 기간 축소
- AI 위험 등급 하향
- 데이터 물리 삭제 허용 확대
- 마이크로서비스/k3s 전환
- 실제 운영 데이터 일괄 이관
- 단계 게이트 우회

## 16. Phase 0 에이전트 배치 예

### 파동 0.1

- Platform Agent: `WP-PLT-001`
- Architect Agent: 경계·폴더·공통 계약 리뷰
- QA Agent: 재현성·경계 검사 리뷰

### 파동 0.2

- DevOps Agent: `WP-OPS-001`
- Security Agent: 네트워크·비밀·컨테이너 리뷰

### 파동 0.3

- Platform Agent: `WP-PLT-002`
- Frontend Agent: 같은 작업 패키지의 로그인 UI 보조
- Security Agent: 세션·MFA·CSRF 리뷰

### 파동 0.4

- Platform Agent: `WP-PLT-003`
- Frontend/UX Agent: `WP-UI-001`
- Integration Agent: generated client와 공통 lockfile 조정

### 파동 0.7

- DMS Agent: `WP-PLT-006`
- Collaboration Agent: `WP-PLT-007`
- QA Agent: 파일·IDOR·알림 중복 회귀 준비

### 파동 0.9

- QA·Security Agent: `WP-QA-000`
- DevOps Agent: clean restore 환경 제공
- Coordinator: Phase 1 진입 판단 자료 취합

## 17. 완료 보고서

각 에이전트의 마지막 응답은 아래 형식을 사용한다.

```text
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

`PASS`는 API 성공 resource ID, 테스트 결과, CI 링크 또는 동등한 실행 증거가 있을 때만 사용한다. 구현하지 않은 기능을 추론으로 완료 처리하지 않는다.
