import { Suspense } from "react";
import type { ReactNode } from "react";
import { StatusTag } from "@lep/ui";
import type { CurrentUser } from "@lep/api-client";
import { logoutAction } from "@/src/shared/data/actions";
import { RoleSegment } from "./RoleSegment";

export interface TopBarProps {
  /** 오른쪽 상태 배지. 목업은 로컬 LLM 실행 여부나 연동 불일치 건수를 보여준다. */
  status?: ReactNode;
  /** 지금 로그인한 사람. 셸은 세션 없이 그려지지 않는다. */
  user: CurrentUser;
}

/** 상단바. 목업의 48px 높이를 그대로 쓴다. */
export function TopBar({ status, user }: TopBarProps) {
  return (
    <header className="col-span-2 flex h-topbar items-center gap-3 border-b border-divider px-4">
      <a className="flex w-[182px] items-center gap-2 no-underline" href="/home">
        <span
          aria-hidden="true"
          className="grid h-[22px] w-[22px] place-items-center bg-accent font-heading text-[13px] font-semibold text-bg"
        >
          L
        </span>
        <span className="font-heading text-[17px] font-semibold tracking-wide text-text">
          LUMINODE
        </span>
      </a>

      <form action="/search" className="contents" role="search">
        <label className="sr-only" htmlFor="global-search">
          프로젝트·태스크·문서·메일 검색
        </label>
        <div className="relative w-[340px]">
          <input
            className="input min-h-[32px] pr-16"
            id="global-search"
            name="q"
            placeholder="검색 (프로젝트·태스크·문서·메일)"
            type="search"
          />
          <kbd
            aria-hidden="true"
            className="text-muted absolute top-1/2 right-2 -translate-y-1/2 border border-divider px-1.5 py-0.5 font-mono text-[11px]"
          >
            Ctrl K
          </kbd>
        </div>
      </form>

      {/* useSearchParams는 정적 렌더에서 Suspense 경계를 폴백으로 떨어뜨린다.
          폴백을 비워 두면 수화 시점에 레이아웃이 흔들리므로 같은 크기의
          자리표시자를 그린다. */}
      <Suspense fallback={<RoleSegmentFallback />}>
        <RoleSegment />
      </Suspense>

      <div className="ml-auto flex items-center gap-3">
        {status}
        <span className="flex items-center gap-2 text-[13px]">
          <span
            aria-hidden="true"
            className="grid h-[26px] w-[26px] place-items-center bg-accent-700 text-[12px] text-white"
          >
            {user.initial}
          </span>
          {user.display_name}
          {user.role === "admin" ? <StatusTag tone="idle">관리자</StatusTag> : null}
        </span>

        {/* 로그아웃은 상태를 바꾸는 동작이라 링크가 아니라 POST여야 한다.
            링크로 두면 브라우저나 프리페치가 먼저 눌러 버릴 수 있다. */}
        <form action={logoutAction}>
          <button className="btn btn-ghost btn-sm" type="submit">
            로그아웃
          </button>
        </form>
      </div>
    </header>
  );
}

/** 역할 전환의 정적 렌더용 자리표시자. 수화 전까지 같은 자리를 차지한다. */
function RoleSegmentFallback() {
  return (
    <div aria-hidden="true" className="seg">
      <span className="seg-opt">용역사</span>
      <span className="seg-opt">발주사</span>
    </div>
  );
}

/** 목업이 상단바 오른쪽에 쓰는 연동 상태 배지들. */
export function LocalLlmStatus({ running }: { running: boolean }) {
  return running ? (
    <StatusTag tone="success">로컬 LLM 실행 중</StatusTag>
  ) : (
    <StatusTag tone="idle">로컬 LLM 중지</StatusTag>
  );
}
