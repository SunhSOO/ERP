import { notFound } from "next/navigation";
import type { ReactNode } from "react";

/** 정적 생성하면 아래 가드가 빌드 시점에 한 번만 평가돼 결과가 구워진다.
 * 그러면 런타임 환경 변수로 열 수 없다. 요청마다 판단하도록 동적으로 둔다. */
export const dynamic = "force-dynamic";

/** 개발 전용 영역.
 *
 * 운영 빌드에서는 존재하지 않는다. 컴포넌트 갤러리와 상태 전시는 개발자가
 * 보는 것이지 사용자에게 노출할 화면이 아니다.
 */
export default function DevLayout({ children }: { children: ReactNode }) {
  if (process.env.NODE_ENV === "production" && process.env.LEP_ENABLE_DEV_PAGES !== "1") {
    notFound();
  }

  return (
    <div className="mx-auto flex max-w-[1100px] flex-col gap-8 p-8">
      <header className="flex flex-col gap-1">
        <p className="text-muted m-0 text-[11px] tracking-wide uppercase">개발 전용</p>
        <nav aria-label="개발 페이지" className="flex gap-4 text-[13px]">
          <a href="/dev/components">컴포넌트</a>
          <a href="/dev/states">화면 상태</a>
        </nav>
      </header>
      {children}
    </div>
  );
}
