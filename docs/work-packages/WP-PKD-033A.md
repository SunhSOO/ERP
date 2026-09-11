# WP-PKD-033A — 로컬 LLM 런타임 상태 (읽기 전용)

- Track: `pkd`
- Parent: WP-PKD-033 (로컬 LLM 어댑터, 조항 분류·회의록 추출은 범위 밖)
- 관련 감사: `docs/server-audit-2026-09-08.md` P1 "AI 설정이 실제 추론 서버와 분리"
- 상태: `DONE` (033A 읽기 전용 범위의 로컬 검증 완료, 운영 실측·배포 제외)

## 작업 시작 절차 (AGENTS.md 4절)

```text
Work Package ID: WP-PKD-033A
Owned Module: apps/backend/src/lep/modules/integrations (LLM 런타임 포트/어댑터만)
Goal: 실제로 선택된 ollama 서버의 연결·설치·적재 모델 상태를 읽기 전용으로 보고한다.
      추론·모델 로드/언로드/재시작은 이 작업의 범위가 아니다.
In Scope:
  - domain/entities.py: LlmRuntimeStatus, LlmRuntimeSnapshot, LlmServer 확장
  - domain/ports.py(신규): LlmRuntimePort
  - infrastructure/llm_runtime.py(신규): FixtureLlmRuntimeAdapter, OllamaLlmRuntimeAdapter
  - application/services.py: IntegrationService.server()/.credentials()가 런타임 포트를 사용하도록 배선,
    restart_model()을 프로젝트 확인 후 항상 409로 거부하도록 변경
  - public.py: LlmRuntimePort 선택 배선(_llm_runtime_adapter), VCS 선택과 독립
  - api/routes.py: ServerOut에 status/detail/available_model_names/running_model_names/
    nullable gpu_usage_percent·active_model_count 반영
  - apps/web AI 설정 화면: 재시작 버튼/문구 제거, null-safe 통계, 설치/실행 모델 명 표시,
    격리 보장 문구 축소
  - packages/api-client/src/domain.ts: LlmServer/LlmRuntimeStatus 타입만 변경(메일 변경 보존)
  - apps/backend/tests/test_ai_runtime.py(신규)
  - apps/web/src/widgets/ai/AiSettingsPage.test.tsx(신규)
Out of Scope:
  - 실제 추론 호출, 모델 pull/로드/언로드/재시작 제어
  - GPU 사용률 측정(두 조회 API 모두 값을 주지 않음)
  - 프로젝트별 모델 설정의 영속화(정책 미승인, 기존 인메모리 픽스처 유지)
  - VCS/문서/메일/볼트 어댑터 변경
  - 인증/권한 모델 변경(CurrentUser 읽기 인증 유지)
Dependencies: ADR-018(포트-어댑터), 기존 llm_choice/llm_base_url/llm_model(common/adapters.py)
API/Event contracts used: GET /api/v1/ai/server, GET /api/v1/projects/{id}/integrations,
  POST /api/v1/projects/{id}/ai/restart (기존 경로, 가짜 성공 대신 409 거부)
Tables owned: 없음 (영속화 없음)
Permissions affected: 없음. 기존 CurrentUser 읽기 인증 유지.
Migration needed: 없음
Tests required: httpx.MockTransport 기반 어댑터 단위 테스트, API 직렬화·인증·재시작 거부 테스트
Risks/assumptions:
  - Ollama가 OpenAI 호환 /models와 자체 /api/ps를 계약대로 응답한다고 가정한다.
  - LinkHealth enum에 "연결 불가"에 해당하는 전용 값이 없어 UNAVAILABLE을 MISMATCH로,
    DEGRADED를 STALE로 매핑했다. 프론트 공용 상태 라벨(apps/web/src/shared/ui/status.ts)은
    이번 작업의 소유 파일이 아니라 값을 새로 추가하지 않았다.
```

## 요청/응답 변경

### `GET /api/v1/ai/server`

기존 `gpu_usage_percent: int`, `active_model_count: int` 두 필드를 nullable로 바꾸고
다음 필드를 추가했다.

| 필드 | 타입 | 의미 |
|---|---|---|
| `status` | `"connected" \| "degraded" \| "unavailable" \| "fixture" \| "not_configured"` | 런타임 프로브 결과 |
| `detail` | `string` | 안전한 요약 사유(원격 서버의 원문 오류를 담지 않음) |
| `gpu_usage_percent` | `int \| null` | 항상 `null`. `/models`·`/api/ps` 어디에도 GPU 사용률이 없다 |
| `active_model_count` | `int \| null` | `/api/ps`로 적재 확인된 모델 수. 측정 실패 시 `null`(0으로 위장하지 않음) |
| `available_model_names` | `string[]` | `/models`가 보고한 설치된 모델 이름 |
| `running_model_names` | `string[]` | `/api/ps`가 보고한 적재된 모델 이름 |

기존 `name`, `network_note`, `project_count`는 그대로다.

### `GET /api/v1/projects/{id}/integrations`

`kind: "llm"` 행의 `health`/`detail`/`missing_input`이 이제
`LlmRuntimePort.snapshot()` 결과로 계산된다. 이전에는 어댑터 선택과 무관하게
항상 `not_configured`로 하드코딩돼 있었다.

### `POST /api/v1/projects/{id}/ai/restart`

프로젝트 존재 확인(404) 이후 항상 `409 STATE_CONFLICT`를 반환한다. 이전 구현은
가짜 `RUNNING` 상태를 즉석에서 만들어 반환했다. 실제 재시작 제어 호출이 없으므로
그 응답은 사실이 아니었다. 프론트 AI 설정 화면에서 재시작 버튼과 관련 액션 임포트를
제거했다.

## 제한 사항 (정직하게 기록)

- **GPU 사용률은 절대 측정되지 않는다.** OpenAI 호환 `/models`와 Ollama `/api/ps`
  어느 쪽도 GPU 사용률을 보고하지 않는다. 화면은 항상 `미측정`을 보여준다.
- **재시작·로드·언로드·pull 제어가 없다.** 이번 작업은 상태를 읽기만 한다. 관련
  버튼을 프론트에서 제거했고 백엔드 엔드포인트는 항상 거부한다.
- **프로젝트별 모델 배정은 영속화되지 않는다.** `docs/server-audit-2026-09-08.md`가
  지적한 대로 정책이 아직 승인되지 않았다. 기존 인메모리 픽스처를 그대로 두었다.
- **처리·격리 보장 문구를 제거했다.** 이 단계는 상태 조회만 제공한다. 프로젝트별 모델 저장과 처리 경로 적용은 구현되지 않았으며, 화면에 해당 제한을 표시한다.
- **`LinkHealth`에 전용 "연결 불가" 값이 없다.** UNAVAILABLE→`mismatch`,
  DEGRADED→`stale`로 매핑했다. 배지 색상·라벨이 완벽히 들어맞지 않을 수 있으나
  `detail` 문자열이 실제 상태를 설명한다. `apps/web/src/shared/ui/status.ts`는 공용
  파일이라 이번 작업에서 값을 추가하지 않았다.
- **httpx 타임아웃은 5초로 짧게 고정했다.** 설정 화면의 상태 조회이지 추론 호출이
  아니므로, 서버가 느리거나 멈춰 있어도 화면이 오래 걸리지 않게 했다.
- **운영 서버 실동작은 검증하지 않았다.** 모든 어댑터 검증은 HTTP fixture로 실행했다. 백엔드 전체 210개와 AI 전용 27개 통과, 전체 mypy 141개 소스·ruff·모듈 경계 통과를 조정자와 독립 리뷰어가 확인했다. 프론트 최종 결과는 아래 완료 보고에 기록한다.

## 독립 리뷰 반영 (2026-09-09)

두 독립 리뷰어가 지적한 6건을 모두 반영했다.

1. **잘못된 행이 있어도 성공한 빈 목록처럼 보였다.** `_parse_models`/`_parse_running`이
   형식이 안 맞는 항목이나 빈 문자열 `id`/`name`을 조용히 건너뛰었다. 이제 한 항목이라도
   딕셔너리가 아니거나 `id`/`name`이 없거나 공백이면 그 조회 전체를 실패(`None`)로
   본다. 진짜로 빈 배열(`{"data": []}`)은 여전히 유효한 0건으로 취급한다.
   `test_a_malformed_model_row_fails_the_whole_installed_probe`,
   `test_a_blank_model_id_fails_the_whole_installed_probe`,
   `test_a_malformed_running_row_fails_the_running_probe_not_zero`,
   `test_a_mix_of_valid_and_invalid_model_rows_is_still_a_failed_probe`,
   `test_a_legitimately_empty_model_list_is_a_real_zero_not_a_failure`.
2. **`httpx.InvalidURL`은 `httpx.HTTPError`의 하위 클래스가 아니라 잡히지 않았다.**
   `_fetch`에 별도 `except httpx.InvalidURL` 분기를 추가했고, 생성자에서 스킴이
   `http`/`https`가 아니면(빈 스킴 포함) 요청을 시도하지 않고 즉시
   `NOT_CONFIGURED`로 답한다. 두 경로 모두 설정값 원문이나 시크릿을 `detail`에
   담지 않는다. `test_malformed_configured_url_is_not_configured_without_leaking_it`,
   `test_non_http_scheme_is_not_configured_not_attempted`,
   `test_invalid_url_raised_by_the_transport_is_handled_not_a_500`.
3. **`/ai/server`, `/projects/{id}/integrations`가 `async def`인데 동기 httpx
   호출을 한다.** 두 라우트만 `def`로 바꿔 FastAPI 스레드풀에서 실행되게 했다.
   다른 라우트는 건드리지 않았다. `test_ai_server_route_is_sync_so_fastapi_uses_the_threadpool`,
   `test_list_credentials_route_is_sync_so_fastapi_uses_the_threadpool`.
4. **"확인할 수 없음"과 "실측된 0개"가 화면에서 구분되지 않았다.** AI 설정 화면에서
   설치된 모델 목록은 `status`가 `connected`/`degraded`일 때만(즉 `/models` 조회가
   실제로 성공했을 때만) 빈 목록을 "설치된 모델이 없습니다"로 보여주고, 그 외에는
   "확인할 수 없습니다"를 유지한다. 적재된 모델 목록은 `connected`일 때만 실측된
   0건으로 표시한다. 프로젝트별 모델 배정 표에 빈 상태 행을 추가했다. "이 프로젝트의
   모델" 카드 문구에서 조항 분류 등 현재 구현 범위에 배정이 적용된다는 주장을
   제거했다 — 033A는 상태를 읽기만 하며, 배정은 저장도, 실제 처리 경로 연결도 되어
   있지 않다.
5. **`network_note`가 검증되지 않은 약속을 했고, 하단 문구가 낡았다.** "문서·메일
   조항 분류는 사내 서버의 로컬 모델에서만 이루어지며 외부로 전송되지 않는다"는
   설정값 출처만으로는 증명할 수 없는 주장이었다. `설정된 추론 서버의 연결 상태와
   모델 목록을 조회합니다. 프로젝트별 모델 저장·적용 기능은 아직 제공되지 않습니다.`로
   바꿨다. 하단 "인증이 들어오는 WP-PKD-021 이후" 문구도 인증이 이미 있는 지금
   시점에는 사실이 아니어서 `이 화면에서는 연결 상태만 조회합니다. 연결 설정 변경은
   관리자에게 문의해 주세요.`로 바꿨다. 제품 화면에 남은 WP 번호 언급은 제거했다.
6. **`credentials()`/`IntegrationService` 시그니처 변경의 하위 호환성.** 픽스처·
   깃허브 어댑터의 `credentials(project_id, converter, llm)`과
   `IntegrationService(adapter, llm_runtime)` 모두 세 번째/두 번째 인자가 필수였다.
   두 인자만 넘기는 기존 방식의 직접 호출도 계속 동작하도록 `llm`에
   `NOT_CONFIGURED` 기본값(`_DEFAULT_LLM_CREDENTIAL`)을, `llm_runtime`에
   `FixtureLlmRuntimeAdapter()` 기본값을 주었다. `public.py`의 실제 배선은 항상
   두 값을 명시적으로 넘기므로 동작이 바뀌지 않는다. 기존 테스트는 변경하지 않았다.
   `test_fixture_adapter_credentials_still_works_with_two_positional_args`.

## 완료 보고 (AGENTS.md 20절)

```text
Completed Work Package: WP-PKD-033A
Files/Modules changed:
  - apps/backend/src/lep/modules/integrations/domain/entities.py
  - apps/backend/src/lep/modules/integrations/domain/ports.py (신규)
  - apps/backend/src/lep/modules/integrations/infrastructure/llm_runtime.py (신규)
  - apps/backend/src/lep/modules/integrations/infrastructure/fixtures.py
  - apps/backend/src/lep/modules/integrations/infrastructure/github_vcs.py
  - apps/backend/src/lep/modules/integrations/application/services.py
  - apps/backend/src/lep/modules/integrations/public.py
  - apps/backend/src/lep/modules/integrations/api/routes.py
  - apps/backend/tests/test_ai_runtime.py (신규)
  - apps/web/app/(app)/projects/[projectId]/settings/ai/page.tsx
  - packages/api-client/src/domain.ts (LlmServer/LlmRuntimeStatus만)
  - docs/work-packages/WP-PKD-033A.md (신규, 이 문서)
Behavior delivered:
  - LEP_ADAPTER_LLM=ollama로 실제 선택된 경우 OpenAI 호환 /models와 Ollama 네이티브
    /api/ps를 읽기 전용·짧은 타임아웃으로 조회해 연결·설치·적재 모델 상태를 보고한다.
  - 픽스처 상태는 fixture/not_configured로 정직하게 보고하며, 실제 어댑터 실패도
    unavailable/degraded로 보고한다. GPU 사용률과 측정 불가 active_model_count는
    항상 null이며 0으로 꾸미지 않는다.
  - /ai/server, /projects/{id}/integrations가 VCS 어댑터 선택과 무관하게 이 런타임
    스냅샷을 사용한다.
  - 재시작 API는 프로젝트 확인 후 항상 409 STATE_CONFLICT. 프론트 재시작 버튼 제거.
  - AI 설정 화면이 null-safe 통계, 설치/실행 모델 이름, 실제 상태 조회 범위를 설명하는 문구를 보여준다.
API/Event contracts: GET /api/v1/ai/server 응답 필드 확장(위 표), 나머지 경로는
  응답 스키마만 바뀌고 경로·메서드는 그대로.
Migrations: 없음
Permissions/Audit: 변경 없음. 기존 CurrentUser 읽기 인증 유지.
Tests run and results: 백엔드 전체 210 passed (9.36s), AI 전용 27 passed (독립 리뷰 1.29s).
  mypy 전체 141 source files 통과, ruff backend src/tests/scripts 통과, 모듈 경계 검사 통과.
  프론트 전체 25 passed (신규 AI 화면 6 포함, 1.56s), pnpm typecheck 통과.
  AI page·테스트 ESLint 통과(저장소 eslintrc 모드), pnpm build 통과(총괄 실행).
  초기 pytest 임시 부모경로 누락은 폴더 생성 후 해소. Vitest 샌드박스 esbuild 경로 제한은
  일반 권한 실행으로 해소. 신규 UI 중복 모델명 선택자 실패는 카드 범위 선택으로 수정 후 통과.
Known limitations: 위 "제한 사항" 절 참조. 추가로: `httpx.URL(...)`을 이용한 스킴
  검증은 http/https만 허용하며, 하위 계층의 `httpx.InvalidURL`도 별도 처리한다. 두 경로는 fixture 테스트로 검증했으며 실제 서버 환경은 미검증이다.
Follow-up dependencies:
  - WP-PKD-033 본편(조항 분류·회의록 추출에 실제 모델 연결)
  - 프로젝트별 모델 배정 영속화 정책 승인 및 구현
  - LinkHealth에 런타임 전용 상태값 추가 여부 결정(공용 파일 소유자 검토 필요)
```


