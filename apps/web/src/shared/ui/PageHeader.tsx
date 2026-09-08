import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  /** 제목 옆 상태 배지. */
  status?: ReactNode;
  /** 제목 아래 한 줄 설명. */
  note?: ReactNode;
  /** 오른쪽 끝 주요 액션. */
  actions?: ReactNode;
}

/** 화면 제목 줄. 목업의 모든 화면이 같은 구조를 쓴다. */
export function PageHeader({ title, status, note, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <h1 className="m-0 text-[20px]">{title}</h1>
      {status}
      {note ? <span className="text-muted text-[12px]">{note}</span> : null}
      {actions ? <div className="ml-auto flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
