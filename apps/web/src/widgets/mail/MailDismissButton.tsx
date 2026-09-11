"use client";

import { useState, useTransition } from "react";
import { Button } from "@lep/ui";
import {
  dismissMailAction,
  type MailActionResult,
} from "@/src/shared/data/mail-review-actions";

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `mail-dismiss-${Date.now()}-${Math.random()}`;
}

export interface MailDismissButtonProps {
  reviewProjectId: string;
  messageId: string;
  version: number;
}

/** 미분류 메일을 프로젝트 무관으로 명시 제외하는 버튼. ADR-021.
 *
 * 확인 체크박스에 동의해야 버튼이 활성화된다. 실패(네트워크/5xx)해도 같은
 * idempotency key로 재시도할 수 있고, 성공하면 다음 조작을 위해 새 key를 쓴다.
 */
export function MailDismissButton({ reviewProjectId, messageId, version }: MailDismissButtonProps) {
  const [confirmed, setConfirmed] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newKey);
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MailActionResult | null>(null);

  function handleSubmit() {
    if (!confirmed || pending) return;
    setResult(null);
    startTransition(async () => {
      const outcome = await dismissMailAction(reviewProjectId, messageId, version, idempotencyKey);
      setResult(outcome);
      if (outcome.ok) {
        setIdempotencyKey(newKey());
        setConfirmed(false);
      }
    });
  }

  return (
    <div className="flex flex-col items-start gap-2 border border-divider p-3">
      <label className="flex items-center gap-2 text-[12.5px]">
        <input
          checked={confirmed}
          disabled={pending}
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        이 메일이 프로젝트와 무관함을 확인합니다
      </label>
      <Button
        disabled={!confirmed || pending}
        disabledReason={!confirmed ? "제외 확인에 동의해 주세요." : undefined}
        onClick={handleSubmit}
        variant="secondary"
      >
        {pending ? "제외 처리 중…" : "프로젝트 무관으로 제외"}
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
    </div>
  );
}
