import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "@/src/widgets/app-shell/AppShell";
import { LocalLlmStatus } from "@/src/widgets/app-shell/TopBar";

/** 목업 화면 묶음의 기능 플래그.
 *
 * 부분적으로만 병합된 상태에서 미완성 메뉴를 노출하지 않기 위해 감싼다.
 * 플래그가 없으면 기존 자리표시자 라우트만 남는다. */
function enabled(): boolean {
  return process.env.NEXT_PUBLIC_LEP_MOCK_SCREENS === "1";
}

export default function AppLayout({ children }: { children: ReactNode }) {
  if (!enabled()) {
    notFound();
  }

  return (
    <AppShell status={<LocalLlmStatus running />} userName="김서준">
      {children}
    </AppShell>
  );
}
