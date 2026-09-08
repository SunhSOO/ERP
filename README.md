# Luminode ERP Platform

저장소는 두 트랙을 병행 관리한다. ADR-016 참조.

- **ERP 트랙** — `docs/specs`의 99화면 전사 ERP 설계와 `work_packages.yaml`의 71개
  작업 패키지. 장기 목표로 유지한다. WP-PLT-001 저장소 기반만 구현됐다.
- **pkd 트랙** — 2차 화면 목업이 정의하는 프로젝트 지식·문서 자동화 제품.
  `pkd_work_packages.yaml`에 작업 패키지가 있다. 현재 개발이 진행 중인 쪽이다.

사용자·세션·MFA와 Compose 기반처럼 제품 중립인 산출물은 두 트랙이 공유한다.

## 저장소 구조

```text
apps/backend/       FastAPI 애플리케이션과 백엔드 테스트
apps/web/           Next.js 애플리케이션
packages/ui/        디자인 토큰과 공유 React 컴포넌트
packages/api-client/ 도메인 타입과 백엔드 호출 클라이언트
packages/           그 밖의 공유 TypeScript 설정
infra/              Compose와 운영 매니페스트 자리 (WP-OPS-001)
tests/              교차 패키지와 종단 테스트 공간
docs/specs/         승인된 설계·구현 명세
docs/design/        화면 디자인 브리프
docs/work-packages/ 작업 패키지 계약
UI mockups/         Claude Design 캔버스 익스포트. 화면의 기준이다
scripts/            부트스트랩, 검증, 경계 검사
```

## 로컬 검증

```text
uv sync
uv run pytest apps/backend/tests -q
uv run ruff check .
uv run mypy apps/backend/src apps/backend/tests scripts
python scripts/check_boundaries.py

corepack pnpm install --frozen-lockfile
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test-unit
corepack pnpm build
```

전체를 한 번에 돌리는 명령은 `scripts/verify.sh`와 `scripts/verify.ps1`이다. 두
스크립트와 `.gitlab-ci.yml`은 서로 동작이 같아야 한다.

계정과 프로젝트는 데이터베이스에 남는다. 개발 장비에서는 SQLite로 충분하고,
서버는 `infra/docker-compose.yml`이 PostgreSQL을 띄운다. Redis와 MinIO는 아직
쓰지 않는다. 외부 연동은 ADR-018의 포트와 어댑터를 따른다.

## 애플리케이션 실행

백엔드와 프론트엔드를 각각 띄운다.

```text
uv run uvicorn lep.bootstrap.app:app --app-dir apps/backend/src --env-file .env --reload
corepack pnpm --filter @lep/web dev
```

`.env.example`을 참고해 `.env`와 `apps/web/.env.local`을 만든다. 백엔드는
`LEP_DATABASE_URL`이 없으면 뜨지 않는다. 어느 저장소에 쓰는지 추측하지 않는다.

`.env`는 자동으로 읽히지 않는다. 위 명령의 `--env-file .env`가 그 일을 한다.
빼면 변수가 없다며 기동을 거부한다.

첫 접속은 가입 화면으로 간다. 이 서버의 **첫 계정이 관리자**가 되고, 이후 가입은
누구나 할 수 있다. 프로젝트는 하나도 없는 상태로 시작하며, 만들면 지식 볼트에
프로젝트 코드 이름의 폴더가 하나 생긴다.

주요 경로는 다음과 같다. `<id>`는 만든 프로젝트의 식별자다.

```text
/signup                                 가입 (첫 계정이 관리자)
/login                                  로그인
/home                                   통합 홈
/projects/<id>/wbs                      WBS·일정
/projects/<id>/tasks                    과업지시서·태스크
/projects/<id>/vault                    지식 볼트
/projects/<id>/documents                문서 생성·변환
/projects/<id>/drive                    프로젝트 드라이브
/projects/<id>/mail                     메일함
/projects/<id>/github                   깃허브 연동
/projects/<id>/meetings                 회의록
/projects/<id>/settings/ai              AI·로컬 LLM 설정
/dev/components                         컴포넌트 갤러리 (개발 전용)
/dev/states                             화면 상태 전시 (개발 전용)
```

## 외부 연동 연결

연동은 포트와 어댑터로 구현했다(ADR-018). 기본값은 전부 픽스처이고, 환경 변수로
실제 어댑터를 켠다. 설정이 빠진 채로 켜면 픽스처로 남으면서 그 사유를 화면 09에
표시한다. 조용히 대체하지 않는다.

| 연동 | 상태 | 필요한 것 |
|---|---|---|
| kordoc 문서 변환 | 연결됨 | CLI 경로 또는 npx |
| 깃허브 | 연결됨 | 개인 액세스 토큰, 대상 저장소 |
| 옵시디언 볼트 | 연결됨 | 볼트 폴더 경로 |
| 하이웍스 메일 | 연결됨 | 계정과 IMAP 비밀번호 |
| 로컬 LLM | 미구현 | GPU 추론 서버 (WP-PKD-033) |

세 가지를 한 번에 켜는 예시다. 토큰은 저장소에 넣지 않는다.

```bash
export LEP_ADAPTER_CONVERTER=kordoc
export LEP_KORDOC_CLI="C:/경로/kordoc/dist/cli.js"

export LEP_ADAPTER_VCS=github
export LEP_GITHUB_TOKEN="$(gh auth token)"
export LEP_GITHUB_REPO=SunhSOO/ERP

export LEP_ADAPTER_VAULT=obsidian
export LEP_OBSIDIAN_VAULT="C:/경로/볼트"
```

**kordoc**은 마크다운을 공문서 양식 HWPX로 만드는 Node CLI다. 원본은
[chrisryugj/kordoc](https://github.com/chrisryugj/kordoc)이고 npm 패키지 이름도
`kordoc`이다. 로컬 체크아웃의 `dist/cli.js`를 node로 실행하거나
`LEP_KORDOC_USE_NPX=1`로 npx를 쓴다.

**깃허브** 어댑터는 저장소의 PR·이슈·브랜치를 읽어 WBS와 대조한다. 태스크 코드로
짝을 짓는데 `TSK-1234`와 `WP-PLT-001` 두 형태를 인식한다. 저장소에서 감지됐지만
WBS에 없는 작업과, WBS상 완료인데 PR이 열려 있는 항목을 구분해 보고한다.

**옵시디언 볼트**는 로컬 마크다운 폴더다. 노트를 읽고 `[[위키링크]]`에서 백링크
색인을 만든다. 편집은 옵시디언에서 하고 여기서는 읽기와 노트 생성만 한다. 같은
이름의 파일이 있으면 덮지 않는다.

**하이웍스 메일**은 그룹웨어 API 신청 없이 표준 IMAP으로 읽는다. 하이웍스에서
`메일 > 환경설정 > 기본 설정`의 POP3/IMAP을 먼저 켜야 한다. 읽기 전용으로
접속하므로 메일을 지우거나 읽음 표시를 남기지 않는다. 발신 도메인으로 프로젝트를
분류하고, 의도 판정은 아직 모델이 아니라 키워드 규칙이라 신뢰도를 낮음으로 낸다.

## 사내 서버 배포

우분투 서버에 올리는 방법은 [infra/README.md](infra/README.md)에 있다. 서버에
미리 깔아야 할 것은 도커뿐이다. kordoc, 옵시디언 앱, 한컴 오피스, Node, 파이썬을
설치하지 않는다.

```bash
git clone https://github.com/SunhSOO/ERP.git
cd ERP/infra && cp .env.example .env && $EDITOR .env
./deploy.sh
```

## API

`GET /health/live`는 프로세스 생존 여부만 반환한다. 업무 API는 `/api/v1` 아래에
있고 `docs/specs/05_API_AND_EVENT_CONTRACTS.md`의 응답 봉투와 RFC 7807 오류 형식을
따른다. 모든 응답에 `X-Trace-ID`가 붙는다.

## 모듈 소유권

백엔드 모듈 소유자는 자기 모듈 안에서만 작업한다. 다른 모듈은 그 모듈의 `public.py`만
임포트할 수 있고 내부 구현은 임포트할 수 없다. 도메인 계층은 FastAPI, SQLAlchemy,
Redis, MinIO를 임포트할 수 없다. 규칙은 `scripts/check_boundaries.py`가 강제하며
`docs/architecture/module-boundaries.md`에 설명돼 있다.

외부 연동은 포트와 어댑터로 구현한다. 도메인은 포트만 알고, 픽스처 어댑터와 실제
어댑터를 환경 변수로 교체한다.

공유 잠금 파일, 생성 API 클라이언트, OpenAPI 출력, 공통 UI 토큰은 Integration Agent
또는 지정된 공유 파일 소유자의 승인이 필요하다.
