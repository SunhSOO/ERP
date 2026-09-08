import type { ReactNode } from "react";

export interface Stat {
  label: string;
  value: ReactNode;
}

export interface StatBarProps {
  /** 지표 묶음이 무엇에 대한 것인지. */
  label: string;
  stats: readonly Stat[];
  className?: string;
}

/** 지표 스트립. 깃허브 연동 상태와 AI 설정 화면이 똑같이 쓴다.
 *
 * 정의 목록으로 낸다. 레이블과 값의 관계가 마크업에 남아야 스크린리더가
 * 짝지어 읽는다. */
export function StatBar({ label, stats, className }: StatBarProps) {
  return (
    <section aria-label={label}>
      <dl
        className={[
          "m-0 flex flex-wrap items-baseline gap-x-8 gap-y-3 border border-divider p-3",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {stats.map((stat) => (
          <div className="flex flex-col gap-1" key={stat.label}>
            <dt className="text-muted text-[11px] tracking-wide uppercase">{stat.label}</dt>
            <dd className="m-0 text-[14px] tabular-nums">{stat.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
