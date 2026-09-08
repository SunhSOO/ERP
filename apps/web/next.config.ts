import path from "node:path";
import type { NextConfig } from "next";

/** 컨테이너 이미지용 독립 실행형 빌드를 켤지 여부.
 *
 * `standalone`은 추적한 파일을 심링크로 모으는데, pnpm 워크스페이스와 겹치면
 * 윈도우에서 심링크 권한이 없어 빌드가 실패한다. 개발 장비의 `pnpm build`가
 * 품질 게이트라 항상 켜 둘 수 없다. 도커 빌드에서만 켠다.
 */
const standalone = process.env.LEP_BUILD_STANDALONE === "1";

/** 서버 액션 본문의 상한.
 *
 * 기본값이 1MB다. 과업지시서는 그보다 크다. 백엔드의 `MAX_UPLOAD_BYTES`와 같은
 * 수여야 한다. 여기가 작으면 화면은 "50MB까지"라고 말해 놓고 서버 액션이 먼저
 * 413으로 끊는다. 사용자에게는 이유 없이 실패한 것으로 보인다.
 */
const MAX_UPLOAD_MB = Number(process.env.LEP_MAX_UPLOAD_MB ?? "50");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 워크스페이스 패키지는 빌드 단계 없이 원본 TypeScript를 그대로 내보낸다.
  // Next가 컴파일하도록 여기에 등록한다. packages/tsconfig의 noEmit이 유지된다.
  transpilePackages: ["@lep/ui", "@lep/api-client"],
  experimental: {
    serverActions: { bodySizeLimit: `${MAX_UPLOAD_MB}mb` },
  },
  ...(standalone
    ? {
        output: "standalone" as const,
        // pnpm 워크스페이스라 추적 기준이 저장소 루트여야 packages/*가 함께 들어간다.
        outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
      }
    : {}),
};

export default nextConfig;
