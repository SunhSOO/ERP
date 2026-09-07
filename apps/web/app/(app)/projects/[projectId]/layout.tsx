import type { ReactNode } from "react";
import { gateway } from "@/src/shared/data/gateway";

export const dynamic = "force-dynamic";

/** 프로젝트 컨텍스트.
 *
 * 존재하지 않는 프로젝트면 여기서 걸린다. 하위 화면이 각자 확인할 필요가 없다.
 * 어느 프로젝트를 보고 있는지 상단에 고정해 화면을 옮겨도 맥락이 사라지지
 * 않게 한다.
 */
export default async function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await gateway.getProject(projectId);

  return (
    <>
      <div className="text-muted flex flex-wrap items-center gap-2 text-[12px]">
        <span className="font-mono">{project.code}</span>
        <span aria-hidden="true">·</span>
        <span>{project.name}</span>
        <span aria-hidden="true">·</span>
        <span>PM {project.pm_name}</span>
        <span aria-hidden="true">·</span>
        <span>{project.role === "vendor" ? "용역사" : "발주사"}</span>
      </div>
      {children}
    </>
  );
}
