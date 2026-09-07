"use client";

import { ErrorState, OfflineBanner, StaleBanner } from "@lep/ui";

/** 콜백이 필요한 상태 컴포넌트의 전시용 래퍼. */

export function ErrorStateDemo() {
  return (
    <ErrorState
      description="백엔드에 연결하지 못했습니다."
      onRetry={() => window.location.reload()}
      traceId="a6a88feb-897d-4b18-996a-b55dd2832c74"
    />
  );
}

export function StaleDemo() {
  return (
    <StaleBanner fetchedAtLabel="3분 전" onRefresh={() => window.location.reload()} />
  );
}

export function OfflineDemo() {
  return (
    <>
      <OfflineBanner />
      <p className="text-muted m-0 text-[12px]">
        네트워크가 연결돼 있으면 위 배너는 보이지 않습니다. 개발자 도구에서 오프라인으로
        전환하면 나타납니다.
      </p>
    </>
  );
}
