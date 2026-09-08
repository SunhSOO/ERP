import { AiPanel, EmptyState, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { promoteClauseAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";

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
  const statements = await gateway.listStatements(projectId);

  if (statements.length === 0) {
    return (
      <>
        <PageHeader title="과업지시서 업로드" />
        <EmptyState
          description="과업지시서를 올리면 AI가 조항을 나누고 실행 가능한 태스크로 분류합니다."
          title="아직 등록된 과업지시서가 없습니다"
          variant="no-data"
        />
      </>
    );
  }

  const statement = statements[0];
  const clauses = await gateway.listClauses(statement.id);
  const needsReview = clauses.filter((clause) => clause.confidence === "low");

  return (
    <>
      <PageHeader
        status={<StatusTag tone="success">분류 완료</StatusTag>}
        title="과업지시서 업로드"
      />

      <div className="flex flex-col gap-2 border border-dashed border-divider p-6">
        <p className="m-0 text-[13px]">
          과업지시서 파일을 끌어다 놓거나 선택하세요.
        </p>
        <p className="text-muted m-0 text-[12px]">.docx, .hwpx, .pdf 지원</p>
      </div>

      <div className="flex flex-wrap items-center gap-3 border border-divider p-3">
        <span className="text-[13px]">{statement.filename}</span>
        <StatusTag tone="success">분석 완료</StatusTag>
        <span className="text-muted text-[12px]">
          AI가 문서를 {statement.clause_count}개 조항으로 나누고, 그중{" "}
          <strong className="text-text">{statement.classified_count}개</strong>를 실행 가능한
          태스크로 분류했습니다.
        </span>
      </div>

      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
        분류된 태스크 {statement.classified_count}건 · 신뢰도 낮음 {needsReview.length}건 검토 필요
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
