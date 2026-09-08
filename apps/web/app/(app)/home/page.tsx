import Link from "next/link";
import { Card, CardTitle, EmptyState, StatusTag, Tag } from "@lep/ui";
import type { Project, ProjectSummary } from "@lep/api-client";
import { gateway } from "@/src/shared/data/gateway";
import { syncTone } from "@/src/shared/ui/status";
import { CreateProjectForm } from "@/src/widgets/projects/CreateProjectForm";

export const dynamic = "force-dynamic";

interface CardData {
  project: Project;
  summary: ProjectSummary | null;
}

async function loadCards(): Promise<CardData[]> {
  const projects = await gateway.listProjects();

  // 카드 하나의 집계가 실패해도 나머지 카드는 남아야 한다.
  // 06_UI_UX 6절의 부분 실패 요구다. allSettled가 그 역할을 한다.
  const summaries = await Promise.allSettled(
    projects.map((project) => gateway.getSummary(project.id)),
  );

  return projects.map((project, index) => {
    const settled = summaries[index];
    return {
      project,
      summary: settled.status === "fulfilled" ? settled.value : null,
    };
  });
}

function SummaryRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted">{label}</span>
      {children}
    </div>
  );
}

function ProjectCard({ project, summary }: CardData) {
  return (
    <Card blueprint className="gap-3" as="li">
      <div className="flex items-baseline justify-between gap-2">
        <CardTitle>{project.name}</CardTitle>
        <Tag variant="outline">{project.role === "vendor" ? "용역사" : "발주사"}</Tag>
      </div>

      <p className="text-muted m-0 font-mono text-[11px]">{project.code}</p>

      {summary === null ? (
        <p className="m-0 border border-warning bg-warning-bg p-2 text-[12px] text-warning-ink">
          <span aria-hidden="true">▲ </span>
          집계를 불러오지 못했습니다. 프로젝트는 정상입니다.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5 text-[12.5px]">
          <SummaryRow label={summary.wbs_progress_percent === null ? "관리 WBS" : "WBS 진행률"}>
            {summary.wbs_progress_percent === null ? (
              <StatusTag tone="warning">{summary.schedule_note ?? "정보 없음"}</StatusTag>
            ) : (
              <span className="tabular-nums">{summary.wbs_progress_percent}%</span>
            )}
          </SummaryRow>

          <SummaryRow label="과업지시서">
            <span className="tabular-nums">{summary.statement_count}건</span>
          </SummaryRow>

          <SummaryRow label="지식 볼트">
            <StatusTag tone={syncTone(summary.vault_health)}>{summary.vault_note}</StatusTag>
          </SummaryRow>

          <SummaryRow label="미분류 메일">
            {summary.unclassified_mail_count > 0 ? (
              <span className="text-warning-ink">{summary.unclassified_mail_count}건</span>
            ) : (
              <span className="text-muted">0건</span>
            )}
          </SummaryRow>

          <SummaryRow label="깃허브 정합">
            <StatusTag tone={syncTone(summary.vcs_health)}>{summary.vcs_note}</StatusTag>
          </SummaryRow>
        </div>
      )}

      <Link className="text-[12px]" href={`/projects/${project.id}/tasks`}>
        프로젝트 열기 →
      </Link>
    </Card>
  );
}

export default async function HomePage() {
  // 세션이 없으면 `(app)` 레이아웃이 먼저 로그인으로 보낸다. 여기 오면 있다.
  const [user, cards] = await Promise.all([gateway.me(), loadCards()]);

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="m-0 text-[22px]">안녕하세요, {user?.display_name}님</h1>
        {cards.length > 0 ? (
          <div className="ml-auto">
            <CreateProjectForm defaultPmName={user?.display_name ?? ""} />
          </div>
        ) : null}
      </div>

      {cards.length === 0 ? (
        <section aria-label="참여 프로젝트" className="flex flex-col gap-4">
          <EmptyState
            description="프로젝트를 만들면 과업지시서 업로드, WBS, 지식 볼트가 함께 열립니다. 지식 볼트는 프로젝트마다 따로 만들어집니다."
            title="아직 프로젝트가 없습니다"
            variant="no-data"
          />
          <CreateProjectForm defaultPmName={user?.display_name ?? ""} startOpen />
        </section>
      ) : (
        <section aria-label="참여 프로젝트">
          <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4 p-0">
            {cards.map((card) => (
              <ProjectCard key={card.project.id} {...card} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
