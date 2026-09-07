import {
  EmptyState,
  ForbiddenState,
  PartialFailureNotice,
  Skeleton,
} from "@lep/ui";
import { ErrorStateDemo, OfflineDemo, StaleDemo } from "@/src/widgets/dev/StateDemos";

/** 일곱 가지 화면 상태 전시.
 *
 * `06_UI_UX_INFORMATION_ARCHITECTURE.md` 6절이 모든 화면에 요구하는 상태다.
 * 여기서 한자리에 모아 두면 규칙이 문서에만 있지 않고 눈으로 확인된다.
 */

function Case({
  title,
  rule,
  children,
}: {
  title: string;
  rule: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="m-0 text-[15px]">{title}</h2>
      <p className="text-muted m-0 text-[12px]">{rule}</p>
      {children}
    </section>
  );
}

export default function StatesGallery() {
  return (
    <>
      <h1 className="m-0 text-[22px]">화면 상태</h1>

      <Case rule="스켈레톤만 쓴다. 전체 화면 스피너를 쓰지 않는다." title="Loading">
        <Skeleton lines={4} />
      </Case>

      <Case
        rule="데이터 없음과 필터 결과 없음은 다른 상황이다. variant가 필수라 뭉뚱그릴 수 없다."
        title="Empty — 데이터 없음"
      >
        <EmptyState
          description="회의록을 올리면 AI가 결정과 액션아이템을 추출합니다."
          title="아직 회의록이 없습니다"
          variant="no-data"
        />
      </Case>

      <Case rule="다음 행동이 필터 초기화다. 생성이 아니다." title="Empty — 필터 결과 없음">
        <EmptyState
          description="다른 분류를 선택하거나 파일을 올려 보세요."
          title="이 분류에 파일이 없습니다"
          variant="no-results"
        />
      </Case>

      <Case rule="추적 ID와 재시도가 필수 속성이다." title="Error">
        <ErrorStateDemo />
      </Case>

      <Case
        rule="필요한 권한과 문의 대상이 필수 속성이다. 본문 안에서 렌더해 셸을 살린다."
        title="Forbidden"
      >
        <ForbiddenState
          contact="시스템 관리자"
          description="이 프로젝트의 자격증명은 관리자만 볼 수 있습니다."
          requiredPermission="integrations.credential.read"
        />
      </Case>

      <Case rule="보고 있는 데이터가 언제 것인지 숨기지 않는다." title="Stale">
        <StaleDemo />
      </Case>

      <Case rule="저장 가능 여부를 명시한다. 실제 오프라인일 때만 보인다." title="Offline">
        <OfflineDemo />
      </Case>

      <Case
        rule="위젯 하나가 실패해도 화면 전체를 막지 않는다."
        title="Partial failure"
      >
        <PartialFailureNotice traceId="9f2c1a44-0b3e-4c77-9a21-6e0f5b2d8c10" what="예산 소진율" />
      </Case>
    </>
  );
}
