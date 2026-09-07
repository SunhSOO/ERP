import type { ReactNode, ThHTMLAttributes } from "react";

export interface TableProps {
  /** 표가 무엇을 담는지. 스크린리더가 먼저 읽는다. */
  caption: string;
  /** 캡션을 눈에 보이게 둘지 여부. 화면에 제목이 따로 있으면 숨긴다. */
  showCaption?: boolean;
  children: ReactNode;
  className?: string;
}

export function Table({ caption, showCaption = false, children, className }: TableProps) {
  return (
    <table className={["table", className].filter(Boolean).join(" ")}>
      <caption className={showCaption ? "text-muted mb-2 text-left text-[12px]" : "sr-only"}>
        {caption}
      </caption>
      {children}
    </table>
  );
}

export type SortDirection = "ascending" | "descending" | "none";

export interface ThProps extends Omit<ThHTMLAttributes<HTMLTableCellElement>, "scope"> {
  /** 정렬 가능한 열은 현재 정렬 상태를 알려야 한다.
   * `06_UI_UX_INFORMATION_ARCHITECTURE.md` 13절이 요구한다. */
  sort?: SortDirection;
  scope?: "col" | "row";
  children: ReactNode;
}

export function Th({ sort, scope = "col", children, ...rest }: ThProps) {
  return (
    <th {...rest} scope={scope} aria-sort={sort}>
      {children}
    </th>
  );
}
