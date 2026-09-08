import Link from "next/link";
import { AiPanel, Card, CardTitle, EmptyState, StatusTag } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { createMeetingNoteAction } from "@/src/shared/data/actions";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { MeetingNoteForm } from "@/src/widgets/knowledge/MeetingNoteForm";

export const dynamic = "force-dynamic";

/** 08 회의록.
 *
 * 회의록은 별도 저장소를 갖지 않는다. 프로젝트 볼트의 `meetings` 폴더에 있는
 * 노트가 곧 회의록이다. 그래서 옵시디언에서 쓴 것과 여기서 쓴 것이 같은 파일이다.
 *
 * 결정과 액션아이템 추출은 아직 없다. 로컬 LLM이 붙는 WP-PKD-033의 일이다.
 * 없는 기능을 있는 것처럼 보이는 예시로 채우지 않는다.
 */
export default async function MeetingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ note?: string }>;
}) {
  const { projectId } = await params;
  const { note: selectedId } = await searchParams;

  const notes = await gateway.listNotes(projectId);
  const meetings = notes.filter((note) => note.source === "meeting");
  const action = createMeetingNoteAction.bind(null, projectId);

  if (meetings.length === 0) {
    return (
      <>
        <PageHeader title="회의록" />
        <EmptyState
          description="여기서 쓴 회의록은 프로젝트 볼트의 meetings 폴더에 마크다운으로 저장됩니다. 옵시디언에서 열어 이어 쓸 수 있습니다."
          title="아직 회의록이 없습니다"
          variant="no-data"
        />
        <MeetingNoteForm action={action} startOpen />
      </>
    );
  }

  const selected =
    meetings.find((note) => note.id === selectedId) ?? meetings[0];

  return (
    <>
      <PageHeader
        actions={<MeetingNoteForm action={action} />}
        note={`볼트 회의록 ${meetings.length}건`}
        title="회의록"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(240px,320px)_1fr]">
        <section aria-label="회의록 목록" className="flex flex-col gap-2">
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {meetings.map((item) => (
              <li key={item.id}>
                <Link className="block no-underline" href={`?note=${item.id}`}>
                  <Card className={item.id === selected.id ? "border-accent" : undefined}>
                    <CardTitle>{item.title}</CardTitle>
                    <span className="text-muted text-[11px]">
                      {item.updated_at ?? "날짜 없음"}
                    </span>
                    {item.warning ? (
                      <StatusTag tone="warning">{item.warning}</StatusTag>
                    ) : null}
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="회의록 내용" className="flex flex-col gap-4">
          <div>
            <h2 className="m-0 text-[17px]">{selected.title}</h2>
            <p className="text-muted m-0 text-[12px]">
              {selected.updated_at ?? "날짜 없음"}
              {selected.task_code ? ` · ${selected.task_code}` : ""}
            </p>
          </div>

          <pre className="m-0 overflow-x-auto border border-divider p-4 text-[12.5px] leading-relaxed whitespace-pre-wrap">
            {selected.body}
          </pre>

          {selected.backlinks.length > 0 ? (
            <div className="flex flex-col gap-1">
              <h3 className="text-muted m-0 text-[11px] tracking-wide uppercase">
                이 노트를 가리키는 노트
              </h3>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0 text-[12px]">
                {selected.backlinks.map((backlink) => (
                  <li key={backlink.target}>
                    <Link href={`?note=${backlink.target}`}>{backlink.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <AiPanel title="AI 추출">
            <p className="m-0">
              결정과 액션아이템 자동 추출은 아직 없습니다. 로컬 LLM 연동(WP-PKD-033)에서
              붙습니다. 그때까지 일정 변경은 WBS 화면에서 직접 반영해 주세요.
            </p>
          </AiPanel>
        </section>
      </div>
    </>
  );
}
