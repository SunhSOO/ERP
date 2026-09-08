import Link from "next/link";
import { AiPanel, Card, CardTitle, EmptyState, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { applyMeetingAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";

export const dynamic = "force-dynamic";

const APPLY_STATUS = {
  pending: { tone: "warning", label: "반영 대기" },
  applied: { tone: "success", label: "반영 완료" },
  dismissed: { tone: "idle", label: "반영 안 함" },
} as const;

/** 08 회의록 → 지식화·변경관리. */
export default async function MeetingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ meeting?: string }>;
}) {
  const { projectId } = await params;
  const { meeting: selectedId } = await searchParams;

  const meetings = await gateway.listMeetings(projectId);

  if (meetings.length === 0) {
    return (
      <>
        <PageHeader title="회의록" />
        <EmptyState
          description="회의록을 올리면 AI가 결정과 액션아이템을 추출합니다."
          title="아직 회의록이 없습니다"
          variant="no-data"
        />
      </>
    );
  }

  const detail = await gateway.getMeeting(selectedId ?? meetings[0].id);
  const { meeting, decisions, action_items: actionItems, preview } = detail;
  const pending = meeting.apply_status === "pending";

  return (
    <>
      <PageHeader title="회의록" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(240px,320px)_1fr]">
        <section aria-label="회의록 목록" className="flex flex-col gap-2">
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {meetings.map((item) => {
              const status = APPLY_STATUS[item.apply_status];
              return (
                <li key={item.id}>
                  <Link className="block no-underline" href={`?meeting=${item.id}`}>
                    <Card className={item.id === meeting.id ? "border-accent" : undefined}>
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="font-mono text-[12px]">{item.code}</span>
                        <span className="text-muted text-[11px]">
                          {item.held_at.slice(5, 10)}
                        </span>
                      </div>
                      <CardTitle>{item.title}</CardTitle>
                      <StatusTag tone={status.tone}>
                        {item.apply_status === "pending"
                          ? `${status.label} ${item.pending_count}`
                          : status.label}
                      </StatusTag>
                    </Card>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>

        <section aria-label="회의록 상세" className="flex flex-col gap-4">
          <div>
            <h2 className="m-0 text-[17px]">
              {meeting.code} · {meeting.title}
            </h2>
            <p className="text-muted m-0 text-[12px]">
              {meeting.held_at.slice(0, 16).replace("T", " ")} · 참석{" "}
              {meeting.attendees.join(", ")}
            </p>
          </div>

          <h3 className="text-muted m-0 text-[11px] tracking-wide uppercase">AI 추출 결정</h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {decisions.map((decision) => (
              <li className="flex flex-wrap items-center gap-2 text-[13px]" key={decision.id}>
                <span className="font-mono text-[12px]">결정 #{decision.ordinal}</span>
                <span className="flex-1">{decision.text}</span>
                <StatusTag tone={decision.applied ? "success" : "warning"}>
                  {decision.applied ? "반영됨" : "WBS 반영 대기"}
                </StatusTag>
              </li>
            ))}
          </ul>

          <h3 className="text-muted m-0 text-[11px] tracking-wide uppercase">액션아이템</h3>
          <Table caption="회의에서 나온 액션아이템">
            <thead>
              <tr>
                <Th>내용</Th>
                <Th>담당</Th>
                <Th>기한</Th>
                <Th>상태</Th>
              </tr>
            </thead>
            <tbody>
              {actionItems.map((item) => (
                <tr key={item.id}>
                  <td>{item.text}</td>
                  <td>{item.owner ?? <span className="text-muted">미지정</span>}</td>
                  <td className="tabular-nums">
                    {item.due ?? <span className="text-muted">즉시</span>}
                  </td>
                  <td>
                    {/* "완료"는 실제 결과가 있을 때만 쓴다. 승인 대기는 승인 대기로 표시한다. */}
                    <StatusTag tone={item.task_created ? "success" : "warning"}>
                      {item.task_created ? "업무 생성됨" : "승인 필요"}
                    </StatusTag>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          {preview.milestone_code && preview.new_end ? (
            <AiPanel
              actions={
                pending ? (
                  <>
                    <ActionButton
                      action={applyMeetingAction.bind(null, projectId, meeting.id, "wbs")}
                      variant="primary"
                    >
                      WBS에 반영
                    </ActionButton>
                    <ActionButton
                      action={applyMeetingAction.bind(
                        null,
                        projectId,
                        meeting.id,
                        "vault_only",
                      )}
                    >
                      볼트에만 지식화
                    </ActionButton>
                    <ActionButton
                      action={applyMeetingAction.bind(null, projectId, meeting.id, "dismiss")}
                    >
                      무시
                    </ActionButton>
                  </>
                ) : null
              }
              title="변경 반영 미리보기"
            >
              <p className="m-0">
                {preview.milestone_code} 마일스톤 기한을{" "}
                <strong className="tabular-nums">{preview.new_end}</strong>로 변경하면 후행 업무{" "}
                {preview.shifts.length}건의 기한도 함께 밀립니다.
              </p>
              {preview.shifts.length > 0 ? (
                <ul className="m-0 mt-2 flex list-none flex-col gap-1 p-0 text-[12px]">
                  {preview.shifts.map((shift) => (
                    <li key={shift.task_code}>
                      <span className="font-mono">{shift.task_code}</span> {shift.task_title} —{" "}
                      <span className="tabular-nums">{shift.old_end}</span>
                      <span aria-hidden="true"> → </span>
                      <span className="tabular-nums">{shift.new_end}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </AiPanel>
          ) : null}
        </section>
      </div>
    </>
  );
}
