import type { ReactNode } from "react";

export interface BlueprintProps {
  children: ReactNode;
  className?: string;
}

/** 네 모서리에 등록 표식을 그리는 프레임이다.
 *
 * 표식은 순수 장식이라 보조기술에서 감춘다. 표식이 상자 바깥에 그려지므로
 * 부모가 overflow를 자르면 안 된다. */
export function BlueprintCorners() {
  return (
    <>
      <i className="corner tl" aria-hidden="true" />
      <i className="corner tr" aria-hidden="true" />
      <i className="corner bl" aria-hidden="true" />
      <i className="corner br" aria-hidden="true" />
    </>
  );
}

export interface CardProps {
  children: ReactNode;
  /** 모서리 등록 표식을 그린다. 홈의 프로젝트 카드가 쓴다. */
  blueprint?: boolean;
  elevation?: "sm" | "md" | "lg";
  className?: string;
  /** 카드가 하나의 영역을 이룰 때 제목과 연결한다. */
  "aria-labelledby"?: string;
  as?: "div" | "section" | "article" | "li";
}

export function Card({
  children,
  blueprint = false,
  elevation,
  className,
  as: Tag = "div",
  ...rest
}: CardProps) {
  return (
    <Tag
      {...rest}
      className={[
        "card",
        blueprint ? "blueprint" : null,
        elevation ? `elev-${elevation}` : null,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {blueprint ? <BlueprintCorners /> : null}
      {children}
    </Tag>
  );
}

export function CardKicker({ children }: { children: ReactNode }) {
  return <span className="card-kicker">{children}</span>;
}

export function CardTitle({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <span className="card-title" id={id}>
      {children}
    </span>
  );
}

export function CardBody({ children }: { children: ReactNode }) {
  return <div className="card-body">{children}</div>;
}

export function CardMeta({ children }: { children: ReactNode }) {
  return <div className="card-meta">{children}</div>;
}
