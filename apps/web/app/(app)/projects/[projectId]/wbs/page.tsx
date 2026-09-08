import Link from "next/link";
import { StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { taskStatus } from "@/src/shared/ui/status";
import { GanttGrid } from "@/src/widgets/wbs/GanttGrid";

export const dynamic = "force-dynamic";

/** 03 WBS·일정 보드. */
export default async function WbsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ view?: string }>;
}) {
  const { projectId } = await params;
  const { view } = await searchParams;
  const excelView = view === "excel";

  const [milestones, tasks, mismatches] = await Promise.all([
    gateway.listMilestones(projectId),
    gateway.listTasks(projectId),
    gateway.listMismatches(projectId).catch(() => []),
  ]);

  const open = mismatches.filter((item) => !item.resolved);

  return (
    <>
      <PageHeader
        actions={
          <>
            {/* 보기 전환을 URL에 남긴다. AGENTS.md 11절. */}
            <Link
              aria-current={excelView ? undefined : "page"}
              className="btn btn-secondary btn-sm"
              href="?"
            >
              Gantt
            </Link>
            <Link
              aria-current={excelView ? "page" : undefined}
              className="btn btn-secondary btn-sm"
              href="?view=excel"
            >
              Excel 보기
            </Link>
          </>
        }
        title="WBS · 일정"
      />

      {open.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3 border border-danger bg-danger-bg p-3 text-danger-ink">
          <span aria-hidden="true">✕</span>
          <span className="text-[13px]">
            깃허브 리포와 <strong>{open.length}건</strong> 불일치.{" "}
            {open.map((item) => item.title).join(", ")}.
          </span>
          <Link className="text-[13px]" href={`/projects/${projectId}/github`}>
            깃허브 연동 →
          </Link>
        </div>
      ) : null}

      {excelView ? (
        <Table caption="WBS 태스크 목록">
          <thead>
            <tr>
              <Th>코드</Th>
              <Th>제목</Th>
              <Th>상태</Th>
              <Th>시작</Th>
              <Th>종료</Th>
              <Th>담당</Th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => {
              const { tone, label } = taskStatus(task.status);
              return (
                <tr key={task.id}>
                  <td className="font-mono text-[12px]">{task.code}</td>
                  <td>{task.title}</td>
                  <td>
                    <StatusTag tone={tone}>{label}</StatusTag>
                  </td>
                  <td className="tabular-nums">{task.start}</td>
                  <td className="tabular-nums">{task.end}</td>
                  <td>{task.assignee ?? <span className="text-muted">미지정</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : (
        <GanttGrid milestones={milestones} tasks={tasks} />
      )}

      <p className="text-muted m-0 text-[12px]">
        점선 막대는 WBS에 정의되지 않았지만 깃허브에서 감지된 작업입니다. 흐린 막대는 완료
        표시됐지만 PR이 병합되지 않은 작업입니다.
      </p>

      {tasks.some((task) => task.status === "blocked") ? (
        <section aria-label="차단된 태스크" className="flex flex-col gap-2">
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">차단 사유</h2>
          {tasks
            .filter((task) => task.status === "blocked")
            .map((task) => (
              <p className="m-0 border border-divider p-3 text-[13px]" key={task.id}>
                <span className="font-mono">{task.code}</span> {task.title} —{" "}
                {task.blocked_reason} 해소 담당 {task.blocked_owner}.
              </p>
            ))}
        </section>
      ) : null}
    </>
  );
}
