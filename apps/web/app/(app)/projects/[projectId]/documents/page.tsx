import Link from "next/link";
import { EmptyState, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { retryDocumentAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { PIPELINE_STAGES } from "@/src/shared/ui/status";
import styles from "@/src/widgets/documents/pipeline.module.css";

export const dynamic = "force-dynamic";

/** 05 문서 생성·변환. */
export default async function DocumentsPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ doc?: string }>;
}) {
  const { projectId } = await params;
  const { doc: selectedId } = await searchParams;

  const documents = await gateway.listDocuments(projectId);

  if (documents.length === 0) {
    return (
      <>
        <PageHeader title="문서 생성·변환" />
        <EmptyState
          description="마크다운 초안을 만들면 hwpx 변환 파이프라인이 시작됩니다."
          title="아직 문서가 없습니다"
          variant="no-data"
        />
      </>
    );
  }

  const selected = documents.find((item) => item.id === selectedId) ?? documents[0];

  return (
    <>
      <PageHeader title="문서 생성·변환" />

      <section aria-label={`${selected.title} 변환 단계`} className="flex flex-col gap-2">
        <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
          선택 문서 — {selected.title}
        </h2>
        <ol className={styles.pipeline}>
          {PIPELINE_STAGES.map((label, index) => {
            const stageNumber = index + 1;
            const done = stageNumber < selected.stage;
            const current = stageNumber === selected.stage;
            const failed = current && selected.state === "failed";
            return (
              <li
                aria-current={current ? "step" : undefined}
                className={[
                  styles.step,
                  done ? styles.stepDone : "",
                  current ? styles.stepCurrent : "",
                  failed ? styles.stepFailed : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                key={label}
              >
                <span aria-hidden="true" className={styles.stepMark}>
                  {done ? "✓" : failed ? "✕" : stageNumber}
                </span>
                <span>{label}</span>
              </li>
            );
          })}
        </ol>
        <p className="text-muted m-0 text-[12px]">변환기: {selected.converter}</p>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section aria-label="마크다운 원본" className="flex flex-col gap-2">
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">md 원본</h2>
          <pre className="m-0 overflow-x-auto border border-divider p-3 font-mono text-[12px] whitespace-pre-wrap">
            {selected.markdown}
          </pre>
        </section>

        <section aria-label="hwpx 미리보기" className="flex flex-col gap-2">
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
            hwpx 미리보기 (양식 적용)
          </h2>
          {/* 실제 hwpx 렌더링이 아니라 양식이 적용된 모습의 재현이다.
              실제 변환은 kordoc 어댑터가 붙는 WP-PKD-030에서 동작한다. */}
          <div className="flex flex-col items-center gap-3 border border-divider bg-surface p-6">
            <p className="m-0 text-[15px] tracking-[0.4em]">검 수 결 과 보 고 서</p>
            <p className="text-muted m-0 text-[12px]">{selected.title}</p>
            <p className="text-muted m-0 text-[11px] tabular-nums">
              {selected.updated_at.slice(0, 10)}
            </p>
          </div>
          <p className="text-muted m-0 text-[11px]">
            양식이 적용된 결과의 재현입니다. 실제 변환은 변환기 연동 후 동작합니다.
          </p>
        </section>
      </div>

      <Table caption="문서별 변환 상태">
        <thead>
          <tr>
            <Th>문서</Th>
            <Th>단계</Th>
            <Th>변환기</Th>
            <Th>동작</Th>
          </tr>
        </thead>
        <tbody>
          {documents.map((item) => (
            <tr key={item.id}>
              <td>
                <Link href={`?doc=${item.id}`}>{item.title}</Link>
              </td>
              <td>
                <StatusTag
                  tone={
                    item.state === "failed"
                      ? "danger"
                      : item.stage === 5
                        ? "success"
                        : "progress"
                  }
                >
                  {item.state === "failed"
                    ? "변환 실패"
                    : `${item.stage}단계 ${PIPELINE_STAGES[item.stage - 1]}`}
                </StatusTag>
                {item.failure_reason ? (
                  <p className="text-muted m-0 mt-1 text-[11px]">{item.failure_reason}</p>
                ) : null}
              </td>
              <td>{item.converter}</td>
              <td>
                {item.state === "failed" ? (
                  <ActionButton action={retryDocumentAction.bind(null, projectId, item.id)}>
                    다시 시도
                  </ActionButton>
                ) : (
                  <Link className="text-[12px]" href={`?doc=${item.id}`}>
                    열기
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}
