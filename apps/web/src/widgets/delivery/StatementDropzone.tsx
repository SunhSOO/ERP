"use client";

import { useActionState, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import type { DragEvent } from "react";
import type { UploadLimits } from "@lep/api-client";
import type { ActionResult } from "@/src/shared/data/actions";

export interface StatementDropzoneProps {
  /** `uploadStatementAction`에 projectId를 미리 묶어 넘긴다. */
  action: (previous: ActionResult | null, form: FormData) => Promise<ActionResult>;
  limits: UploadLimits;
}

function megabytes(bytes: number): string {
  return `${Math.round(bytes / (1024 * 1024))}MB`;
}

/** 업로드 중에는 영역 전체를 잠근다. */
function Status({ fileName }: { fileName: string | null }) {
  const { pending } = useFormStatus();

  if (pending) {
    return (
      <p className="m-0 text-[13px]" role="status">
        <span aria-hidden="true">◌ </span>
        {fileName ?? "파일"}을 올리고 조항을 나누는 중입니다…
      </p>
    );
  }
  return null;
}

/** 과업지시서를 끌어다 놓는 영역.
 *
 * 드롭하면 바로 올라간다. 확장자와 크기는 서버가 최종 판단하지만, 여기서 먼저
 * 걸러 주면 20MB를 다 올린 뒤에 거절당하는 일이 없다.
 *
 * 클릭으로도 고를 수 있어야 한다. 드래그만 되는 업로드는 키보드 사용자에게
 * 닫힌 문이다.
 */
export function StatementDropzone({ action, limits }: StatementDropzoneProps) {
  const [result, formAction] = useActionState<ActionResult | null, FormData>(action, null);
  const [over, setOver] = useState(false);
  const [rejected, setRejected] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /** 서버 규칙과 같은 기준으로 미리 본다. 통과하면 그대로 제출한다. */
  function accept(file: File): boolean {
    const dot = file.name.lastIndexOf(".");
    const suffix = dot < 0 ? "" : file.name.slice(dot).toLowerCase();

    if (!limits.suffixes.includes(suffix)) {
      setRejected(`${suffix || "확장자 없는 파일"}은 지원하지 않습니다.`);
      return false;
    }
    if (file.size > limits.max_bytes) {
      setRejected(`파일이 ${megabytes(limits.max_bytes)}보다 큽니다.`);
      return false;
    }
    setRejected(null);
    return true;
  }

  function submit(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!accept(file)) return;
    setFileName(file.name);
    formRef.current?.requestSubmit();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setOver(false);
    const dropped = event.dataTransfer.files;
    if (dropped.length === 0) return;
    // 파일 입력에 실어야 폼 제출에 함께 실린다.
    if (inputRef.current) inputRef.current.files = dropped;
    submit(dropped);
  }

  return (
    <form action={formAction} ref={formRef}>
      <div
        className={[
          "flex flex-col items-start gap-2 border border-dashed p-6 transition-colors",
          over ? "border-accent bg-accent-100" : "border-divider",
        ].join(" ")}
        onDragLeave={() => setOver(false)}
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDrop={handleDrop}
      >
        <p className="m-0 text-[13px]">
          과업지시서 파일을 끌어다 놓거나{" "}
          <label className="cursor-pointer text-accent-700 underline" htmlFor="statement-file">
            파일 선택
          </label>
          하세요.
        </p>

        <input
          className="sr-only"
          id="statement-file"
          name="file"
          onChange={(event) => submit(event.currentTarget.files)}
          ref={inputRef}
          type="file"
          accept={limits.suffixes.join(",")}
        />

        <p className="text-muted m-0 text-[12px]">
          {limits.suffixes.join(", ")} · 최대 {megabytes(limits.max_bytes)}
        </p>

        <Status fileName={fileName} />

        {rejected ? (
          <p className="m-0 text-[12px] text-danger-ink" role="alert">
            <span aria-hidden="true">✕ </span>
            {rejected}
          </p>
        ) : null}

        {result ? (
          <p
            className={[
              "m-0 text-[12px]",
              result.ok ? "text-success-ink" : "text-danger-ink",
            ].join(" ")}
            role="status"
          >
            <span aria-hidden="true">{result.ok ? "● " : "✕ "}</span>
            {result.message}
            {result.traceId ? ` (추적 ID ${result.traceId})` : ""}
          </p>
        ) : null}
      </div>
    </form>
  );
}
