import { AiPanel, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { promoteClauseAction, uploadStatementAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { StatementDropzone } from "@/src/widgets/delivery/StatementDropzone";

export const dynamic = "force-dynamic";

const CONFIDENCE = {
  high: { tone: "success", label: "높음" },
  medium: { tone: "warning", label: "보통" },
  low: { tone: "warning", label: "낮음" },
} as const;

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
          note="문서를 올리면 조항 단위로 나눕니다. 분류는 사람이 확인한 뒤 WBS에 반영합니다."
          title="과업지시서 업로드"
        />
        {dropzone}
        <p className="text-muted m-0 text-[13px]">
          아직 등록된 과업지시서가 없습니다.
        </p>
      </>
    );
  }

  // 가장 최근에 올린 문서를 펼쳐 본다. 나머지는 아래 목록에 남는다.
  const statement = statements[statements.length - 1];
  const clauses = statement.parse_error ? [] : await gateway.listClauses(statement.id);
  const needsReview = clauses.filter((clause) => clause.confidence === "low");

  return (
    <>
      <PageHeader
        status={
          statement.parse_error ? (
            <StatusTag tone="danger">분석 실패</StatusTag>
          ) : (
            <StatusTag tone="success">분석 완료</StatusTag>
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
            문서를 {statement.clause_count}개 조항으로 나눴습니다. 분류된 태스크는{" "}
            <strong className="text-text">{statement.classified_count}건</strong>입니다.
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
            조항을 찾지 못했습니다. 제N조 형식이나 번호 목록이 있는 문서인지 확인해
            주세요.
          </p>
        )
      ) : (
        <>
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
            조항 {clauses.length}건 · 신뢰도 낮음 {needsReview.length}건 검토 필요
          </h2>

          <Table caption="과업지시서 조항과 분류 결과">
            <thead>
              <tr>
                <Th>조항</Th>
                <Th>분류된 태스크</Th>
                <Th>카테고리</Th>
                <Th>신뢰도</Th>
                <Th>WBS 매핑</Th>
              </tr>
            </thead>
            <tbody>
              {clauses.map((clause) => {
                const confidence = CONFIDENCE[clause.confidence];
                const low = clause.confidence === "low";
                return (
                  <tr key={clause.id}>
                    <td className="whitespace-nowrap">{clause.article}</td>
                    <td>{clause.task_title}</td>
                    <td>{clause.category}</td>
                    <td>
                      <StatusTag tone={confidence.tone}>{confidence.label}</StatusTag>
                    </td>
                    <td>
                      {clause.wbs_mapping ? (
                        <span className="font-mono text-[12px]">{clause.wbs_mapping}</span>
                      ) : (
                        <ActionButton
                          action={promoteClauseAction.bind(null, projectId, clause.id)}
                          disabledReason={
                            low
                              ? "신뢰도가 낮습니다. 계약 조건 해석을 먼저 확인해 주세요."
                              : undefined
                          }
                        >
                          WBS로 반영
                        </ActionButton>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </>
      )}

      {needsReview.length > 0 ? (
        <AiPanel title="AI 분석">
          <p className="m-0">
            신뢰도 낮은 조항 {needsReview.length}건은 계약 조건 해석이 필요합니다. WBS 반영 전
            사람 확인을 권장합니다.
          </p>
        </AiPanel>
      ) : null}
    </>
  );
}
