import type { ReactNode } from "react";

export interface AiPanelProps {
  /** 패널 제목. 목업은 "AI 요약", "AI 분석", "변경 반영 미리보기"를 쓴다. */
  title: string;
  children: ReactNode;
  /** 근거로 이동하는 링크나 실행 버튼. */
  actions?: ReactNode;
  className?: string;
}

/** AI가 만든 내용을 담는 패널.
 *
 * AI 생성값을 사람 입력과 시각적으로 구분하라는 `AGENTS.md` 11절 규칙 때문에
 * 전용 `ai` 색상 토큰과 ◆ 표식을 쓴다. 본문에 사실과 추론이 섞이면 안 되고,
 * "완료"는 실제 실행 결과가 있을 때만 쓴다. */
export function AiPanel({ title, children, actions, className }: AiPanelProps) {
  return (
    <section
      className={[
        "flex gap-3 border border-dashed border-ai bg-ai-bg p-3 text-ai-ink",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span aria-hidden="true" className="text-ai leading-none">
        ◆
      </span>
      <div className="flex flex-1 flex-col gap-2">
        <h2 className="m-0 text-[12px] tracking-wide uppercase">{title}</h2>
        <div className="text-[13px]">{children}</div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </section>
  );
}
