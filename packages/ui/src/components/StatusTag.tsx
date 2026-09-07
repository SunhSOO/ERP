import type { ReactNode } from "react";

/** 상태 배지의 의미 축.
 *
 * 원시 색상 속성을 일부러 노출하지 않는다. 색상만으로 상태를 구분하는 배지를
 * 타입 수준에서 만들 수 없게 하기 위해서다.
 * `06_UI_UX_INFORMATION_ARCHITECTURE.md` 7절 규칙이다.
 */
export type StatusTone =
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "progress"
  | "idle"
  | "ai";

/** 목업이 쓰는 글리프다. 색을 못 보는 사용자도 모양으로 구분할 수 있다. */
const GLYPH: Record<StatusTone, string> = {
  success: "●",
  warning: "▲",
  danger: "✕",
  info: "●",
  progress: "◐",
  idle: "○",
  ai: "◆",
};

const TONE_CLASS: Record<StatusTone, string> = {
  success: "tag-success",
  warning: "tag-warning",
  danger: "tag-danger",
  info: "tag-info",
  progress: "tag-info",
  idle: "tag-muted",
  ai: "tag-ai",
};

export interface StatusTagProps {
  tone: StatusTone;
  /** 배지에 반드시 텍스트가 들어간다. 글리프 단독 배지는 만들 수 없다. */
  children: ReactNode;
  /** 글리프를 숨긴다. 같은 열에서 이미 의미가 반복될 때만 쓴다. */
  hideGlyph?: boolean;
  className?: string;
}

export function StatusTag({
  tone,
  children,
  hideGlyph = false,
  className,
}: StatusTagProps) {
  return (
    <span className={["tag", TONE_CLASS[tone], className].filter(Boolean).join(" ")}>
      {hideGlyph ? null : <span aria-hidden="true">{GLYPH[tone]}</span>}
      {children}
    </span>
  );
}

export type TagVariant = "accent" | "accent-2" | "neutral" | "outline";

export interface TagProps {
  variant?: TagVariant;
  children: ReactNode;
  className?: string;
}

/** 상태가 아닌 분류 배지다. 역할, 유형, 출처 표시에 쓴다. */
export function Tag({ variant = "neutral", children, className }: TagProps) {
  return (
    <span className={["tag", `tag-${variant}`, className].filter(Boolean).join(" ")}>
      {children}
    </span>
  );
}
