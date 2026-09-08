"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";
import { Button, InputField, TextareaField } from "@lep/ui";
import type { ActionResult } from "@/src/shared/data/actions";

function Submit() {
  const { pending } = useFormStatus();
  return (
    <Button disabled={pending} type="submit" variant="primary">
      {pending ? "저장 중…" : "볼트에 저장"}
    </Button>
  );
}

export interface MeetingNoteFormProps {
  action: (previous: ActionResult | null, form: FormData) => Promise<ActionResult>;
  startOpen?: boolean;
}

/** 회의록 작성 폼.
 *
 * 저장하면 프로젝트 볼트의 `meetings` 폴더에 마크다운 파일이 하나 생긴다.
 * 옵시디언에서 같은 파일을 열어 이어서 편집할 수 있다.
 */
export function MeetingNoteForm({ action, startOpen }: MeetingNoteFormProps) {
  const [open, setOpen] = useState(Boolean(startOpen));
  const [result, formAction] = useActionState<ActionResult | null, FormData>(action, null);

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} size="sm" variant="secondary">
        + 회의록 작성
      </Button>
    );
  }

  return (
    <form action={formAction} className="flex flex-col gap-3 border border-divider p-4">
      <h2 className="m-0 text-[15px]">회의록 작성</h2>

      <InputField
        autoFocus
        hint="파일 이름이 됩니다."
        label="제목"
        maxLength={200}
        name="title"
        placeholder="예: 2026-09-08 착수 회의"
        required
      />

      <TextareaField
        hint="마크다운으로 씁니다. [[다른 노트]]로 연결하면 백링크가 잡힙니다."
        label="내용"
        name="body"
        rows={10}
      />

      {result ? (
        <p
          className={[
            "m-0 text-[12.5px]",
            result.ok ? "text-success-ink" : "text-danger-ink",
          ].join(" ")}
          role="status"
        >
          <span aria-hidden="true">{result.ok ? "● " : "✕ "}</span>
          {result.message}
          {result.traceId ? ` (추적 ID ${result.traceId})` : ""}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Submit />
        <Button onClick={() => setOpen(false)} variant="ghost">
          닫기
        </Button>
      </div>
    </form>
  );
}
