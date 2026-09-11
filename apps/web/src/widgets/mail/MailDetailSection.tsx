"use client";

import { Fragment, Suspense, use } from "react";
import { mailMessagePath, mailMessageQuery } from "@/src/shared/data/mail-message-id";
import type { MailDetailResult, MailProjectsResult } from "./mail-deferred-results";
import { MailApprovalFormDeferred } from "./MailApprovalFormDeferred";
import { MailAttachmentFollowupForm } from "./MailAttachmentFollowupForm";
import { MailDismissButton } from "./MailDismissButton";
import { AiPanel, StatusTag } from "@lep/ui";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { promoteMailToNoteAction } from "@/src/shared/data/mail-review-actions";

const CONFIDENCE_LABEL = { high: "높음", medium: "중", low: "낮음" } as const;

function fileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)}KB`;
  return `${bytes}B`;
}

interface MailDetailSectionProps {
  detailPromise: Promise<MailDetailResult>;
  projectId: string;
  projectsPromise: Promise<MailProjectsResult>;
  isAdmin: boolean;
  displayName: string | undefined;
}

function MailDetailContent({
  detailPromise,
  projectId,
  projectsPromise,
  isAdmin,
  displayName,
}: MailDetailSectionProps) {
  const result = use(detailPromise);

  if ("error" in result) {
    const errorMsg =
      result.error === "linked_file_mismatch"
        ? "원본 소스를 사용할 수 없습니다. 첨부 연결 정보가 일치하지 않습니다."
        : "이 메일을 볼 수 없습니다.";
    return (
      <p className="m-0 border border-danger bg-danger-bg p-3 text-[13px] text-danger-ink">
        <span aria-hidden="true">✕ </span>
        {errorMsg}
      </p>
    );
  }

  const selected = result;

  return (
    <section aria-label="메일 상세" className="flex flex-col gap-3">
      <h2 className="m-0 text-[17px]">{selected.subject}</h2>
      <p className="text-muted m-0 text-[12px]">
        {selected.sender_name} ({selected.sender_org}) → {displayName} ·{" "}
        <span className="tabular-nums">{selected.received_at.slice(11, 16)}</span>
      </p>

      {selected.intent && selected.confidence ? (
        <StatusTag tone="warning">
          분류 추천: {selected.intent} (신뢰도 {CONFIDENCE_LABEL[selected.confidence]})
        </StatusTag>
      ) : null}

      {selected.suggestions && selected.suggestions.length > 0 ? (
        <section className="flex flex-col gap-2 border border-divider p-3">
          <h3 className="m-0 text-[13px] font-semibold">프로젝트 추천</h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {selected.suggestions.map((suggestion, index) => (
              <li key={index} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13px]">{suggestion.project_name}</span>
                  <StatusTag tone={suggestion.confidence === "high" ? "info" : suggestion.confidence === "medium" ? "warning" : "idle"}>
                    {CONFIDENCE_LABEL[suggestion.confidence]}
                  </StatusTag>
                </div>
                {suggestion.reasons.length > 0 ? (
                  <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[12px]">
                    {suggestion.reasons.map((reason, i) => (
                      <li key={i} className="text-muted">· {reason}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {selected.approved_by ? (
        <p className="text-muted m-0 text-[12px]">
          {selected.classification === "unrelated" ? "제외" : "승인"} · {selected.approved_by}
          {selected.approved_at ? ` · ${selected.approved_at}` : ""}
        </p>
      ) : null}

      <p className="m-0 border border-divider p-3 text-[13px] whitespace-pre-wrap">
        {selected.body || <span className="text-muted">본문이 없습니다.</span>}
      </p>

      {selected.attachments.length > 0 ? (
        <section aria-label="첨부 파일" className="flex flex-col gap-2">
          <h3 className="text-muted m-0 text-[11px] tracking-wide uppercase">
            첨부 {selected.attachments.length}개
          </h3>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {selected.attachments.map((file) => (
              <li
                className="flex flex-wrap items-center gap-2 border border-divider p-2 text-[12.5px]"
                key={file.part_index}
              >
                <span aria-hidden="true">📎</span>
                {file.linked_file_id || (isAdmin && selected.classification === "unclassified") ? (
                  <a
                    className="flex-1"
                    href={`/api/mail/${mailMessagePath(selected.id)}/attachments/${file.part_index}${mailMessageQuery(selected.id)}${
                      file.linked_file_id ? `${mailMessageQuery(selected.id) ? "&" : "?"}linked_file_id=${encodeURIComponent(file.linked_file_id)}` : ""
                    }`}
                  >
                    {file.filename}
                  </a>
                ) : (
                  <span className="flex-1">{file.filename}</span>
                )}
                <span className="text-muted tabular-nums">{fileSize(file.size_bytes)}</span>
                {file.linked_file_id ? (
                  <StatusTag tone="success">연결완료</StatusTag>
                ) : (
                  <StatusTag tone="idle">미승인</StatusTag>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {isAdmin ? (
        <Fragment>
          {selected.can_review ? (
            <MailApprovalFormDeferred message={selected} projectsPromise={projectsPromise} reviewProjectId={projectId} />
          ) : null}
          {selected.can_review && selected.classification === "unclassified" ? (
            <MailDismissButton
              messageId={selected.id}
              reviewProjectId={projectId}
              version={selected.version}
            />
          ) : null}
          <MailAttachmentFollowupForm message={selected} projectId={projectId} />
        </Fragment>
      ) : null}

      <AiPanel
        actions={
          <ActionButton
            action={promoteMailToNoteAction.bind(null, projectId, selected.id)}
            disabledReason={
              selected.note_id
                ? "이미 지식화된 메일입니다."
                : selected.classification !== "project" || !selected.approved_by
                  ? "승인된 메일만 지식화할 수 있습니다."
                  : undefined
            }
          >
            지식화 (볼트에 노트 생성)
          </ActionButton>
        }
        title="분류 참고"
      >
        {selected.intent ? (
          <p className="m-0">
            발신 정보와 키워드를 바탕으로 {selected.milestone_code ?? "해당 프로젝트"} 관련{" "}
            <strong>{selected.intent}</strong>으로 보입니다
            {selected.confidence ? ` (참고 수준 ${CONFIDENCE_LABEL[selected.confidence]})` : ""}. 최종 분류와 승인은 담당자가 확인해야 합니다.
          </p>
        ) : (
          <p className="m-0">추가로 제안할 조치가 없습니다.</p>
        )}
        <p className="text-muted m-0 mt-2 text-[12px]">
          메일 내용으로 일정을 자동 변경하지 않습니다. 필요한 변경은 WBS 화면에서 직접 반영해 주세요.
        </p>
      </AiPanel>
    </section>
  );
}

export function MailDetailSection(props: MailDetailSectionProps) {
  return (
    <Suspense fallback={<p className="m-0 border border-divider p-3 text-[13px]">메일 본문 불러오는 중…</p>}>
      <MailDetailContent {...props} />
    </Suspense>
  );
}
