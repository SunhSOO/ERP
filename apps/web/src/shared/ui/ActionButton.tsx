"use client";

import { useState, useTransition } from "react";
import { Button } from "@lep/ui";
import type { ButtonVariant } from "@lep/ui";
import type { ActionResult } from "@/src/shared/data/actions";

export interface ActionButtonProps {
  children: string;
  action: () => Promise<ActionResult>;
  variant?: ButtonVariant;
  size?: "md" | "sm";
  /** 있으면 버튼이 비활성화되고 사유가 툴팁으로 붙는다. */
  disabledReason?: string;
}

/** 서버 액션을 부르고 결과를 그 자리에 표시하는 버튼.
 *
 * 성공 문구만 띄우고 끝내지 않는다. 액션이 revalidate하므로 화면의 데이터도
 * 함께 갱신된다. 실패하면 사유와 추적 ID를 숨기지 않고 보여준다.
 */
export function ActionButton({
  children,
  action,
  variant = "secondary",
  size = "sm",
  disabledReason,
}: ActionButtonProps) {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<ActionResult | null>(null);

  const handleClick = () => {
    setResult(null);
    startTransition(async () => {
      setResult(await action());
    });
  };

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <Button
        disabled={pending || Boolean(disabledReason)}
        disabledReason={disabledReason}
        onClick={handleClick}
        size={size}
        variant={variant}
      >
        {pending ? "처리 중…" : children}
      </Button>
      {result ? (
        <span
          className={[
            "text-[11px]",
            result.ok ? "text-success-ink" : "text-danger-ink",
          ].join(" ")}
          role="status"
        >
          <span aria-hidden="true">{result.ok ? "● " : "✕ "}</span>
          {result.message}
          {result.traceId ? ` (추적 ID ${result.traceId})` : ""}
        </span>
      ) : null}
    </span>
  );
}
