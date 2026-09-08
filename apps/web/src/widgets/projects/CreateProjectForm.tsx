"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";
import { Button, InputField, SelectField } from "@lep/ui";
import { createProjectAction } from "@/src/shared/data/actions";
import type { ActionResult } from "@/src/shared/data/actions";

function Submit() {
  const { pending } = useFormStatus();
  return (
    <Button disabled={pending} type="submit" variant="primary">
      {pending ? "만드는 중…" : "프로젝트 만들기"}
    </Button>
  );
}

export interface CreateProjectFormProps {
  /** PM 이름의 기본값. 비워 두면 백엔드가 로그인한 사람 이름을 넣는다. */
  defaultPmName: string;
  /** 프로젝트가 하나도 없으면 접지 않고 펼친 채로 시작한다. */
  startOpen?: boolean;
}

/** 프로젝트 생성 폼.
 *
 * 프로젝트를 만들면 백엔드가 같은 이름의 볼트 폴더를 만든다. 그래서 코드가
 * 폴더 이름 규칙을 따라야 하고, 비워 두면 이름에서 만들어 준다.
 */
export function CreateProjectForm({ defaultPmName, startOpen }: CreateProjectFormProps) {
  const [open, setOpen] = useState(Boolean(startOpen));
  const [result, formAction] = useActionState<ActionResult | null, FormData>(
    createProjectAction,
    null,
  );

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} size="sm" variant="secondary">
        + 새 프로젝트
      </Button>
    );
  }

  return (
    <form
      action={formAction}
      className="flex max-w-[520px] flex-col gap-3 border border-divider p-4"
    >
      <h2 className="m-0 text-[15px]">새 프로젝트</h2>

      <InputField
        autoFocus
        label="프로젝트 이름"
        maxLength={200}
        name="name"
        placeholder="예: 다온 스마트팩토리 구축"
        required
      />

      <InputField
        hint="비우면 이름에서 자동으로 만듭니다. 지식 볼트의 폴더 이름이 됩니다."
        label="프로젝트 코드"
        maxLength={40}
        name="code"
        pattern="[A-Za-z0-9][A-Za-z0-9_\-]{1,39}"
        placeholder="예: DAON-2026"
      />

      <InputField label="발주처" maxLength={200} name="customer_name" />

      <SelectField defaultValue="vendor" label="우리 역할" name="role">
        <option value="vendor">용역사</option>
        <option value="client">발주사</option>
      </SelectField>

      <InputField
        defaultValue={defaultPmName}
        label="PM"
        maxLength={100}
        name="pm_name"
      />

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

      <div className="flex items-center gap-2">
        <Submit />
        <Button onClick={() => setOpen(false)} variant="ghost">
          취소
        </Button>
      </div>
    </form>
  );
}
