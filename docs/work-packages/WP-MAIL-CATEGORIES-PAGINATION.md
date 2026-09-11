# WP-MAIL-CATEGORIES-PAGINATION

Work Package ID: WP-MAIL-CATEGORIES-PAGINATION
Owned Module: mail_frontend (ADR-021, `docs/work-packages/2026-09-09-mail-approval.md`)
Goal: 메일함에서 분류 탭(미분류/프로젝트별 분류됨/제외됨/전체) 중심으로 프로젝트 범위 탐색을 두드러지게 하고, 한 페이지 노출 건수를 20으로 제한한 다음/이전 페이지 이동으로 리스트를 탐색한다.
In Scope: 메일 목록 크기(page size), 카테고리 탭 페이지 리셋 동작, 페이지네이션 회귀 테스트.
추가 반영: 관리자 전용 프로젝트 탐색(프로젝트별 분류됨), 카테고리/프로젝트 현재 항목 aria-current, 프로젝트 링크 경로 인코딩, 비관리자 교차 프로젝트 네비 비노출.
Out of Scope: 백엔드 계약 변경, 권한 정책 확장, 새로운 API/라우트 추가, 메일 승인·첨부 동작 변경.
Dependencies: `2026-09-09-mail-approval.md`, 기존 메일 승인 UI(`WP-PKD-MAIL-UI-20260909`)
API/Event contracts used: `GET /api/v1/projects/{project_id}/mail?status=...&offset=...&limit=...`
Tables owned: 없음(프론트엔드 전용).
Permissions affected: UI 편의 요소만 변경(서버 ACL은 유지).
Migration needed: 없음.
Tests required: mail page size/offset/카테고리 이동/이전-다음 링크 회귀.
Risks/assumptions: 백엔드 기본 `limit` 동작에 의존하지 않고 쿼리 파라미터로 `limit`을 항상 전달한다.

## 구현 내용

- `apps/web/src/shared/data/mail-review.ts`
  - `MAIL_PAGE_SIZE`를 `50`에서 `20`으로 낮추고 동일한 `limit` 값이 모든 메일 목록 호출에 반영되도록 유지.
- `apps/web/src/widgets/mail/mail-review.test.ts`
  - `MAIL_PAGE_SIZE` 고정값 회귀(`20`) 추가.
  - 기존 offset 제한 테스트는 새 페이지 크기 상수 기반 동작을 계속 검증.
- `apps/web/src/widgets/mail/MailPage.test.tsx`
  - 카테고리 라벨을 `프로젝트별 분류됨`으로 변경.
  - 카테고리 탭 링크가 페이지를 `1`로 재설정(`?status=...&page=1`)함을 회귀 검증.
  - 카테고리 탭 `aria-current` 접근성 확인 테스트 추가.
  - 관리자 프로젝트 네비게이션 링크에 대한 `encodeURIComponent` 적용 및 현재 프로젝트 표시 테스트 추가.
  - 비관리자에서 프로젝트 교차 네비를 렌더링하지 않음, `listProjects` 호출 미호출 검증.
- `apps/web/app/(app)/projects/[projectId]/mail/page.tsx`
  - 카테고리 네비게이션을 테두리 강조 영역으로 정리하고 현재 카테고리 제목/`페이지당 20건` 표시 추가.
  - 관리자 전용 `프로젝트별 분류됨` 네비게이션(프로젝트별 분류 탭용) 추가.
  - 현재 카테고리(`aria-current`) 및 프로젝트(`aria-current`, `status=project`에서만) 접근성 마킹 적용.
  - 페이지네이션(이전/다음) 컨트롤에 테두리 표시 추가 및 목록 바로 위 배치 유지.

## 실행 결과

- 적용 대상: 프론트엔드 메일 목록 UI만 변경.
- 관련 테스트: `apps/web/src/widgets/mail/mail-review.test.ts`, `apps/web/src/widgets/mail/MailPage.test.tsx`.
- 상태: 페이지/카테고리/프로젝트 네비게이션 UI 변경 반영 완료.
- 실행 명령(검증 요청 단계):
- `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/MailPage.test.tsx`
- `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/mail-review.test.ts`

## 총괄 최종 검증 (2026-09-09)

- 코드 작성 모델: GPT-5.3 Codex Spark. 사용자가 관련 소스/테스트 전달을 승인한 뒤 실행했다.
- `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail`: 9 files, 103 passed. 최종 JSX 수정 후 총괄이 실행 권한이 있는 환경에서 검증했다. 위 Spark 내부의 vitest 실행 제한은 이 최종 결과로 보완된다.
- `corepack pnpm --filter @lep/web typecheck`: PASS (exit 0).
- Spark 최종 `corepack pnpm --filter @lep/web lint`: PASS.
- 동작: 프로젝트별 분류됨/미분류 카테고리 표시, 관리자 프로젝트 탐색, 선택 상태 aria-current, 20건 페이지 및 이전/다음, 카테고리/프로젝트 이동 시 page=1.
- API/Event/DB migration 변경 없음. 기존 승인/첨부/권한/감사 흐름 유지.
- 한계: 운영 배포 및 실제 브라우저/스테이징 시각 검증은 수행하지 않았다. 이번 결과는 로컬 구현 및 자동 테스트 검증이다.
