"use client";

import { useState, useTransition } from "react";
import { Button, SelectField, StatusTag } from "@lep/ui";
import type { DriveCategoryKey, MailMessage } from "@lep/api-client";
import {
  approveMailAction,
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
    : `mail-approve-${Date.now()}-${Math.random()}`;
}

export interface MailApprovalFormProps {
  reviewProjectId: string;
  message: MailMessage;
  projects: { id: string; name: string }[];
}

/** 미분류 메일을 프로젝트로 승인하는 폼. ADR-021.
 *
 * 대상 프로젝트는 기본 선택이 없고, 첨부는 전부 기본 미선택이다. 요약을
 * 확인하고 명시적으로 동의해야 최종 승인 버튼이 활성화된다.
 */
export function MailApprovalForm({ reviewProjectId, message, projects }: MailApprovalFormProps) {
  // Use the top suggestion as the default if available, otherwise use suggested_project_id fallback
  const topSuggestion = message.suggestions && message.suggestions.length > 0
    ? message.suggestions[0]
    : null;
  const defaultProjectId = topSuggestion?.project_id ?? message.suggested_project_id ?? "";

  const [targetProjectId, setTargetProjectId] = useState(defaultProjectId);
  const [selected, setSelected] = useState<Record<number, boolean>>({});
  const [categories, setCategories] = useState<Record<number, DriveCategoryKey>>({});
  const [reviewed, setReviewed] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newKey);
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MailActionResult | null>(null);

  if (!message.can_review || message.classification !== "unclassified") return null;

  const suggestedName = topSuggestion?.project_name
    ?? (message.suggested_project_id
      ? (projects.find((project) => project.id === message.suggested_project_id)?.name ??
          message.suggested_project_id)
      : null);

  function markEdited() {
    setIdempotencyKey(newKey());
    setReviewed(false);
    setConfirmed(false);
  }

  function handleTargetChange(value: string) {
    setTargetProjectId(value);
    markEdited();
  }

  function handleToggle(partIndex: number) {
    setSelected((prev) => ({ ...prev, [partIndex]: !prev[partIndex] }));
    markEdited();
  }

  function handleCategoryChange(partIndex: number, value: DriveCategoryKey) {
    setCategories((prev) => ({ ...prev, [partIndex]: value }));
    markEdited();
  }

  const selectedAttachments: AttachmentSelection[] = message.attachments
    .filter((file) => !file.linked_file_id && selected[file.part_index])
    .map((file) => ({
      part_index: file.part_index,
      category: categories[file.part_index] ?? "original",
    }));

  const canSubmit = Boolean(targetProjectId) && confirmed && !pending;

  function handleSubmit() {
    if (!canSubmit) return;
    setResult(null);
    startTransition(async () => {
      const outcome = await approveMailAction(
        reviewProjectId,
        message.id,
        targetProjectId,
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

  return (
    <section aria-label="메일 승인" className="flex flex-col gap-3 border border-divider p-3">
      <h3 className="m-0 text-[13px]">프로젝트로 승인</h3>

      {suggestedName ? (
        <p className="text-muted m-0 text-[12px]">
          추천 프로젝트: {suggestedName}. 추천은 승인이 아닙니다. 대상 프로젝트를 직접
          선택해 주세요.
        </p>
      ) : null}

      <SelectField
        disabled={pending}
        label="대상 프로젝트"
        onChange={(event) => handleTargetChange(event.target.value)}
        value={targetProjectId}
      >
        <option value="">프로젝트를 선택하세요</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </SelectField>

      {message.attachments.length > 0 ? (
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="text-muted m-0 text-[11px] tracking-wide uppercase">
            연결할 첨부 (선택하지 않으면 메일만 승인)
          </legend>
          {message.attachments.map((file) => (
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
      ) : null}

      <Button disabled={pending} onClick={() => setReviewed(true)} size="sm" variant="secondary">
        승인 내용 확인
      </Button>

      {reviewed ? (
        <div className="border border-divider p-2 text-[12.5px]">
          <p className="m-0">
            대상 프로젝트:{" "}
            {targetProjectId
              ? (projects.find((project) => project.id === targetProjectId)?.name ?? targetProjectId)
              : "선택 안 함"}
          </p>
          <p className="m-0">
            연결할 첨부:{" "}
            {selectedAttachments.length === 0
              ? "없음 (메일만 승인)"
              : selectedAttachments
                  .map((attachment) => {
                    const file = message.attachments.find(
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
            위 내용대로 승인합니다
          </label>
        </div>
      ) : null}

      <Button
        disabled={!canSubmit}
        disabledReason={
          !targetProjectId
            ? "대상 프로젝트를 선택해 주세요."
            : !confirmed
              ? "승인 내용을 확인하고 동의해 주세요."
              : undefined
        }
        onClick={handleSubmit}
        variant="primary"
      >
        {pending ? "승인 처리 중…" : "메일 승인"}
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

      {message.attachments.some((file) => file.linked_file_id) ? (
        <p className="text-muted m-0 text-[11px]">
          <StatusTag hideGlyph tone="success">
            일부 첨부는 이미 연결되어 있어 다시 선택할 수 없습니다
          </StatusTag>
        </p>
      ) : null}
    </section>
  );
}
