# WP-AUDIT-20260908 — 회사 서버 기능 점검

Work Package ID: WP-AUDIT-20260908
Owned Module: QA / 운영 점검 문서
Goal: 실제 배포 상태와 승인된 PKD 범위의 기능 격차 확인
In Scope: SSH 읽기 전용 상태·코드 확인, 로컬 테스트, 우선순위 보고
Out of Scope: 운영 데이터 변경, 재배포, 기능 수정, 외부 메시지 발송
Dependencies: DECISIONS.md ADR-016~019, PKD 작업 패키지, 실행 중 컨테이너
API/Event contracts used: 현재 /api/v1 및 OpenAPI 읽기
Tables owned: 없음
Permissions affected: 없음
Migration needed: 없음
Tests required: 로컬 백엔드 회귀·경계 검사, 프론트 단위·타입 검사, 서버 비인증 HTTP 응답
Risks/assumptions: 로컬에 기존 미커밋 메일 변경이 있음. 서버와 동일하다고 가정하지 않음. 개인정보·자격증명·업무 원문은 수집하지 않음.

## 점검 결과

점검일: 2026-09-08 (KST). 회사 서버에 SSH 접속하여 실행 중 컨테이너, 내부 OpenAPI, 소스, 비인증 응답을 확인했다. 운영 데이터와 설정은 변경하지 않았다.

### 배포 상태

- 서버 저장소: `/opt/luminode/ERP`, HEAD `8313e3e`, git status clean.
- 로컬 HEAD: `e6dcfbd`. 기존 메일 관련 미커밋 변경이 있어 로컬 테스트를 서버 전체 검증과 동일시하지 않는다.
- API, web, PostgreSQL: Docker healthy. Ollama: 실행 중.
- 웹: `0.0.0.0:3000`, 로그인 페이지 HTTP 200. API·DB·Ollama 포트는 docker ps 기준 호스트 직접 노출 없음.
- API 내부 `/health/live`: 200. 세션 없는 `/api/v1/projects`, `/api/v1/ai/server`, `/api/v1/auth/me`: 모두 401.
- Ollama: `qwen3.8:27b` 모델이 100% GPU로 적재되어 있음. 실제 추론 품질·지연은 이번 점검에서 측정하지 않았다.
- 실제 어댑터 선택값: LLM=ollama, VCS=github, mail=hiworks, vault=obsidian, converter=kordoc. 선택값은 외부 서비스의 정상 동작을 보장하지 않는다.
- 프로젝트 API, 프로젝트 public 인터페이스, AI fixture, delivery API 네 파일은 실행 중 API 컨테이너와 로컬 소스의 SHA-256이 LF 정규화 후 동일했다.

### 기능 격차와 우선순위

| 우선순위 | 항목 | 확인한 근거 | 사용자 영향 / 후속 작업 |
|---|---|---|---|
| P0 | 프로젝트별 권한 검사 누락 | 실행 중 `projects/api/routes.py`는 CurrentUser로 로그인만 요구하고, 목록·상세·보관에 사용자 범위를 전달하지 않는다. `projects/public.py:require_project`는 존재 여부만 검사한다. ProjectService 목록은 전체 비보관 프로젝트를 조회한다. | 로그인한 사용자의 프로젝트 열람·보관 범위를 제한하는 정책이 없다. 멤버십·permission·범위 검사와 타 프로젝트 접근 회귀 검증 우선. 운영 객체 변경으로 재현하지는 않았다. |
| P1 | 문서 생성·드라이브 저장소 미구현 | 실행 컨테이너 `documents/public.py`가 `FixtureDocumentRepository`를 사용하고, 실제 별칭은 `EmptyDocumentRepository`. 목록은 항상 [], 단건은 None, 저장은 입력만 반환한다. OpenAPI에 문서 생성·드라이브 업로드·다운로드 API 없음. | 변환기가 설치되어 있어도 업무 문서를 등록하고 변환·보관·다운로드하는 전체 흐름이 성립하지 않는다. 영속 저장소와 업로드·생성·다운로드·버전·감사 계약 필요. |
| P1 | 태스크 기본 편집과 상태 전이 부족 | 실행 API에는 태스크 목록·생성과 조항의 태스크 승격은 있지만 태스크 수정·상태 전이 API가 없다. 마일스톤은 목록·일정 이동만 있다. | 생성 이후 담당자·기간·진행·차단·완료를 정상 업무 흐름으로 관리하기 어렵다. 승인된 PKD 상태 모델에 맞춘 수정·transition, 충돌 검사 필요. |
| P1 | AI 설정이 실제 추론 서버와 분리 | 실행 컨테이너 integrations public은 GitHub 외 기능을 fixture로 위임. fixture 서버명은 미설정, GPU는 0, 프로젝트 모델 목록은 빈 배열. 실제 Ollama는 GPU에서 모델 실행 중. | 설정 화면과 실제 상태가 다르다. 프로젝트 모델 설정은 초기 레코드가 없어 동작하지 못하며 재시작 코드도 실제 Ollama 제어가 아니다. 실측 상태 조회와 프로젝트 설정 저장·적용을 연결해야 한다. |
| P1 | 회의록 자동화 미완성 | 회의록 페이지는 볼트 notes API로 작성·조회하며 AI 결정/액션 추출 미구현을 명시한다. 별도 회의록 API 부재만으로 작성 기능이 없다고 판단하지 않았다. | 수기 회의록은 가능하나 결정·할 일 추출, 검토 후 WBS 반영은 미완성. 기존 LLM 분류 기반을 별도 수용 기준으로 확장해야 한다. |
| P2 | 홈의 GitHub 연결 표시가 고정 | 실행 `projects/api/routes.py` summary가 VCS 값을 UNKNOWN, 저장소 미연결로 고정한다. | 실제 GitHub 어댑터 설정과 홈 상태 표시가 일치하지 않을 수 있다. 통합 모듈 public 결과를 사용해야 한다. |
| P2 | 운영 문서와 현재 구현 불일치 | infra/README는 인증·영속성·LLM 어댑터가 없다고 설명하지만 최신 README 및 실행 서버에는 존재한다. PKD WP-033에도 과거 차단 사유가 남아 있다. | 현재 가능한 기능과 미구현 기능을 구분하기 어렵다. 실제 부분 구현 범위 기준으로 문서와 작업 패키지 상태 갱신 필요. |

전사 ERP의 CRM·재무·인사 등은 ADR-016에 의해 장기 ERP 트랙으로 분리되어 있다. 현재 PKD 제품의 결함과 장기 범위 미구현을 구분해야 하며, 이번 점검은 기능 추가를 승인하거나 해당 설계를 변경하지 않는다.

### 검증

- 로컬 백엔드: `.venv/Scripts/python.exe -m pytest apps/backend/tests -q --basetemp=.audit-tmp/run2 --tb=short` — 117 passed (8.97초).
- 초기 백엔드 실행은 임시 경로 접근·생성 문제로 setup 오류가 발생했다. 작업 폴더 내 부모 디렉터리를 만든 뒤 재실행하여 해소했다. 제품 오류로 분류하지 않는다.
- 프론트: `corepack pnpm test-unit` — 3개 파일, 19 passed. 최초 샌드박스 실행은 esbuild 경로 접근 오류였으며 일반 권한 재실행에서 통과했다.
- 타입 검사: `corepack pnpm typecheck` — 통과.
- 모듈 경계: `.venv/Scripts/python.exe scripts/check_boundaries.py` — 통과.
- 서버 비인증 GET 검사는 위 배포 상태 항목 참조. 웹 포트의 직접 `/api/v1/*` 호출은 404이며, Next 서버 측 API 호출 구조이므로 그 사실만으로 장애라고 판정하지 않았다.
- 테스트 통과는 현 테스트 범위 내 회귀 결과다. 프론트 테스트는 포맷·태그·리다이렉트 3개 파일에 한정되어 핵심 업무 E2E를 보장하지 않는다.

### 제한 및 후속 의존성

- 로그인 후 브라우저 조작, 실제 업무 파일 업로드·변환, 메일 수집, 외부 GitHub 호출, 재시작·복구 시험은 수행하지 않았다.
- readiness는 임시 파일 쓰기를 포함하므로 수동 호출하지 않았다. DB는 healthy 상태까지만 확인했으며 업무 테이블의 데이터는 조회하지 않았다.
- 소스상 권한 결함은 확인했지만 실제 직원 계정·타 프로젝트로 변경 요청을 보내지 않았다.
- 재배포·설정 변경·migration·업무 기능 수정 없음. 신규 산출물은 이 점검 문서다.
- 권장 순서: 프로젝트 권한 → 태스크 편집/상태 전이 → 문서/드라이브 전체 흐름 → AI 실측 설정/회의록 자동화 → 표시·문서 정합성.

Completed Work Package: WP-AUDIT-20260908 (명시한 점검 범위)
Files/Modules changed: docs/server-audit-2026-09-08.md 추가
Behavior delivered: 운영 상태와 기능 격차를 근거와 우선순위로 기록
API/Event contracts: 변경 없음
Migrations: 없음
Permissions/Audit: 운영 권한 변경 없음, 프로젝트 범위 검사 결함 기록
Tests run and results: 백엔드 117, 프론트 19 통과; 타입·모듈 경계 통과
Known limitations: 운영 인증 후 E2E·변경/복구·외부 연동 실동작 미검증
Follow-up dependencies: 위 우선순위별 수용 기준과 수정 작업 패키지

추가 기록: 프로젝트 전체 공유가 현재 코드 주석에 의도적으로 명시되어 있으므로, 이를 단순 우발 버그로 단정하지 않는다. 공통 권한 계약과의 충돌 검토를 DECISIONS.md ADR-020 (Proposed)에 남겼다. 기존 승인 결정은 변경하지 않았다. 변경 문서는 이 보고서와 DECISIONS.md 제안 항목이다.
