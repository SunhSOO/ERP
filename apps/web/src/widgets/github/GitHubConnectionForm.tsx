"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { Button, InputField } from "@lep/ui";
import { updateVcsConnectionAction } from "@/src/shared/data/actions";
import type { ActionResult } from "@/src/shared/data/actions";
import type { RepositoryConnection } from "@lep/api-client";

function Submit() {
  const { pending } = useFormStatus();
  return (
    <Button disabled={pending} type="submit" variant="primary">
      {pending ? "저장 중…" : "저장"}
    </Button>
  );
}

export interface GitHubConnectionFormProps {
  projectId: string;
  connection: RepositoryConnection;
  canEdit: boolean;
}

export function GitHubConnectionForm({
  projectId,
  connection,
  canEdit,
}: GitHubConnectionFormProps) {
  const [result, formAction] = useActionState<ActionResult | null, FormData>(
    updateVcsConnectionAction.bind(null, projectId),
    null,
  );

  if (!canEdit) {
    return null;
  }

  const [owner, repo] = connection.repository?.split("/") ?? ["", ""];

  return (
    <form
      action={formAction}
      className="flex max-w-[520px] flex-col gap-3 border border-divider p-4"
    >
      <h2 className="m-0 text-[15px]">저장소 연동</h2>

      <InputField
        autoFocus
        label="저장소 소유자"
        maxLength={100}
        name="owner"
        placeholder="예: my-org"
        defaultValue={owner}
        required
      />

      <InputField
        label="저장소 이름"
        maxLength={100}
        name="repository"
        placeholder="예: my-repo"
        defaultValue={repo}
        required
      />

      <input type="hidden" name="expected_version" value={connection.version} />

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

      {result && result.ok ? (
        <p
          className="m-0 border border-success bg-success-bg p-2 text-[12.5px] text-success-ink"
          role="alert"
        >
          <span aria-hidden="true">✓ </span>
          {result.message}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Submit />
      </div>
    </form>
  );
}
