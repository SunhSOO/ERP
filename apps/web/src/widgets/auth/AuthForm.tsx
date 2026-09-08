"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { Button } from "@lep/ui";
import type { ActionResult } from "@/src/shared/data/actions";

type Action = (previous: ActionResult | null, form: FormData) => Promise<ActionResult>;

export interface AuthFormProps {
  action: Action;
  submitLabel: string;
  children: React.ReactNode;
}

/** 제출 중에는 버튼을 잠근다. 두 번 눌러 계정이 두 개 생기는 일을 막는다. */
function Submit({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button block disabled={pending} type="submit" variant="primary">
      {pending ? "처리 중…" : label}
    </Button>
  );
}

/** 로그인과 가입이 공유하는 폼.
 *
 * 실패를 화면에 그대로 남긴다. 서버가 준 문구와 추적 ID를 보여 주지 않으면
 * 사용자가 무엇이 잘못됐는지 알 길이 없다. `AGENTS.md` 19절.
 */
export function AuthForm({ action, submitLabel, children }: AuthFormProps) {
  const [result, formAction] = useActionState<ActionResult | null, FormData>(action, null);

  return (
    <form action={formAction} className="flex flex-col gap-3">
      {children}

      {result && !result.ok ? (
        <p
          className="m-0 border border-danger bg-danger-bg p-2 text-[12.5px] text-danger-ink"
          role="alert"
        >
          <span aria-hidden="true">✕ </span>
          {result.message}
          {result.traceId ? ` (추적 ID ${result.traceId})` : ""}
        </p>
      ) : null}

      <Submit label={submitLabel} />
    </form>
  );
}
