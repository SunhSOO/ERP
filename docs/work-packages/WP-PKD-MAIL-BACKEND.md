# WP-PKD-MAIL-BACKEND

Work Package ID: WP-PKD-MAIL-APPROVAL-20260909 / backend
Owned Module: mail, schema registry, mail migration, project home mail count bridge
Goal: 사람의 승인 후에만 메일 프로젝트 분류와 선택 첨부 연결을 확정
In Scope: 추천/확정 분리, 영속 승인 및 목록 snapshot, mailbox key, 승인/제외/CAS/idempotency/감사, 권한 검사, 첨부 checksum, pagination/counts, 기존 지식화 제한
Out of Scope: 실제 메일 조회/발송/삭제, 서버 배포, 전체 프로젝트 권한 정책, 일반 첨부 복사/스캔
Dependencies: ADR-021, docs/work-packages/2026-09-09-mail-approval.md; documents.public 등록 계약
API/Event contracts used: 위 승인 문서의 /api/v1 mail endpoints; documents.public.register_mail_attachments; 이벤트 없음
Tables owned: mail 승인/감사 및 필요한 snapshot 테이블만. documents 테이블 직접쓰기 금지.
Permissions affected: active admin 검토, active admin/프로젝트 생성자 승인 메일 읽기
Migration needed: 신규 테이블 additive, scripts/migrate_mail_review.py --apply 명시, 기존 테이블 불변
Tests required: fixture만 사용한 승인/미승인/첨부선택/권한/재시작/rollback/idempotency/hash/분류목록 회귀 + ruff/mypy/경계/전체회귀
Risks/assumptions: approved 원문 snapshot은 명시 컬럼/attachment 관계로 저장하여 POP3 최근 300건 밖에서도 목록을 보존한다. 첨부 원본 삭제시 다운로드 불가. 핵심 메타데이터 JSONB 저장/바이너리 저장 없음.

진행 상태: 승인된 설계에 따라 회귀 테스트부터 Claude Code Sonnet medium에게 위임했다. 제품/테스트 코드는 Claude가 작성하고 조정자는 코드 검토·검사 실행·이 문서만 작성한다. `.pytest_cache/mail-review-runs`는 권한 거부되어 workspace `.mail-review-runs`를 임시 로그 경로로 사용한다. 운영 접속 및 외부 원본 요청은 하지 않는다.

## 실패 재현 및 검토

- 첫 API 회귀 실행: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py -q --basetemp=.mail-review-runs/red --tb=short` — 6 failed. 승인 endpoint 부재404, 추천/연결/승인 응답필드 부재 및 adapter 자동 project_id 확정을 재현했다.
- adapter 선택 회귀: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_real_adapters.py -q -k 'mail or domain or intent or overlay' --basetemp=.mail-review-runs/adapter-red --tb=short` — 1 failed, 3 passed. 도메인 매칭이 추천이 아니라 project_id를 채우는 결함을 재현했다.
- 추가 승인 범위: 이미 승인한 메일의 미연결 첨부도 `/attachments/approve`에서 같은 프로젝트로만 연결한다. version/CAS/idempotency/감사 및 선택 첨부 hash 계약은 초기 승인과 같다.
- 다운로드는 optional linked_file_id를 확인하여 계정 교체 후 동일 UIDL이 재사용되어도 과거 드라이브 링크가 새 계정 파일을 가리키지 않도록 한다.
- 총괄/교차 리뷰는 SQLite 첫 SAVEPOINT의 외부 rollback, idempotency 결과의 전체 연결집합 보존, DB 제약/인덱스, 목록의 SQL pagination 및 원본 POP3 호출 횟수를 중점으로 검토한다.

## 중단 및 인계 요청 (2026-09-09)

사용자가 현재 작업을 정리·인계한 뒤 중단하고 토큰을 절감하도록 요청했다. 진행 중인 마지막 Claude 호출만 마친 뒤 필수 범위 검사를 실행하고 코드 동결한다. 새 구현 호출은 시작하지 않는다.

- 현재 확보 검증: 메일 승인 pytest46개 통과(13.57s), scoped mypy18파일 통과, 모듈 경계 통과. 이는 마지막 호출 직전 결과이며 최종 결과는 아래에 별도로 기록한다.
- UIDL transport 제한: DB/MailOut/source_mail_id는 raw UIDL이다. UIDL에 `/` 등이 포함되면 기존 path parameter가 동작하지 않을 수 있다. 총괄은 optional `id_encoding=base64url` query로 path 식별자만 엄격히 복원하는 호환 확장안을 정했지만 사용자 중단 요청으로 착수하지 않았다. UI/백엔드 일괄 후속 작업과 synthetic `/ ? #` roundtrip 테스트가 필요하다.
- 운영 배포, 실제 하이웍스/외부 연동 조회, production migration은 실행하지 않았다.

### Claude 재개 정보

실제 Claude session_id: `ec4b6fa9-5af9-404a-87c5-77c47fff40a7` (도구 프로세스 session24802와 다른 값).

후속 사용자 승인 후 재개한다면 stdin 프롬프트를 전달하고 다음 조건을 유지한다: `claude -p --resume ec4b6fa9-5af9-404a-87c5-77c47fff40a7 --model sonnet --effort medium --output-format stream-json --verbose --restricted --tools Read,Glob,Grep,Edit,Write --permission-mode acceptEdits --strict-mcp-config`. 모델 대체·Bash·권한 우회 옵션을 추가하지 않는다. 제품 및 테스트 코드 작성은 계속 Claude가 맡고, 조정자는 검사 실행·검토·문서만 담당한다.

마지막 로그: `.mail-review-runs/backend-final.jsonl`; 프롬프트: `.mail-review-runs/backend-final-prompt.md`. `release-src`는 부모가 만든 독립 baseline이므로 검색·편집에서 제외한다.

## 동결 시점 최종 검증과 인계

마지막 Claude 호출은 저장된 파일 수정 이후 `Failed to authenticate: OAuth session expired and could not be refreshed`로 종료했다(`is_error=true`, exit1). 사용자 중단 지시에 따라 재인증·추가 코드 호출을 하지 않았다. 작업 코드는 현재 상태로 동결한다.

최종 1회 검사:

- `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py -q --basetemp=.mail-review-runs/handoff --tb=short`: **52 passed (14.12s)**. 승인/추가첨부/제외, 권한, 재시작·목록, 원본 hash, linked_file_id, rollback, 동시 키 충돌, 지식화 후 최초응답 replay, migration dry-run/apply/reapply 및 실패 sanitize 회귀 포함.
- `.venv/Scripts/python.exe -m mypy apps/backend/src/lep/modules/mail apps/backend/tests/test_mail_approval.py scripts/migrate_mail_review.py`: **18 source files 통과**.
- `.venv/Scripts/python.exe scripts/check_boundaries.py`: **통과**.
- scoped ruff: **1건 실패** — `apps/backend/tests/test_mail_approval.py:1708`의 I001 import 정렬. 제품 코드 오류는 발견되지 않았으나 이 품질 게이트는 미완료다. 사용자 중단 요청으로 직접/추가 Claude 수정하지 않았다.
- 검사 원문은 `.mail-review-runs/backend-handoff-{pytest,mypy,ruff}.txt`에 있다.

수정 파일: mail `api/routes.py`, `application/services.py`, `domain/entities.py`, 신규 `domain/ports.py`, `infrastructure/fixtures.py`, `infrastructure/hiworks_pop3.py`, 신규 `infrastructure/models.py`, `public.py`; 공통 `common/schema.py` 모델 등록; `projects/api/routes.py` 홈 mail count 호출만; `tests/test_real_adapters.py` 메일 분류 기대값; 신규 `tests/test_mail_approval.py`, `scripts/migrate_mail_review.py`; 이 인계 문서. 기존 미커밋 메일 첨부/타 모듈 변경은 보존했다.

남은 작업:

1. Claude 인증 복구 후 동일 session_id 및 Sonnet medium 조건으로 test I001 1건만 보완하고 필요한 게이트 재확인.
2. 사용자 중단으로 미착수한 raw UIDL 특수문자 transport 호환 확장과 frontend 동시 연결·회귀.
3. 전체 통합/독립 release baseline 검사 및 실제 PostgreSQL·스테이징 검증 결과는 총괄 인계에서 확인. 이 조정자는 scoped fixture 검사만 실행했으며 운영 배포/실제 메일/production migration을 하지 않았다.
4. vault 파일쓰기와 DB commit은 단일 분산 트랜잭션이 아니다. 지식화 CAS 선점으로 동시 중복 실행은 막지만 외부 파일쓰기 후 DB commit 실패 복구는 후속 운영 검토가 필요하다.

Completed Work Package: WP-PKD-MAIL-BACKEND 구현 인계 및 동결(전체 릴리스 완료 아님)
Behavior delivered: DB 승인 권위, 추천 분리, 선택 첨부 참조, 명시 승인/제외/추가첨부, 권한·CAS·idempotency·감사·hash 검증·페이지/건수
API/Event contracts: 승인 문서 기준 endpoint 및 linked_file_id query, OpenAPI synthetic 예제. 이벤트 없음.
Migrations: 신규 mail5+documents1 테이블 additive migration 스크립트. fixture dry-run/apply/reapply 통과; 운영 적용 없음.
Permissions/Audit: active admin 검토, active admin/해당 프로젝트 생성자 승인 메일 읽기, 성공 command/download 감사
Tests run and results: pytest52/mypy18/경계 통과, ruff I001 한 건 남음
Known limitations: 위 남은 작업 및 OAuth 종료
Follow-up dependencies: 사용자 재개 요청, Claude 인증 복구, scoped lint 정리 및 통합 릴리스 검증

### 사용자 재개 후 최초 호출 결과

기존 UUID를 `--resume --model sonnet --effort medium`으로 한 번 재개했으나 OAuth session expired/refresh 실패로 즉시 exit1 종료됐다. 인증 실패 시 재시도하지 말라는 총괄 지시에 따라 추가 호출하지 않았다. 이번 재개에서 제품/테스트 코드는 변경되지 않았으며 Ruff I001 한 건, `AI 분석` 문구 정정, UIDL 특수문자 transport 보완은 그대로 남아 있다. 변경이 없으므로 통과했던 검사를 반복하지 않았다. 실행 근거: `.mail-review-runs/backend-uidl.jsonl`, 전달 프롬프트: `.mail-review-runs/backend-uidl-prompt.md`.
