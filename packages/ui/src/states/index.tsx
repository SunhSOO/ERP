"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Button } from "../components/Button";

/* 06_UI_UX_INFORMATION_ARCHITECTURE.md 6절이 모든 화면에 일곱 상태를 요구한다.
 * 규칙을 주석이 아니라 필수 속성으로 강제한다. */

/* ── Loading ────────────────────────────────────────────────────────────
 * 무한 스피너를 쓰지 않는다. 실제 레이아웃 형태의 스켈레톤만 쓴다. */

export interface SkeletonProps {
  /** 몇 줄짜리 자리표시자를 그릴지. */
  lines?: number;
  className?: string;
}

export function Skeleton({ lines = 3, className }: SkeletonProps) {
  return (
    <div className={["flex flex-col gap-2", className].filter(Boolean).join(" ")}>
      <span className="sr-only" role="status">
        불러오는 중
      </span>
      {Array.from({ length: lines }, (_, index) => (
        <span
          aria-hidden="true"
          className="block h-4 animate-pulse bg-neutral-200"
          key={index}
          style={{ width: `${100 - index * 8}%` }}
        />
      ))}
    </div>
  );
}

/* ── Empty ──────────────────────────────────────────────────────────────
 * 데이터 없음과 필터 결과 없음은 다른 상황이다. 문구도 다음 행동도 달라야 한다.
 * variant를 필수로 두어 둘을 뭉뚱그릴 수 없게 한다. */

export interface EmptyStateProps {
  variant: "no-data" | "no-results";
  title: string;
  description?: string;
  /** no-data면 생성 행동, no-results면 필터 초기화를 준다. */
  action?: ReactNode;
}

export function EmptyState({ variant, title, description, action }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-start gap-2 border border-dashed border-divider p-6"
      data-empty-variant={variant}
    >
      <p className="m-0 text-[15px]">{title}</p>
      {description ? <p className="text-muted m-0 text-[13px]">{description}</p> : null}
      {action}
    </div>
  );
}

/* ── Error ──────────────────────────────────────────────────────────────
 * 추적 ID 없이 오류를 보여주지 않는다. 사용자가 문의할 때 필요하다. */

export interface ErrorStateProps {
  title?: string;
  description?: string;
  /** 서버가 X-Trace-ID로 준 값 또는 Next의 error.digest. */
  traceId: string;
  onRetry: () => void;
}

export function ErrorState({
  title = "불러오지 못했습니다",
  description,
  traceId,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-start gap-3 border border-danger bg-danger-bg p-6 text-danger-ink">
      <p className="m-0 text-[15px]">{title}</p>
      {description ? <p className="m-0 text-[13px]">{description}</p> : null}
      <p className="m-0 text-[12px]">
        추적 ID <code className="bg-bg px-1 py-0.5 font-mono select-all">{traceId}</code>
      </p>
      <Button onClick={onRetry} variant="secondary" size="sm">
        다시 시도
      </Button>
    </div>
  );
}

/* ── Forbidden ──────────────────────────────────────────────────────────
 * 권한이 없다는 말만으로는 사용자가 할 수 있는 게 없다. 필요한 권한과 문의
 * 대상을 반드시 함께 준다. 전체 화면을 갈아치우지 않고 본문 안에서 렌더한다. */

export interface ForbiddenStateProps {
  requiredPermission: string;
  contact: string;
  description?: string;
}

export function ForbiddenState({
  requiredPermission,
  contact,
  description,
}: ForbiddenStateProps) {
  return (
    <div className="flex flex-col items-start gap-2 border border-divider p-6">
      <p className="m-0 text-[15px]">이 화면을 볼 권한이 없습니다</p>
      {description ? <p className="text-muted m-0 text-[13px]">{description}</p> : null}
      <p className="m-0 text-[13px]">
        필요한 권한 <code className="font-mono">{requiredPermission}</code>
      </p>
      <p className="text-muted m-0 text-[13px]">문의 {contact}</p>
    </div>
  );
}

/* ── Stale ──────────────────────────────────────────────────────────────
 * 화면이 보고 있는 데이터가 언제 것인지 숨기지 않는다. */

export interface StaleBannerProps {
  fetchedAtLabel: string;
  onRefresh: () => void;
}

export function StaleBanner({ fetchedAtLabel, onRefresh }: StaleBannerProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 border border-warning bg-warning-bg p-2 text-warning-ink"
      role="status"
    >
      <span aria-hidden="true">▲</span>
      <span className="text-[13px]">데이터가 갱신됐습니다. 표시된 값은 {fetchedAtLabel} 기준입니다.</span>
      <Button onClick={onRefresh} variant="secondary" size="sm">
        새로고침
      </Button>
    </div>
  );
}

/* ── Offline ────────────────────────────────────────────────────────────
 * 저장이 되는지 안 되는지를 명시한다. 사용자가 입력을 잃지 않게 하기 위해서다. */

export function OfflineBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      className="flex items-center gap-3 border border-danger bg-danger-bg p-2 text-danger-ink"
      role="alert"
    >
      <span aria-hidden="true">✕</span>
      <span className="text-[13px]">
        네트워크가 끊겼습니다. 지금은 저장할 수 없습니다. 입력한 내용을 다른 곳에 옮겨 두세요.
      </span>
    </div>
  );
}

/* ── Partial failure ────────────────────────────────────────────────────
 * 위젯 하나가 실패해도 화면 전체를 막지 않는다. */

export interface PartialFailureNoticeProps {
  /** 무엇이 실패했는지. "예산 소진율"처럼 위젯 이름을 넣는다. */
  what: string;
  traceId?: string;
  onRetry?: () => void;
}

export function PartialFailureNotice({ what, traceId, onRetry }: PartialFailureNoticeProps) {
  return (
    <div className="flex flex-col items-start gap-2 border border-warning bg-warning-bg p-3 text-warning-ink">
      <p className="m-0 text-[13px]">
        <span aria-hidden="true">▲ </span>
        {what}을(를) 불러오지 못했습니다. 나머지는 정상입니다.
      </p>
      {traceId ? (
        <p className="m-0 text-[11px]">
          추적 ID <code className="font-mono select-all">{traceId}</code>
        </p>
      ) : null}
      {onRetry ? (
        <Button onClick={onRetry} variant="secondary" size="sm">
          이 항목만 다시 시도
        </Button>
      ) : null}
    </div>
  );
}
