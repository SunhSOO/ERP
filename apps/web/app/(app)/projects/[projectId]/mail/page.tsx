import { Fragment } from "react";
import Link from "next/link";
import { Card, EmptyState, ForbiddenState, StatusTag } from "@lep/ui";
import { ApiProblem } from "@lep/api-client";
import type { MailCounts, MailMessage, MailStatusFilter } from "@lep/api-client";
import { gateway } from "@/src/shared/data/gateway";
import {
  MAIL_PAGE_SIZE,
  fetchMailById,
  fetchMailCounts,
  fetchMailPage,
  normalizeMailPage,
  normalizeMailStatus,
} from "@/src/shared/data/mail-review";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { MailDetailSection } from "@/src/widgets/mail/MailDetailSection";
import { MailCountsHeader } from "@/src/widgets/mail/MailCountsHeader";
import { MailTabCountBadge } from "@/src/widgets/mail/MailTabCountBadges";
import { MailProjectsNav } from "@/src/widgets/mail/MailProjectsNav";
import type { MailDetailResult, MailProjectsResult } from "@/src/widgets/mail/mail-deferred-results";

export const dynamic = "force-dynamic";

const STATUS_TABS = ["unclassified", "project", "unrelated", "all"] as const;

const STATUS_TAB_LABEL: Record<MailStatusFilter, string> = {
  unclassified: "미분류",
  project: "프로젝트별 분류됨",
  unrelated: "제외됨",
  all: "전체",
};

function tabHref(status: MailStatusFilter, page: number, suggested?: "yes" | "no"): string {
  const params: Record<string, string> = { status, page: String(page) };
  if (suggested) {
    params.suggested = suggested;
  }
  return `?${new URLSearchParams(params).toString()}`;
}

function canViewWithinTab(
  detail: MailMessage,
  status: MailStatusFilter,
  isAdmin: boolean,
  routeProjectId: string,
): boolean {
  if (status === "project") {
    return detail.classification === "project" && detail.project_id === routeProjectId;
  }
  if (!isAdmin) return false;
  if (status === "unclassified") return detail.classification === "unclassified";
  if (status === "unrelated") return detail.classification === "unrelated";
  return (
    detail.classification === "unclassified" ||
    detail.classification === "unrelated" ||
    (detail.classification === "project" && detail.project_id === routeProjectId)
  );
}

async function createDetailResult(
  targetId: string | null,
  messages: MailMessage[],
  query: Record<string, unknown>,
  status: MailStatusFilter,
  isAdmin: boolean,
  projectId: string,
): Promise<MailDetailResult> {
  if (!targetId) {
    return { error: "notfound" };
  }

  const inPageMatch = messages.find((item) => item.id === targetId) ?? null;
  const isOutsidePage = Boolean(query.mail && !inPageMatch);

  try {
    const detail = await fetchMailById(targetId);
    if (detail.id !== targetId) {
      return { error: "notfound" };
    } else if (inPageMatch) {
      return detail; // backend GET already authorizes the current actor
    } else if (isOutsidePage) {
      if (detail.classification === "project" && detail.project_id === projectId) {
        if (query.linked_file_id) {
          const hasLink = detail.attachments.some(
            (file) => file.linked_file_id === query.linked_file_id as string,
          );
          if (!hasLink) {
            return { error: "linked_file_mismatch" };
          }
        }
        return detail;
      } else {
        return { error: "forbidden" };
      }
    } else if (canViewWithinTab(detail, status, isAdmin, projectId)) {
      return detail;
    } else {
      return { error: "forbidden" };
    }
  } catch (err) {
    if (err instanceof ApiProblem && err.problem.status === 403) {
      return { error: "forbidden" };
    }
    return { error: "unknown" };
  }
}

export default async function MailPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<Record<string, unknown>>;
}) {
  const { projectId } = await params;
  const query = await searchParams;

  const user = await gateway.me();
  const isAdmin = user?.role === "admin";
  const status = normalizeMailStatus(query.status as string | undefined, isAdmin);
  const page = normalizeMailPage(query.page as string | undefined);
  const suggested = status === "unclassified" && ((query.suggested as string | undefined) === "yes" || (query.suggested as string | undefined) === "no") ? (query.suggested as "yes" | "no") : undefined;

  // Start deferred requests early (before list)
  const countsPromise: Promise<MailCounts | null> = isAdmin
    ? fetchMailCounts(projectId).catch(() => null)
    : Promise.resolve(null);

  const projectsPromise: Promise<MailProjectsResult> = isAdmin
    ? gateway
        .listProjects()
        .then((projects) => ({
          ok: true as const,
          projects: projects.map((p) => ({ id: p.id, name: p.name })),
        }))
        .catch(() => ({ ok: false as const }))
    : Promise.resolve({ ok: true as const, projects: [] });

  let messages: Awaited<ReturnType<typeof fetchMailPage>>["messages"];
  let total: number | null;
  let hasMore: boolean;

  try {
    const listResult = await fetchMailPage(projectId, status, page, suggested);
    messages = listResult.messages;
    total = listResult.total;
    hasMore = listResult.hasMore;
  } catch (error) {
    if (error instanceof ApiProblem && error.problem.status === 403) {
      return (
        <>
          <PageHeader title="메일함" />
          <ForbiddenState
            contact="관리자"
            description="이 메일 목록을 볼 권한이 없습니다."
            requiredPermission="mail.review 또는 해당 프로젝트 생성자"
          />
        </>
      );
    }
    if (error instanceof ApiProblem) {
      return (
        <>
          <PageHeader title="메일함" />
          <p className="m-0 border border-danger bg-danger-bg p-3 text-[13px] text-danger-ink">
            <span aria-hidden="true">✕ </span>
            메일함을 불러오지 못했습니다. 추적 ID{" "}
            <code className="font-mono select-all">{error.traceId}</code>
          </p>
        </>
      );
    }
    throw error;
  }

  const targetId = (query.mail as string | undefined) ?? messages[0]?.id ?? null;

  const detailPromise: Promise<MailDetailResult> = createDetailResult(
    targetId,
    messages,
    query,
    status,
    isAdmin,
    projectId,
  );

  return (
    <>
      <PageHeader
        note={isAdmin ? <MailCountsHeader countsPromise={countsPromise} /> : undefined}
        title="메일함"
      />

      <section className="mb-3 rounded border border-divider bg-surface p-3">
        <h2 className="m-0 text-[16px] font-semibold">{STATUS_TAB_LABEL[status]} 카테고리</h2>
        <p className="text-muted mb-2 text-[12px]">페이지당 {MAIL_PAGE_SIZE}건 · 새 메일은 최대 30초 후 목록에 반영될 수 있습니다.</p>

        {isAdmin ? (
          <>
            <nav aria-label="메일 분류 탭" className="mb-3 rounded border border-divider p-2">
              <p className="mb-1 text-[12px] font-semibold">카테고리</p>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {STATUS_TABS.map((tab) => (
                  <li key={tab}>
                    <Link
                      aria-current={status === tab ? "page" : undefined}
                      className="no-underline"
                      href={tabHref(tab, 1)}
                    >
                      <StatusTag tone={tab === status ? "info" : "idle"}>
                        {STATUS_TAB_LABEL[tab]}
                        <MailTabCountBadge countsPromise={countsPromise} status={tab} />
                      </StatusTag>
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>

            <nav aria-label="프로젝트별 분류됨" className="mb-2">
              <p className="mb-1 text-[12px] font-semibold">프로젝트별 분류됨</p>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                <MailProjectsNav projectsPromise={projectsPromise} status={status} projectId={projectId} />
              </ul>
            </nav>

            {status === "unclassified" ? (
              <nav aria-label="추천 필터" className="mb-2">
                <p className="mb-1 text-[12px] font-semibold">추천</p>
                <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                  <li>
                    <Link className="no-underline" href={tabHref("unclassified", 1)}>
                      <StatusTag tone={suggested === undefined ? "info" : "idle"}>전체</StatusTag>
                    </Link>
                  </li>
                  <li>
                    <Link className="no-underline" href={tabHref("unclassified", 1, "yes")}>
                      <StatusTag tone={suggested === "yes" ? "info" : "idle"}>추천있음</StatusTag>
                    </Link>
                  </li>
                  <li>
                    <Link className="no-underline" href={tabHref("unclassified", 1, "no")}>
                      <StatusTag tone={suggested === "no" ? "info" : "idle"}>추천없음</StatusTag>
                    </Link>
                  </li>
                </ul>
              </nav>
            ) : null}
          </>
        ) : null}

        <nav
          aria-label="메일 목록 페이지"
          className="mb-2 flex items-center gap-2 rounded border border-divider p-2"
        >
          {page > 1 ? (
            <Link className="no-underline" href={tabHref(status, page - 1, suggested)}>
              이전
            </Link>
          ) : null}
          <span className="text-muted text-[11px]">
            {page}쪽{total !== null ? ` · 전체 ${total}건` : ""}
          </span>
          {hasMore ? (
            <Link className="no-underline" href={tabHref(status, page + 1, suggested)}>
              다음
            </Link>
          ) : null}
        </nav>
      </section>

      {messages.length === 0 && !targetId ? (
        <EmptyState
          description={
            isAdmin
              ? "이 분류에 해당하는 메일이 없습니다."
              : "이 프로젝트로 승인된 메일이 아직 없습니다."
          }
          title="메일이 없습니다"
          variant={isAdmin ? "no-results" : "no-data"}
        />
      ) : (
        <div className="flex flex-col gap-4 lg:flex-row lg:overflow-hidden lg:max-h-[calc(100vh-28rem)]">
          <section aria-label="메일 목록" className="lg:min-h-0 lg:overflow-y-auto">
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {messages.map((item) => (
                <li key={item.id}>
                  <Link
                    className="block no-underline"
                    href={`?${new URLSearchParams({
                      status,
                      page: String(page),
                      mail: item.id,
                      ...(suggested && { suggested }),
                    }).toString()}`}
                  >
                    <Card className={targetId && item.id === targetId ? "border-accent" : undefined}>
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-[13px]">
                          {item.sender_name} ({item.sender_org})
                        </span>
                        <span className="text-muted text-[11px] tabular-nums">
                          {item.received_at.slice(11, 16)}
                        </span>
                      </div>
                      <span className="text-[13px]">{item.subject}</span>
                      {item.suggestions && item.suggestions.length > 0 ? (
                        <span className="text-[12px]">
                          추천: {item.suggestions[0].project_name} · {item.suggestions[0].confidence === "high" ? "높음" : item.suggestions[0].confidence === "medium" ? "중" : "낮음"}
                        </span>
                      ) : null}
                      {item.attachments.length > 0 ? (
                        <span className="text-muted text-[11px]">
                          <span aria-hidden="true">📎 </span>
                          첨부 {item.attachments.length}개
                        </span>
                      ) : null}
                      {item.classification === "unclassified" ? (
                        <StatusTag tone="warning">
                          {item.intent ? `${item.intent} 추정` : "미분류"}
                        </StatusTag>
                      ) : item.classification === "unrelated" ? (
                        <StatusTag tone="idle">프로젝트 무관</StatusTag>
                      ) : (
                        <StatusTag tone="success">분류됨</StatusTag>
                      )}
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {targetId ? (
            <div className="lg:flex-1 lg:min-h-0 lg:overflow-y-auto">
              <MailDetailSection
                key={JSON.stringify([
                  projectId,
                  status,
                  targetId,
                  query.linked_file_id ?? null,
                ])}
                detailPromise={detailPromise}
                projectId={projectId}
                projectsPromise={projectsPromise}
                isAdmin={isAdmin}
                displayName={user?.display_name}
              />
            </div>
          ) : null}
        </div>
      )}
    </>
  );
}
