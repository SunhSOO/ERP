"use client";

import { useId } from "react";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

interface FieldShellProps {
  label: ReactNode;
  /** 오류 메시지. 있으면 컨트롤에 aria-invalid와 aria-describedby가 연결된다. */
  error?: string;
  /** 보조 설명. 오류와 함께 컨트롤에 연결된다. */
  hint?: string;
  className?: string;
}

interface RenderArgs {
  id: string;
  describedBy: string | undefined;
  invalid: boolean;
}

function FieldShell({
  label,
  error,
  hint,
  className,
  render,
}: FieldShellProps & { render: (args: RenderArgs) => ReactNode }) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy =
    [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className={["field", className].filter(Boolean).join(" ")}>
      <label htmlFor={id}>{label}</label>
      {render({ id, describedBy, invalid: Boolean(error) })}
      {hint ? (
        <p id={hintId} className="text-muted mt-1 mb-0 text-[12px]">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="mt-1 mb-0 text-[12px] text-danger-ink" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export interface InputFieldProps
  extends FieldShellProps,
    Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "className"> {}

export function InputField({ label, error, hint, className, ...rest }: InputFieldProps) {
  return (
    <FieldShell
      label={label}
      error={error}
      hint={hint}
      className={className}
      render={({ id, describedBy, invalid }) => (
        <input
          {...rest}
          id={id}
          className="input"
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        />
      )}
    />
  );
}

export interface TextareaFieldProps
  extends FieldShellProps,
    Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id" | "className"> {}

export function TextareaField({
  label,
  error,
  hint,
  className,
  ...rest
}: TextareaFieldProps) {
  return (
    <FieldShell
      label={label}
      error={error}
      hint={hint}
      className={className}
      render={({ id, describedBy, invalid }) => (
        <textarea
          {...rest}
          id={id}
          className="input"
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        />
      )}
    />
  );
}

export interface SelectFieldProps
  extends FieldShellProps,
    Omit<SelectHTMLAttributes<HTMLSelectElement>, "id" | "className"> {
  children: ReactNode;
}

/** 목업은 드롭다운을 `div` + ▾ 글자로 흉내 냈다. 실제 select로 바꾼다.
 * 키보드 조작과 스크린리더 안내가 공짜로 따라온다. */
export function SelectField({
  label,
  error,
  hint,
  className,
  children,
  ...rest
}: SelectFieldProps) {
  return (
    <FieldShell
      label={label}
      error={error}
      hint={hint}
      className={className}
      render={({ id, describedBy, invalid }) => (
        <select
          {...rest}
          id={id}
          className="input"
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        >
          {children}
        </select>
      )}
    />
  );
}
