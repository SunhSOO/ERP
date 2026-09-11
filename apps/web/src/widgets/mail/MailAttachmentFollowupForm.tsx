"use client";

import { useState, useTransition } from "react";
import { Button, StatusTag } from "@lep/ui";
import type { DriveCategoryKey, MailMessage } from "@lep/api-client";
import {
  approveMailAttachmentsAction,
  type AttachmentSelection,
  type MailActionResult,
} from "@/src/shared/data/mail-review-actions";

const CATEGORY_LABEL: Record<DriveCategoryKey, string> = {
  original: "원본",
  report: "보고서",
  deliverable: "산출물",
  source: "소스",
};

const CATEGORY_OPTIONS: readonly DriveCategoryKey[] = ["original", "report", "deliverable", "source"];

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `mail-attach-${Date.now()}-${Math.random()}`;
}

export interface MailAttachmentFollowupFormProps {
  projectId: string;
  message: MailMessage;
}

/** 이미 승인된 메일에 뒤늦게 발견한 첨부를 추가로 연결하는 폼. ADR-021.
 *
 * 대상 프로젝트는 최초 승인 때 확정되어 이 폼에서는 절대 바꾸지 않는다. 이미
 * `linked_file_id`가 있는 첨부는 처음부터 선택지에 나타나지 않는다.
 */
export function MailAttachmentFollowupForm({ projectId, message }: MailAttachmentFollowupFormProps) {
  const selectable = message.attachments.filter((file) => !file.linked_file_id);

  const [selected, setSelected] = useState<Record<number, boolean>>({});
  const [categories, setCategories] = useState<Record<number, DriveCategoryKey>>({});
  const [reviewed, setReviewed] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newKey);
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MailActionResult | null>(null);

  if (
    message.classification !== "project" ||
    !message.can_review ||
    selectable.length === 0
  ) {
    return null;
  }

  function markEdited() {
    setIdempotencyKey(newKey());
    setReviewed(false);
    setConfirmed(false);
  }

  function handleToggle(partIndex: number) {
    setSelected((prev) => ({ ...prev, [partIndex]: !prev[partIndex] }));
    markEdited();
  }

  function handleCategoryChange(partIndex: number, value: DriveCategoryKey) {
    setCategories((prev) => ({ ...prev, [partIndex]: value }));
    markEdited();
  }

  const selectedAttachments: AttachmentSelection[] = selectable
    .filter((file) => selected[file.part_index])
    .map((file) => ({
      part_index: file.part_index,
      category: categories[file.part_index] ?? "original",
    }));

  const canSubmit = selectedAttachments.length > 0 && confirmed && !pending;

  function handleSubmit() {
    if (!canSubmit) return;
    setResult(null);
    startTransition(async () => {
      const outcome = await approveMailAttachmentsAction(
        projectId,
        message.id,
        message.version,
        selectedAttachments,
        idempotencyKey,
      );
      setResult(outcome);
      if (outcome.ok) {
        setIdempotencyKey(newKey());
        setReviewed(false);
        setConfirmed(false);
        setSelected({});
      }
    });
  }

  const linked = message.attachments.filter((file) => file.linked_file_id);

  return (
    <section aria-label="첨부 추가 연결" className="flex flex-col gap-3 border border-divider p-3">
      <h3 className="m-0 text-[13px]">뒤늦게 발견한 첨부 연결</h3>
      <p className="text-muted m-0 text-[12px]">
        대상 프로젝트는 최초 승인 때 정한 그대로이며 여기서 바꿀 수 없습니다.
      </p>

      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="text-muted m-0 text-[11px] tracking-wide uppercase">
          아직 연결되지 않은 첨부
        </legend>
        {selectable.map((file) => (
          <div className="flex flex-wrap items-center gap-2 text-[12.5px]" key={file.part_index}>
            <label className="flex items-center gap-2">
              <input
                checked={Boolean(selected[file.part_index])}
                disabled={pending}
                onChange={() => handleToggle(file.part_index)}
                type="checkbox"
              />
              {file.filename}
            </label>
            {selected[file.part_index] ? (
              <select
                aria-label={`${file.filename} 분류`}
                className="input"
                disabled={pending}
                onChange={(event) =>
                  handleCategoryChange(file.part_index, event.target.value as DriveCategoryKey)
                }
                value={categories[file.part_index] ?? "original"}
              >
                {CATEGORY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {CATEGORY_LABEL[option]}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
        ))}
      </fieldset>

      {linked.length > 0 ? (
        <p className="text-muted m-0 text-[12px]">
          이미 연결된 첨부: {linked.map((file) => file.filename).join(", ")}{" "}
          <StatusTag tone="success">연결완료</StatusTag>
        </p>
      ) : null}

      <Button disabled={pending} onClick={() => setReviewed(true)} size="sm" variant="secondary">
        연결 내용 확인
      </Button>

      {reviewed ? (
        <div className="border border-divider p-2 text-[12.5px]">
          <p className="m-0">
            새로 연결할 첨부:{" "}
            {selectedAttachments.length === 0
              ? "없음"
              : selectedAttachments
                  .map((attachment) => {
                    const file = selectable.find(
                      (item) => item.part_index === attachment.part_index,
                    );
                    return `${file?.filename ?? attachment.part_index} (${CATEGORY_LABEL[attachment.category as DriveCategoryKey]})`;
                  })
                  .join(", ")}
          </p>
          <label className="mt-2 flex items-center gap-2">
            <input
              checked={confirmed}
              disabled={pending}
              onChange={(event) => setConfirmed(event.target.checked)}
              type="checkbox"
            />
            위 내용대로 연결합니다
          </label>
        </div>
      ) : null}

      <Button
        disabled={!canSubmit}
        disabledReason={
          selectedAttachments.length === 0
            ? "연결할 첨부를 1개 이상 선택해 주세요."
            : !confirmed
              ? "연결 내용을 확인하고 동의해 주세요."
              : undefined
        }
        onClick={handleSubmit}
        variant="primary"
      >
        {pending ? "연결 처리 중…" : "첨부 연결"}
      </Button>

      {result ? (
        <p
          className={
            result.ok ? "m-0 text-[12px] text-success-ink" : "m-0 text-[12px] text-danger-ink"
          }
          role="status"
        >
          <span aria-hidden="true">
            {result.ok ? "● " : result.status === "conflict" ? "▲ " : "✕ "}
          </span>
          {result.status === "conflict" ? "충돌: " : ""}
          {result.message}
          {result.traceId ? ` (추적 ID ${result.traceId})` : ""}
        </p>
      ) : null}
    </section>
  );
}
