# WP-PKD-001 ~ 013 Completion Report

Work Packages: WP-PKD-001, 002, 003, 004 ~ 013 (목업 화면 10장과 이를 받치는 백엔드)
Result: PASS
Track: pkd (ADR-016)
Date: 2026-09-07

## Behavior delivered

2차 화면 목업이 정의하는 제품을 동작하는 애플리케이션으로 만들었다. 화면 10장이
전부 렌더되고, 목업의 동작 버튼이 실제로 백엔드 상태를 바꾼다.

| 화면 | 라우트 | 상태 |
|---|---|---|
| 01 통합 홈 | `/home` | 완료 |
| 02 과업지시서·태스크 | `/projects/{id}/tasks` | 완료 |
| 03 WBS·일정 | `/projects/{id}/wbs` | 완료 |
| 04 지식 볼트 | `/projects/{id}/vault` | 완료 |
| 05 문서 생성·변환 | `/projects/{id}/documents` | 완료 |
| 06 메일함 | `/projects/{id}/mail` | 완료 |
| 07 깃허브 연동 | `/projects/{id}/github` | 완료 |
| 08 회의록·변경관리 | `/projects/{id}/meetings` | 완료 |
| 09 AI·로컬 LLM 설정 | `/projects/{id}/settings/ai` | 완료 |
| 10 프로젝트 드라이브 | `/projects/{id}/drive` | 완료 |

개발 전용으로 컴포넌트 갤러리(`/dev/components`)와 화면 상태 전시(`/dev/states`)를
추가했다. 운영 빌드에서는 기본적으로 404이며 `LEP_ENABLE_DEV_PAGES=1`로 연다.

## Decisions recorded

`DECISIONS.md`에 ADR 네 건을 추가했다.

- ADR-016 목업 제품 병행 트랙. ERP 설계 유지, `WP-PKD-*` ID 공간 분리, 태스크
  상태 매핑표 포함
- ADR-017 프론트엔드 스타일링은 Tailwind CSS v4
- ADR-018 통합은 포트와 어댑터로 구현
- ADR-019 접근성 우선 토큰 보정

## Files and modules changed

**결정과 계약**: `DECISIONS.md`, `docs/work-packages/pkd_work_packages.yaml`(신규),
`work_packages.yaml`의 `WP-UI-001`에 교차 참조 주석, `README.md`, `.env.example`,
`.gitignore`.

**디자인 시스템**: `packages/ui/src/styles/`에 토큰·기본·컴포넌트 CSS. 목업의
"Industry" 시스템을 이식했다. `packages/ui/src/components/`에 공유 컴포넌트 열 종,
`states/`에 화면 상태 일곱 종, `locale/format.ts`에 한국어 표시 형식.

**프론트엔드**: `apps/web/app/(app)/`에 화면 10장과 라우트별 `loading.tsx`,
`error.tsx`. `apps/web/src/widgets/app-shell/`에 앱 셸. `apps/web/src/shared/data/`에
게이트웨이와 서버 액션. `packages/api-client/`에 도메인 타입과 클라이언트.

**백엔드**: `apps/backend/src/lep/common/`에 응답 봉투, Problem Details,
페이지네이션. 도메인 모듈 여섯 개 신설.

| 모듈 | 담당 화면 |
|---|---|
| `projects` | 01 |
| `delivery` | 02, 03 |
| `knowledge` | 04, 08 |
| `documents` | 05, 10 |
| `mail` | 06 |
| `integrations` | 07, 09 |

## API changes

`/api/v1` 아래 읽기 20개와 쓰기 12개를 추가했다. 응답은
`05_API_AND_EVENT_CONTRACTS.md`의 봉투 형식을 따르고 오류는 RFC 7807 Problem
Details를 쓴다. 모든 응답에 `X-Trace-ID`가 붙으며 오류 본문의 `trace_id`와 값이 같다.

이벤트는 없다.

## Migrations

없다. 데이터베이스 스키마가 없다. 데이터는 인메모리 픽스처에서 온다(ADR-018).
영속성은 WP-PKD-020에서 붙인다.

## Permissions

없다. 인증이 아직 없다. `ForbiddenState` 컴포넌트는 만들었지만 실제 화면에는
연결하지 않고 상태 전시에서만 확인한다. 연결은 WP-PKD-021에서 한다.

## Rules enforced in code, not just documented

- 신뢰도가 낮은 과업지시서 조항은 API가 WBS 반영을 거부한다. 화면의 "검토 필요"
  라벨이 실제로 참이 된다
- 회의록 변경 반영은 미리보기와 실행이 같은 계산을 쓴다. 다이얼로그가 사용자에게
  약속한 내용과 실제 결과가 어긋날 수 없다
- 원본문서는 읽기 전용이다. 새 버전은 산출문서로 가야 한다
- 변환 실패는 실패로 저장되고 재시도 액션과 함께 노출된다. 성공으로 숨기지 않는다
- `StatusTag`에 색상 전용 속성이 없다. 색상만으로 상태를 구분하는 배지를 타입
  수준에서 만들 수 없다
- 자격증명 응답에 비밀 값 필드가 없다. 설정 여부와 상태만 담는다

## Accessibility fixes applied to the mockups

목업을 그대로 옮기지 않고 아래를 고쳤다. ADR-019와 06_UI_UX 13절 근거다.

- 잠긴 메뉴가 `pointer-events:none`을 건 실제 링크였다. 탭으로 도달하고 엔터로
  활성화되는 결함이라 `span` + `aria-disabled`로 바꾸고 사유를 연결했다
- 세그먼티드 컨트롤에 `fieldset`과 숨김 `legend`를 붙였다
- 표 헤더에 `scope`와 정렬 상태를 붙였다
- 스킵 링크와 `prefers-reduced-motion` 블록을 추가했다
- 명암비 미달 토큰 네 개를 보정했다. 보조 텍스트는 `neutral-700`(5.9:1), 기본
  버튼은 `accent-700`(6.5:1)

## Tests executed

```
uv run pytest apps/backend/tests/architecture -q     4 passed
uv run ruff check .                                  All checks passed
uv run mypy apps/backend/src apps/backend/tests scripts   113 files, no issues
uv run pytest apps/backend/tests -q                  25 passed
python scripts/check_boundaries.py                   Boundary check passed
corepack pnpm lint                                   No ESLint warnings or errors
corepack pnpm typecheck                              통과
corepack pnpm test-unit                              15 passed
corepack pnpm build                                  14 routes
powershell -File .\scripts\verify.ps1                전체 통과
```

수동 검증으로 백엔드와 프론트엔드를 띄우고 화면 12개(제품 10 + 개발 2)를 요청해
기대 문구가 렌더되는지 확인했다. 12개 전부 통과했다.

쓰기 흐름은 API 수준에서 확인했다. 저신뢰 조항 거부(409), 고신뢰 조항의 태스크
생성, 메일 지식화 후 볼트 노트 수 증가, 분류 아님 처리 후 홈 카드 수치 감소,
깃허브 불일치 해소 후 태스크 상태 전환, 변환 실패 재시도가 모두 의도대로 동작했다.

## Results

전체 게이트 통과. `scripts/verify.ps1`, `scripts/verify.sh`, `.gitlab-ci.yml` 세
러너에 `test-unit`을 같은 위치로 편입해 서로 동등하게 유지했다.

## Security and privacy review

- 픽스처는 목업의 가상 회사(다온물산·한빛테크·청람소프트)와 가상 인명만 쓴다
- 목업의 `daon-corp.co.kr`과 `seojun.kim@luminode.local`은 실재하는 주소로 읽힐 수
  있어 픽스처에서 제거했다
- 자격증명 API가 비밀 값을 담지 않는다는 것을 테스트로 고정했다
- 저장소에 비밀 패턴 일치가 없다
- 외부 서비스를 호출하는 테스트가 없다

## Known limitations

- **서버 액션의 브라우저 종단 검증이 남았다.** 화면의 버튼은 서버 액션으로 백엔드
  쓰기를 부른다. 타입 검사와 빌드는 통과했고 같은 흐름을 API 수준에서 검증했지만
  브라우저에서 버튼을 눌러 확인하지는 않았다. 수동 확인을 권한다
- **Playwright를 넣지 않았다.** 계획에는 있었으나 CI에 브라우저 이미지를 추가해야
  하고 이 환경에서 다운로드 성공을 확인할 수 없어 보류했다. 단위 테스트만 세 러너에
  편입했다
- **좌측 메뉴의 메일 뱃지를 연결하지 않았다.** 목업은 메일함에 건수 뱃지를 단다.
  앱 셸이 프로젝트 컨텍스트를 모르는 구조라 추가 배선이 필요해 남겼다
- **폰트를 자체 호스팅하지 않았다.** Barlow와 Barlow Condensed는 시스템에 설치된
  경우에만 적용된다. `next/font/google`은 빌드 시 네트워크를 타는데 빌드가 CI 하드
  게이트라 넣지 않았다. 폰트 파일 반입이 필요하다
- **반응형 최소 폭을 정하지 않았다.** 목업은 고정 1280×760이다. 좁은 화면의 메뉴
  동작과 최소 지원 폭 결정이 남았다
- **hwpx 미리보기는 재현이다.** 실제 변환은 kordoc 어댑터가 붙는 WP-PKD-030에서
  동작한다
- **목업 익스포트 57MB가 저장소에 들어온다.** `UI mockups/exports/`의 11개 파일이
  각각 5.4MB다. 저장소 크기 관점에서 별도 보관을 검토할 만하다

## Handoff

다음은 WP-PKD-020 영속성이다. `infra/`에 Compose와 PostgreSQL을 올리고 모듈별
SQLAlchemy 저장소 어댑터를 추가한다. 도메인 계층은 손대지 않는다. 경계 검사기가
도메인의 SQLAlchemy 임포트를 막으므로 구조가 자동으로 지켜진다. 픽스처 어댑터는
테스트와 데모용으로 남긴다.

그 뒤 WP-PKD-021에서 ERP 트랙의 WP-PLT-002 인증을 연결하고, 자격증명 저장 화면을
연다. 실연동 어댑터는 그다음이며 착수 전에 아래 입력이 필요하다.

| 어댑터 | 필요한 입력 |
|---|---|
| kordoc | 설치 위치와 호출 방식 |
| 깃허브 | 개인 액세스 토큰과 대상 저장소 |
| 옵시디언 | 볼트 경로 |
| 로컬 LLM | 사내 GPU 추론 서버 주소와 사양 |
| 하이웍스 | 계정과 API 접근 권한 |
