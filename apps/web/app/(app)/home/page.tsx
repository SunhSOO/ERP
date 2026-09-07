import Link from "next/link";
import { AiPanel, Card, CardTitle, LinkButton, StatusTag, Tag } from "@lep/ui";
import type { Project, ProjectSummary } from "@lep/api-client";
import { gateway } from "@/src/shared/data/gateway";
import { syncTone } from "@/src/shared/ui/status";

/** 픽스처가 요청마다 바뀔 수 있으므로 정적 생성하지 않는다. */
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

      <Link className="text-[12px]" href={`/projects/${project.id}/wbs`}>
        프로젝트 열기 →
      </Link>
    </Card>
  );
}

export default async function HomePage() {
  const cards = await loadCards();
  const vendorProjects = cards.filter((card) => card.project.role === "vendor");
  const alerts = cards.filter((card) => card.summary?.vcs_health === "mismatch");

  return (
    <>
      <div className="flex items-center gap-3">
        <h1 className="m-0 text-[22px]">안녕하세요, 김서준님</h1>
      </div>

      <section aria-label="참여 프로젝트">
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4 p-0">
          {cards.map((card) => (
            <ProjectCard key={card.project.id} {...card} />
          ))}
        </ul>
      </section>

      <section aria-label="빠른 작업" className="flex flex-col gap-2">
        <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
          빠른 작업 · 용역사
        </h2>
        <div className="flex flex-wrap gap-2">
          {vendorProjects[0] ? (
            <>
              <LinkButton
                href={`/projects/${vendorProjects[0].project.id}/tasks`}
                size="sm"
                variant="secondary"
              >
                + 과업지시서 업로드
              </LinkButton>
              <LinkButton
                href={`/projects/${vendorProjects[0].project.id}/wbs`}
                size="sm"
                variant="secondary"
              >
                WBS 새 태스크
              </LinkButton>
              <LinkButton
                href={`/projects/${vendorProjects[0].project.id}/meetings`}
                size="sm"
                variant="secondary"
              >
                회의록 업로드 → 지식화
              </LinkButton>
              <LinkButton
                href={`/projects/${vendorProjects[0].project.id}/documents`}
                size="sm"
                variant="secondary"
              >
                문서 변환 요청
              </LinkButton>
            </>
          ) : null}
        </div>
      </section>

      <AiPanel title="AI 요약">
        {alerts.length > 0 ? (
          <p className="m-0">
            {alerts.map((card) => card.project.customer_name).join(", ")} 깃허브 리포에 WBS와
            어긋난 항목이 있습니다. 미분류 메일도 확인이 필요합니다.
          </p>
        ) : (
          <p className="m-0">지금 확인할 불일치가 없습니다.</p>
        )}
      </AiPanel>
    </>
  );
}
