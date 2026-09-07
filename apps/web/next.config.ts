import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 워크스페이스 패키지는 빌드 단계 없이 원본 TypeScript를 그대로 내보낸다.
  // Next가 컴파일하도록 여기에 등록한다. packages/tsconfig의 noEmit이 유지된다.
  transpilePackages: ["@lep/ui", "@lep/api-client"],
};

export default nextConfig;
