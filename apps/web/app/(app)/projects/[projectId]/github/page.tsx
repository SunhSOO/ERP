import { StatBar, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { resolveMismatchAction, syncVcsAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { linkHealth, taskStatus } from "@/src/shared/ui/status";
import type { TaskStatus } from "@lep/api-client";

export const dynamic = "force-dynamic";

/** 07 깃허브 연동 상태. */
export default async function GithubPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [status, mismatches, mappings] = await Promise.all([
    gateway.getVcs(projectId),
    gateway.listMismatches(projectId),
    gateway.listMappings(projectId),
  ]);

  const health = linkHealth(status.health);
  const open = mismatches.filter((item) => !item.resolved);

  return (
    <>
      <PageHeader
        actions={
          <ActionButton action={syncVcsAction.bind(null, projectId)}>지금 동기화</ActionButton>
        }
        title="깃허브 연동"
      />

      <StatBar
        label="저장소 연동 지표"
        stats={[
          { label: "리포지토리", value: <span className="font-mono">{status.repository}</span> },
          {
            label: "연동 상태",
            value: <StatusTag tone={health.tone}>{health.label}</StatusTag>,
          },
          { label: "열린 PR", value: status.open_pull_requests },
          { label: "정합률", value: `${status.match_rate_percent}%` },
        ]}
      />

      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
        불일치 {open.length}건
      </h2>

      {open.length === 0 ? (
        // 불일치 0건은 두 가지 다른 상황이다. 전부 짝이 맞은 경우와, 짝지을
        // 것이 아예 없는 경우다. 후자를 "정합"이라 부르면 거짓말이 된다.
        mappings.length === 0 ? (
          <p className="m-0 border border-warning bg-warning-bg p-3 text-[13px] text-warning-ink">
            <span aria-hidden="true">▲ </span>
            저장소에서 WBS 태스크와 연결된 작업을 찾지 못했습니다. 브랜치나 PR 제목에 태스크
            코드를 넣으면 여기에 연결됩니다.
          </p>
        ) : (
          <p className="m-0 border border-divider p-3 text-[13px]">
            <span aria-hidden="true">● </span>
            WBS와 저장소가 정합합니다.
          </p>
        )
      ) : (
        open.map((item) => (
          <div className="flex flex-col gap-2 border border-danger p-3" key={item.id}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[14px]">{item.title}</span>
              <StatusTag tone="danger">
                {item.kind === "undefined_work" ? "미정의 작업" : "상태 불일치"}
              </StatusTag>
            </div>
            <p className="m-0 text-[13px]">{item.detail}</p>
            <div className="flex flex-wrap gap-2">
              <ActionButton action={resolveMismatchAction.bind(null, projectId, item.id)}>
                {item.kind === "undefined_work" ? "새 WBS 태스크로 등록" : "상태 재검토"}
              </ActionButton>
            </div>
          </div>
        ))
      )}

      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
        태스크 ↔ 리포 매핑
      </h2>

      <Table caption="WBS 태스크와 저장소 이슈·PR의 대응">
        <thead>
          <tr>
            <Th>WBS 태스크</Th>
            <Th>연결된 이슈/PR</Th>
            <Th>상태</Th>
            <Th>정합</Th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((mapping) => {
            const task = taskStatus(mapping.task_status as TaskStatus);
            return (
              <tr key={`${mapping.task_code ?? "none"}-${mapping.vcs_ref}`}>
                <td>
                  {mapping.task_code ? (
                    <>
                      <span className="font-mono text-[12px]">{mapping.task_code}</span>{" "}
                      {mapping.task_title}
                    </>
                  ) : (
                    <span className="text-muted">— (WBS 없음) {mapping.task_title}</span>
                  )}
                </td>
                <td className="font-mono text-[12px]">{mapping.vcs_ref}</td>
                <td>
                  <StatusTag tone={task.tone}>{task.label}</StatusTag>
                </td>
                <td>
                  <StatusTag tone={mapping.aligned ? "success" : "danger"}>
                    {mapping.aligned ? "정합" : "불일치"}
                  </StatusTag>
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </>
  );
}
