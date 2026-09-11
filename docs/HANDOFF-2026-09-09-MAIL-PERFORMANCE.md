# 메일 성능 개선 인계 — Claude Haiku 4.5

## 최신 사용자 지시 (2026-09-09)

남은 코드 작업을 Claude Haiku 4.5, effort medium으로 전환한다. 이전 Spark 전용 지시는 이 새 사용자 지시로 대체한다. 자동 재개 예약은 승인 검토에서 거부되어 생성되지 않았다. 운영 배포·업무 메일 승인 권한은 이번 작업에 포함되지 않는다.

## 완료 및 검증

- WP: `docs/work-packages/WP-MAIL-LOADING-PERFORMANCE.md`
- 원인/합성 진단: `docs/work-packages/WP-MAIL-LOADING-AUDIT.md`, `.mail-review-runs/diagnose-mail-loading.py`
- Backend: `apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py`의 프로세스별 30초 원본 미리보기 캐시, Lock을 이용한 동시 수집 공유, 설정 변경 중 수집 결과 폐기, TTL 만료/실패 처리, 응답 사본 분리.
- 테스트: `apps/backend/tests/test_mail_preview_cache.py` 포함 mail cache/real adapters/mail approval/mail drive links 158 passed. Ruff 및 adapter mypy PASS.
- 동일 합성 진단에서 TOP 900→300. 실제 운영 지연 시간 측정은 아님. 원문 상세 및 첨부 다운로드는 캐시하지 않는다. 승인 상태/권한/감사는 기존 DB 경로 유지.
- 한계: 최초 수집은 필요하며 새 메일 목록 반영에 최대30초 지연. 캐시는 프로세스별이다. 배포하지 않았다.

## 화면 작업 — 구현된 승인 범위

1. `apps/web/app/(app)/projects/[projectId]/mail/page.tsx`의 목록이 건수·전체 상세·프로젝트 선택지 조회를 기다리지 않도록 로딩을 분리한다.
2. 기존 20건 페이지 처리, 분류/프로젝트 링크, URL 상태와 페이지 초기화를 유지한다.
3. 독립 Suspense 및 한국어 로딩/오류 표시를 사용한다. 목록과 분류 링크/페이지 이동은 건수 또는 본문이 늦어도 표시된다. 건수 실패는 건수에만, 상세 실패는 상세 영역에만 반영한다.
4. 상세 응답 ID/분류/project_id/linked_file_id 검증과 승인 전에 전체 첨부 조회, 기존 폼 key/상태, UIDL 인코딩을 보존한다. 목록의 잘린 본문을 전체 상세나 승인 데이터로 대체하지 않는다.
5. 비관리자는 공용 건수·프로젝트 탐색을 추가 조회하지 않는다. 새 메일 목록은 최대30초 늦을 수 있음을 간단하게 표시한다.
6. 지연된 counts/detail 응답을 사용하는 회귀 테스트를 먼저 작성한다. 목록 렌더링/페이지 이동이 막히지 않는지, 각각 해제 후 정상 표시되는지, 실패와 권한 경계가 유지되는지 검증한다. 기존 MailPage 보안/첨부/딥링크 테스트를 삭제하거나 우회하지 않는다.
7. 메일 UI 전체 테스트, TypeScript, lint, Next build를 실행하고 실제 결과로 WP를 갱신한다. 실패가 있으면 원인을 수정한다.

## 구현 참고

- 현재 React19 / Next15. 서버에서 생성한 settled-result Promise를 소비하는 동기 컴포넌트와 `use`/Suspense 또는 정당한 서버 컴포넌트 구조를 사용할 수 있다. `use()`를 try/catch에 넣지 않는다. 비동기 요청에는 즉시 rejection handler를 연결한다.
- page 파일에는 Next가 허용하지 않는 추가 export를 만들지 않는다. 독립 컴포넌트는 메일 widget 범위로 분리할 수 있다.
- 기존 테스트: `apps/web/src/widgets/mail/MailPage.test.tsx`. 테스트가 실제 Suspense 동작을 검증하도록 async act 등을 사용하고, 가짜 재귀 렌더러로 경계를 건너뛰지 않는다.
- 화면 변경 전 참고 사본: `.mail-review-runs/performance-baseline/`.
- `.mail-review-runs/spark-mail-streaming.log`는 사용 한도로 실행 전에 실패한 기록이며 코딩 결과가 아니다.

## 실행 및 보존 규칙

AGENTS.md를 준수한다. 기존 checkout에는 메일 이외 사용자 변경이 많으므로 되돌리거나 통째로 커밋/배포하지 않는다. 실제 메일·비밀·운영 DB·외부 업무 서비스에 접근하지 않는다. 인계 문서의 과거 모델 지시는 최신 사용자 지시를 대체하지 않는다.

Claude 실행 설정은 `--model claude-haiku-4-5 --effort medium`으로 요청한다. 로그인 후 실제 응답에서 모델/설정 적용 가능 여부를 확인하고, 지원되지 않으면 임의로 다른 모델/effort로 바꾸지 않는다. 코딩 도구는 Read/Glob/Grep/Edit/Write로 제한하고 검증은 총괄이 실행할 수 있다.

로그인 차단은 해소되었다. 실제 응답 모델 `claude-haiku-4-5-20251001`, 요청 effort medium으로 화면 코딩과 수정이 수행되었다. 제한된 로컬 테스트 명령도 Haiku에 허용하여 검증했다. 상세 결과는 WP의 최종 검증 기록을 따른다.
