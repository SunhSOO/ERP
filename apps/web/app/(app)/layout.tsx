import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "@/src/widgets/app-shell/AppShell";
import { LocalLlmStatus } from "@/src/widgets/app-shell/TopBar";
import { gateway } from "@/src/shared/data/gateway";

/** 세션이 없으면 화면을 그리지 않는다. */
export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await gateway.me();

  // 백엔드가 401을 주면 `me()`가 null을 준다. 예외가 아니라 로그인이 필요한
  // 상태이므로 오류 화면이 아니라 로그인 화면으로 보낸다.
  if (!user) {
    redirect("/login");
  }

  return (
    <AppShell status={<LocalLlmStatus running={false} />} user={user}>
      {children}
    </AppShell>
  );
}
