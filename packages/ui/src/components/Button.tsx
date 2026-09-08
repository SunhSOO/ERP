import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";

interface CommonProps {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  icon?: boolean;
  block?: boolean;
  className?: string;
  children?: ReactNode;
}

function classes({ variant = "secondary", size = "md", icon, block, className }: CommonProps) {
  return [
    "btn",
    `btn-${variant}`,
    size === "sm" ? "btn-sm" : null,
    icon ? "btn-icon" : null,
    block ? "btn-block" : null,
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

export interface ButtonProps
  extends CommonProps,
    Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "children"> {
  /** 비활성 사유. 있으면 title로 노출한다.
   *
   * 사유 없이 버튼을 비활성화하지 않는다. 다음 행동과 차단 사유를 명확히 하라는
   * `06_UI_UX_INFORMATION_ARCHITECTURE.md` 5.1절 규칙이다. */
  disabledReason?: string;
}

export function Button({
  variant,
  size,
  icon,
  block,
  className,
  children,
  disabledReason,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled}
      title={disabled && disabledReason ? disabledReason : rest.title}
      aria-describedby={rest["aria-describedby"]}
      className={classes({ variant, size, icon, block, className })}
    >
      {children}
    </button>
  );
}

export interface LinkButtonProps
  extends CommonProps,
    Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className" | "children"> {}

/** 이동이 목적인 버튼이다. 실제 링크여야 새 탭 열기와 주소 복사가 동작한다. */
export function LinkButton({
  variant,
  size,
  icon,
  block,
  className,
  children,
  ...rest
}: LinkButtonProps) {
  return (
    <a {...rest} className={classes({ variant, size, icon, block, className })}>
      {children}
    </a>
  );
}
