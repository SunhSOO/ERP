"use client";

import { ErrorState } from "@lep/ui";

export interface RouteErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/** 라우트 단위 오류 화면.
 *
 * Next가 서버 컴포넌트의 오류를 이리로 넘긴다. `digest`가 서버 로그와 이어지는
 * 값이라 추적 ID로 그대로 쓴다. 백엔드가 내려가 있으면 흰 화면 대신 이것이
 * 보인다.
 */
export function RouteError({ error, reset }: RouteErrorProps) {
  const unreachable = error.name === "ApiUnreachable";

  return (
    <ErrorState
      description={
        unreachable
          ? "백엔드에 연결하지 못했습니다. API 서버가 실행 중인지 확인해 주세요."
          : error.message
      }
      onRetry={reset}
      traceId={error.digest ?? "없음"}
    />
  );
}
