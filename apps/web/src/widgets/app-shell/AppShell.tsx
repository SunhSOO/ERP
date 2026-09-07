import type { ReactNode } from "react";
import { OfflineBanner } from "@lep/ui";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";
import type { TopBarProps } from "./TopBar";

export interface AppShellProps extends TopBarProps {
  children: ReactNode;
  badges?: { mail?: number };
}

/** 앱 셸.
 *
 * 목업의 아트보드는 1280×760 고정이었다. 상단바 48px과 좌측 메뉴 208px은 그대로
 * 두고 전체 크기만 뷰포트에 맞춘다.
 *
 * 스킵 링크가 첫 자식이다. 키보드 사용자가 메뉴를 건너뛰고 본문으로 갈 수 있어야
 * 한다는 `06_UI_UX_INFORMATION_ARCHITECTURE.md` 13절 요구다.
 */
export function AppShell({ children, badges, ...topBar }: AppShellProps) {
  return (
    <div className="grid h-dvh grid-cols-[var(--spacing-sidenav)_1fr] grid-rows-[var(--spacing-topbar)_1fr] overflow-hidden bg-bg">
      <a className="skip-link" href="#main">
        본문으로 건너뛰기
      </a>

      <TopBar {...topBar} />
      <SideNav badges={badges} />

      <main className="flex flex-col gap-4 overflow-auto px-6 py-5" id="main" tabIndex={-1}>
        <OfflineBanner />
        {children}
      </main>
    </div>
  );
}
