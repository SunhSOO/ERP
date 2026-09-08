import { AiPanel, StatusTag, Table, Th } from "@lep/ui";
import type { Clause } from "@lep/api-client";
import { gateway } from "@/src/shared/data/gateway";
import {
  classifyStatementAction,
  promoteClauseAction,
  uploadStatementAction,
} from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { StatementDropzone } from "@/src/widgets/delivery/StatementDropzone";

export const dynamic = "force-dynamic";

const CONFIDENCE = {
  high: { tone: "success", label: "높음" },
  medium: { tone: "warning", label: "보통" },
  low: { tone: "warning", label: "낮음" },
} as const;

/** 분류 결과를 색이 아니라 이름으로도 구분할 수 있게 한다. */
const CATEGORY_TONE: Record<string, "success" | "info" | "warning" | "idle"> = {
  과업범위: "success",
  산출물: "success",
  일정: "info",
  품질: "info",
  보안: "warning",
  계약조건: "idle",
  일반사항: "idle",
  미분류: "idle",
};

function ClauseRow({ clause, projectId }: { clause: Clause; projectId: string }) {
  const confidence = CONFIDENCE[clause.confidence];
  const unclassified = clause.category === "미분류";

  return (
    <tr>
      <td className="whitespace-nowrap align-top font-mono text-[12px]">
        <span style={{ paddingLeft: `${(clause.level - 1) * 12}px` }}>{clause.article}</span>
      </td>
      <td className="align-top">
        <div>{clause.task_title}</div>
        {clause.classified_reason ? (
          <div className="text-muted mt-1 text-[11px]">{clause.classified_reason}</div>
        ) : null}
      </td>
      <td className="align-top">
        <StatusTag tone={CATEGORY_TONE[clause.category] ?? "idle"}>
          {clause.category}
        </StatusTag>
      </td>
      <td className="align-top">
        {clause.actionable ? (
          <StatusTag tone="success">수행</StatusTag>
        ) : (
          <span className="text-muted text-[12px]">제약</span>
        )}
      </td>
      <td className="align-top">
        <StatusTag tone={confidence.tone}>{confidence.label}</StatusTag>
      </td>
      <td className="align-top">
        {clause.wbs_mapping ? (
          <span className="font-mono text-[12px]">{clause.wbs_mapping}</span>
        ) : (
          <ActionButton
            action={promoteClauseAction.bind(null, projectId, clause.id)}
            disabledReason={
              unclassified
                ? "아직 분류되지 않았습니다. 먼저 분류를 실행해 주세요."
                : clause.confidence === "low"
                  ? "신뢰도가 낮습니다. 사람이 확인한 뒤 반영해 주세요."
                  : !clause.actionable
                    ? "수행할 일이 아니라 지켜야 할 조건입니다."
                    : undefined
            }
          >
            WBS로 반영
          </ActionButton>
        )}
      </td>
    </tr>
  );
}

/** 02 과업지시서 업로드·태스크 분류. */
export default async function TasksPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [statements, limits] = await Promise.all([
    gateway.listStatements(projectId),
    gateway.uploadLimits(),
  ]);

  const dropzone = (
    <StatementDropzone
      action={uploadStatementAction.bind(null, projectId)}
      limits={limits}
    />
  );

  if (statements.length === 0) {
    return (
      <>
        <PageHeader
          note="문서를 올리면 규칙으로 절을 나눕니다. 분류는 그다음 단계입니다."
          title="과업지시서 업로드"
        />
        {dropzone}
        <p className="text-muted m-0 text-[13px]">아직 등록된 과업지시서가 없습니다.</p>
      </>
    );
  }

  // 가장 최근에 올린 문서를 펼쳐 본다. 나머지는 아래 줄에 남는다.
  const statement = statements[statements.length - 1];
  const clauses = statement.parse_error ? [] : await gateway.listClauses(statement.id);
  const unclassified = clauses.filter((c) => c.category === "미분류");
  const needsReview = clauses.filter(
    (c) => c.category !== "미분류" && c.confidence === "low",
  );

  return (
    <>
      <PageHeader
        actions={
          clauses.length > 0 ? (
            <ActionButton
              action={classifyStatementAction.bind(null, projectId, statement.id)}
              disabledReason={
                unclassified.length === 0 ? "분류할 조항이 남아 있지 않습니다." : undefined
              }
              variant="primary"
            >
              {`분류 실행 (${unclassified.length}건)`}
            </ActionButton>
          ) : null
        }
        status={
          statement.parse_error ? (
            <StatusTag tone="danger">분석 실패</StatusTag>
          ) : (
            <StatusTag tone="success">절 {statement.clause_count}개</StatusTag>
          )
        }
        title="과업지시서 업로드"
      />

      {dropzone}

      <div className="flex flex-wrap items-center gap-3 border border-divider p-3">
        <span className="text-[13px]">{statement.filename}</span>
        {statement.parse_error ? (
          <span className="text-[12px] text-danger-ink">
            <span aria-hidden="true">✕ </span>
            {statement.parse_error}
          </span>
        ) : (
          <span className="text-muted text-[12px]">
            규칙으로 절 {statement.clause_count}개를 나눴고, 그중{" "}
            <strong className="text-text">{statement.classified_count}개</strong>를
            분류했습니다. 절마다 지식 볼트에 노트가 하나씩 있습니다.
          </span>
        )}
      </div>

      {statements.length > 1 ? (
        <p className="text-muted m-0 text-[12px]">
          이 프로젝트에 올린 과업지시서 {statements.length}건 중 가장 최근 문서를 보고
          있습니다.
        </p>
      ) : null}

      {clauses.length === 0 ? (
        statement.parse_error ? null : (
          <p className="m-0 border border-warning bg-warning-bg p-2 text-[12.5px] text-warning-ink">
            <span aria-hidden="true">▲ </span>
            절을 찾지 못했습니다. `제N조`나 `1.` / `1.1` 형태의 번호가 있는 문서인지
            확인해 주세요.
          </p>
        )
      ) : (
        <>
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
            절 {clauses.length}건 · 미분류 {unclassified.length}건 · 신뢰도 낮음{" "}
            {needsReview.length}건
          </h2>

          <Table caption="과업지시서의 절과 분류 결과">
            <thead>
              <tr>
                <Th>절</Th>
                <Th>제목</Th>
                <Th>카테고리</Th>
                <Th>성격</Th>
                <Th>신뢰도</Th>
                <Th>WBS 매핑</Th>
              </tr>
            </thead>
            <tbody>
              {clauses.map((clause) => (
                <ClauseRow clause={clause} key={clause.id} projectId={projectId} />
              ))}
            </tbody>
          </Table>
        </>
      )}

      {clauses.length > 0 ? (
        <AiPanel title="분류 상태">
          {unclassified.length === clauses.length ? (
            <p className="m-0">
              아직 분류하지 않았습니다. 절을 나누는 것은 규칙이고 분류는 로컬 LLM이
              합니다. 위의 분류 실행을 눌러 주세요.
            </p>
          ) : unclassified.length > 0 ? (
            <p className="m-0">
              {unclassified.length}건이 미분류로 남았습니다. 각 줄의 사유를 확인해
              주세요.
            </p>
          ) : (
            <p className="m-0">
              모든 절을 분류했습니다
              {clauses[0]?.classified_by ? ` (${clauses[0].classified_by})` : ""}. 신뢰도가
              낮은 {needsReview.length}건은 사람 확인 뒤 WBS에 반영해 주세요.
            </p>
          )}
        </AiPanel>
      ) : null}
    </>
  );
}
