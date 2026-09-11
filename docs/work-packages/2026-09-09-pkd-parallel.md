# 2026-09-09 PKD 개선 병렬 작업 분담

## 실행 계약

- 사용자 요청: 작업을 서브에이전트에 분리하고 제품 코드는 Claude Code Sonnet medium으로 구현한다.
- Claude Code 2.1.265의 `--model sonnet --effort medium` 호출 성공 확인. 현재 sonnet 별칭은 claude-sonnet-5로 해석된다.
- Codex 조정자는 조사·프롬프트·테스트·리뷰를 담당하고 제품 코드를 직접 작성하지 않는다. 수정 요청도 동일 Claude 모델로 위임한다.
- 각 Claude 실행에는 Read/Glob/Grep/Edit/Write만 허용한다. 쉘·테스트 실행은 조정자가 수행한다. 권한 우회 옵션과 모델 fallback을 사용하지 않는다.
- 기존 미커밋 메일 변경은 보존한다. 같은 checkout에서 파일 소유권을 분리하고 공유 파일은 총괄이 순서를 지정한다.
- 운영 서버의 설정·데이터·배포 및 실제 외부 서비스 호출은 이번 구현 실행 범위에 포함하지 않는다.
- 실제 자격증명, 고객/직원 데이터, vault 원문은 하위 작업에 전달하지 않는다.

## 작업 패키지

| 패키지 | 담당 | 산출물 | 의존성 / 현재 단계 |
|---|---|---|---|
| WP-PKD-ACL-20260909 | 총괄 / Claude 공통기반 | 프로젝트 permission·범위, 감사, migration 계약 | 사용자에게 공유 조회 유지 vs 멤버 제한 정책 질문 중. 결정 전 정책 종속 구현 금지 |
| WP-PKD-WBS-20260909 | wbs_claude | 태스크 편집·상태 전이·낙관적 잠금·WBS UI | 먼저 독립 domain 규칙과 테스트 구현. API는 ACL/migration 계약 이후 |
| WP-PKD-DMS-20260909 | documents_claude | 문서 영속성·업로드/스캔·불변 버전·변환·다운로드 | 먼저 변환 산출물 덮어쓰기 버그 해결. API는 ACL/migration/object/scan 계약 이후 |
| WP-PKD-AI-20260909 | ai_claude | 실제 LLM 상태·프로젝트 모델 설정·회의록 검토/반영 | 먼저 실측 읽기/정직한 상태 표시. 설정 쓰기·회의 반영은 ACL/delivery 계약 이후 |
| WP-PKD-INTEGRATION-20260909 | 총괄 / Claude 통합 | 공유 타입·모델 등록·홈 GitHub 상태·운영 문서·전체 검증 | 담당별 단계 산출물 수령 후 |

## 1차 독립 구현 경계

### WBS 도메인

Work Package ID: WP-PKD-WBS-RULES-20260909
Owned Module: delivery/domain
Goal: PKD 태스크 편집 및 전이 규칙을 서버 도메인에 정의
In Scope: 순수 상태·편집 검증과 단위 테스트
Out of Scope: 권한 정책 선택, DB/API/UI 연결, 운영 변경
Dependencies: ADR-016, 기존 delivery/domain/entities.py
API/Event contracts used: 이번 단계 없음
Tables owned: 없음
Permissions affected: 없음
Migration needed: 없음
Tests required: 허용/불허 전이, 차단 필수값, 날짜 역전, VCS_ONLY 경계
Risks/assumptions: 규칙 구현만으로 화면 기능이 완성되지 않음

### 문서 변환 산출물

Work Package ID: WP-PKD-DMS-ARTIFACT-20260909
Owned Module: documents/domain/ports.py, documents/infrastructure/kordoc_converter.py
Goal: latest.hwpx 덮어쓰기 제거와 검증 가능한 고유 산출물 제공
In Scope: 고유 경로·체크섬·크기/내용 검증, 기존 convert 계약 호환, mock 테스트
Out of Scope: 업무 파일 실변환, 신규 문서 API, 사용자 파일 다운로드 공개
Dependencies: 기존 kordoc converter
API/Event contracts used: 기존 convert 호출자 호환
Tables owned: 없음
Permissions affected: 없음
Migration needed: 없음
Tests required: 두 변환 결과 독립, 출력 누락·실패·경로 안전성, 기존 계약 호환
Risks/assumptions: 파일 반환은 내부 계약이며 권한 검증된 다운로드는 후속 단계

### AI 읽기 상태

Work Package ID: WP-PKD-AI-STATUS-20260909
Owned Module: integrations, AI 설정 page, 공용 타입의 AI 관련 부분만
Goal: 실행 중 LLM 상태를 fixture와 구분해 표시
In Scope: 모델 목록/적재 상태 읽기, 오류/미측정 표시, 가짜 재시작 성공 제거
Out of Scope: 실제 모델 재시작, 프로젝트 모델 쓰기, 회의 자동 반영
Dependencies: 기존 LLM 설정값과 CurrentUser 인증
API/Event contracts used: /api/v1/ai/server 및 /api/v1/ai/models 호환 검토
Tables owned: 없음
Permissions affected: 현재 읽기 인증 유지
Migration needed: 없음
Tests required: fake transport 정상/timeout/잘못된 응답/미설정, 타입검사
Risks/assumptions: GPU 메모리 적재량과 GPU 사용률은 다른 값이며 추정치로 사용률을 만들지 않음

## 후속 통합 원칙

1. 권한 정책은 질문에 대한 응답과 DECISIONS.md에 승인된 범위로 확정한다.
2. 기존 DB 변경은 새 migration으로 처리한다. create_all이 기존 컬럼을 변경한다고 가정하지 않는다.
3. 변경 API는 사용자 범위·감사·낙관적 잠금·선택 execute idempotency를 포함한다.
4. 스캐너 미설정/실패는 격리 상태이며 성공으로 표시하지 않는다.
5. 회의록은 추출 근거·원문 해시·승인된 선택 payload가 고정된 미리보기 후에만 WBS를 만든다.
6. 부분 단계의 테스트 통과를 전체 기능 완성으로 보고하지 않는다.

## 1차 검증 결과

- 기존 회귀 기준: 신규 담당 테스트를 제외한 백엔드 117 passed (9.20초).
- WBS 독립 규칙: 48 passed, 지정 파일 ruff/mypy 통과, 문서 담당 교차 리뷰 완료. API·DB·UI 미연결. 상세: `docs/WP-PKD-WBS-EDIT-20260909.md`.
- 문서 artifact: 신규 18 + 기존 adapter 42 = 60 passed, 지정 3파일 ruff/mypy 통과. WBS 담당 리뷰의 포트 호환/OSError/부분 파일 정리 지적 반영.
- WBS·문서와 기존 전체 백엔드 통합(신규 AI 테스트 제외): 183 passed (9.11초).
- AI 033A: 실제 상태 조회/화면/오류 처리 및 독립 리뷰 완료. 백엔드 신규 27개와 프론트 신규 6개 테스트 포함. 프로젝트 모델 설정 저장·회의록 자동화는 후속 단계다.

### 문서 artifact 완료 보고

Completed Work Package: WP-PKD-DMS-20260909-A (내부 변환 산출물 단계)
Files/Modules changed: documents/domain/ports.py, documents/infrastructure/kordoc_converter.py, tests/test_document_artifacts.py
Behavior delivered: UUID 고유 파일, exclusive binary 저장, SHA-256/크기/경로 반환, 이전 산출물 보존, 실패 결과 정제
API/Event contracts: 기존 convert(markdown, template) 반환 계약 유지; 별도 ArtifactCapableConverterPort 추가
Migrations: 없음
Permissions/Audit: 공개 다운로드나 권한 변경 없음; 부분파일 정리 실패 시 비밀 없는 경고
Tests run and results: 신규+기존 adapter 60 passed (0.41초), ruff/mypy 통과
Known limitations: 문서 DB·스캔·ready·다운로드 API 미연결; 파일 정리 자체 실패 시 부분 파일이 남을 수 있으나 성공/참조를 반환하지 않음; 실제 kordoc 미실행
Follow-up dependencies: ACL, 문서 저장소·스캔·migration·UI 계약


## 최종 통합 인계 — 2026-09-09

**이번에 완료한 것은 위 세 개의 독립 1차 단계이며, 전체 기능 보완의 완료가 아니다.**

- 코드 작성 및 리뷰 지적 수정은 모두 Claude Code `--model sonnet --effort medium`으로 위임했다. JSONL assistant 메시지의 모델은 `claude-sonnet-5`로 확인했다. Codex 담당자는 조사·리뷰·테스트 실행·문서·정리를 수행했다.
- WBS: 순수 편집/전이 규칙만 준비됨. 기존 WBS 화면에서 태스크 편집이 가능해진 것은 아니다.
- 문서: 실제 변환기의 기존 latest.hwpx 덮어쓰기 버그 수정 및 내부 산출물 계약 개선. 문서 저장·업로드/스캔·다운로드 전체 흐름은 후속 구현이다.
- AI: 실측 상태 조회·미측정과 0 구분·가짜 재시작 성공 제거·화면 설명 개선이 연결됨. 프로젝트 설정 저장·모델 적용·회의록 추출/승인·홈 GitHub 상태는 후속 구현이다.
- 프로젝트 권한은 공유 조회 유지와 멤버 제한 중 사용자 응답 대기. 기존 정책 변경, DB migration, 운영 데이터 변경, 배포는 수행하지 않았다.
- 기존 미커밋 메일 변경을 보존했다. 공용 API client의 이번 변경은 AI 상태 타입 부분이다.

### 최종 실행 검증

- 총괄 백엔드 전체: `.venv/Scripts/python.exe -m pytest apps/backend/tests -q --basetemp=.pytest_cache/pkd-20260909/parent-final --tb=short` — **210 passed (9.24초)**.
- 총괄 프론트 전체: `corepack pnpm test-unit` — **25 passed, 4 files (2.00초)**. AI 화면 신규 6개 포함.
- 전체 mypy: **141개 소스 파일 오류 없음**.
- 전체 Ruff: **All checks passed**. 초기 두 오류는 임시폴더에 생성된 경계검사 실패 예제였으며 제품 코드를 고쳐 숨기지 않고 임시 산출물을 정리해 해소했다.
- 프론트 lint/typecheck 및 모듈 경계 검사 통과.
- 빌드: 최종 헤더 문구와 UI 테스트 반영 후 `corepack pnpm build` 재실행 성공(exit 0). 컴파일·lint·타입 검사·정적 페이지 생성·build tracing까지 통과.
- 운영 서버·실제 외부 연동·실제 kordoc·스테이징 E2E는 실행하지 않았다.

### 계약과 운영상 제한

- `/api/v1/ai/server`: 연결 상태·설치/적재 모델 필드 추가. GPU 사용률과 적재 모델 수는 미측정일 때 null. 프론트/백엔드 배포 시 함께 반영해야 한다.
- 모델 재시작 요청은 실제 제어가 구현되기 전까지 409로 거부한다.
- 이벤트/DB migration/프로젝트 권한 정책 변경 없음.
- 문서 산출물은 UUID 경로로 남으며 기존 산출물을 덮지 않는다. 파일 정리 자체 실패 시 참조 없는 부분파일은 남을 수 있다.
- 실행 프롬프트·Claude JSONL·테스트 임시 산출물은 gitignored `.pytest_cache/pkd-claude-runs-20260909` 및 `.pytest_cache/pkd-wbs-scratch-20260909`에 보관했다. 자격증명이나 실제 업무 원문은 하위 작업에 전달하지 않았다.

Completed Work Package: 독립 1차 WBS 규칙 / DMS artifact / AI 033A
Files/Modules changed: delivery domain, documents converter/ports, integrations runtime/API, AI page 및 공유 AI 타입, 관련 테스트와 작업 문서
Behavior delivered: 위 1차 단계에 한함
API/Event contracts: AI 상태 스키마 확장, 재시작 409; 이벤트 변경 없음
Migrations: 없음
Permissions/Audit: 기존 읽기 인증 유지, 프로젝트 정책 변경 없음
Tests run and results: 백엔드210/프론트25 및 위 정적검사
Known limitations: 권한·WBS 편집 API/UI·문서 전체 흐름·프로젝트 모델 설정·회의 자동화·GitHub 홈 상태·운영 검증 미완료
Follow-up dependencies: 권한 범위 확정, 공통 audit/낙관적잠금/migration 계약, 각 후속 패키지 통합


추가 형식 점검: 이번 변경 대상의 `git diff --check`는 통과했다. 전체 diff 검사에는 기존 미커밋 메일 fixtures.py의 EOF 빈 줄 1건이 있어 기록만 남기고 해당 파일을 수정하지 않았다.
