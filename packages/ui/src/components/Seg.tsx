"use client";

import { useId } from "react";

export interface SegOption<T extends string> {
  value: T;
  label: string;
}

export interface SegProps<T extends string> {
  /** 그룹 레이블. 목업에는 없었다. 스크린리더가 무엇을 고르는지 알아야 한다. */
  legend: string;
  options: readonly SegOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** 레이블을 눈에 보이게 둘지 여부. 기본은 숨김이다. */
  showLegend?: boolean;
  className?: string;
}

/** 세그먼티드 컨트롤. 발주사와 용역사 전환에 쓴다.
 *
 * 라디오 입력 기반이라 좌우 방향키 이동이 브라우저에서 그대로 동작한다.
 * 목업은 fieldset 없이 벌거벗은 라디오였다. */
export function Seg<T extends string>({
  legend,
  options,
  value,
  onChange,
  showLegend = false,
  className,
}: SegProps<T>) {
  const name = useId();

  return (
    <fieldset className={["m-0 border-0 p-0", className].filter(Boolean).join(" ")}>
      <legend className={showLegend ? "text-muted mb-1 text-[12px]" : "sr-only"}>
        {legend}
      </legend>
      <div className="seg">
        {options.map((option) => (
          <label className="seg-opt" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
