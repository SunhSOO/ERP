import Link from "next/link";
import { AiPanel, Card, CardTitle, EmptyState, StatusTag } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { syncVaultAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { vaultTone } from "@/src/shared/ui/status";

export const dynamic = "force-dynamic";

const SOURCE_LABEL = {
  meeting: "회의록 출처",
  statement: "과업지시서 출처",
  mail: "메일 출처",
  manual: "직접 작성",
} as const;

const VAULT_LABEL = { ok: "동기화됨", stale: "동기화 지연", failed: "동기화 실패" } as const;

/** 04 지식 볼트. */
export default async function VaultPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ note?: string }>;
}) {
  const { projectId } = await params;
  const { note: selectedId } = await searchParams;

  const [status, notes] = await Promise.all([
    gateway.getVault(projectId),
    gateway.listNotes(projectId),
  ]);

  const selected = notes.find((note) => note.id === selectedId) ?? notes[0] ?? null;

  return (
    <>
      <PageHeader
        actions={
          <ActionButton action={syncVaultAction.bind(null, projectId)}>지금 동기화</ActionButton>
        }
        note={`노트 ${status.note_count}개`}
        status={<StatusTag tone={vaultTone(status.health)}>{VAULT_LABEL[status.health]}</StatusTag>}
        title="지식 볼트"
      />

      {status.vault_path === "" ? (
        <p className="m-0 border border-divider p-2 text-[12px]">
          <span aria-hidden="true">○ </span>
          볼트 경로가 아직 설정되지 않았습니다. 지금은 픽스처 데이터를 보고 있습니다.
        </p>
      ) : null}

      {notes.length === 0 ? (
        <EmptyState
          description="회의록이나 메일을 지식화하면 여기에 노트가 쌓입니다."
          title="아직 노트가 없습니다"
          variant="no-data"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(280px,380px)_1fr]">
          <section aria-label="태스크별 링크 노트" className="flex flex-col gap-3">
            <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
              태스크별 링크 노트
            </h2>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {notes.map((note) => (
                <li key={note.id}>
                  <Link
                    aria-current={selected?.id === note.id ? "true" : undefined}
                    className="block no-underline"
                    href={`?note=${note.id}`}
                  >
                    <Card
                      className={selected?.id === note.id ? "border-accent" : undefined}
                      elevation={selected?.id === note.id ? "sm" : undefined}
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <CardTitle>{note.title}</CardTitle>
                        <span className="text-muted text-[11px]">
                          {SOURCE_LABEL[note.source]}
                        </span>
                      </div>
                      <p className="text-muted m-0 text-[12px]">
                        노트 {note.note_count}개 · 백링크 {note.backlinks.length}개
                        {note.updated_at ? ` · 마지막 업데이트 ${note.updated_at}` : ""}
                      </p>
                      {note.warning ? (
                        <StatusTag tone="warning">{note.warning}</StatusTag>
                      ) : null}
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {selected ? (
            <section aria-label="노트 미리보기" className="flex flex-col gap-3">
              <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
                노트 미리보기 — {selected.id}.md
              </h2>
              <pre className="m-0 overflow-x-auto border border-divider p-3 font-mono text-[12px] whitespace-pre-wrap">
                {selected.body}
              </pre>

              <h3 className="text-muted m-0 text-[11px] tracking-wide uppercase">
                백링크 {selected.backlinks.length}개
              </h3>
              <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[13px]">
                {selected.backlinks.map((backlink) => (
                  <li key={backlink.target}>
                    <span aria-hidden="true">↳ </span>
                    {backlink.label}
                  </li>
                ))}
              </ul>

              {selected.source === "meeting" ? (
                <AiPanel title="AI 생성 노트">
                  <p className="m-0">이 노트는 회의록에서 자동 생성되었습니다.</p>
                </AiPanel>
              ) : null}
            </section>
          ) : null}
        </div>
      )}
    </>
  );
}
