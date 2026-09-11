import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const resolve = (path: string) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    // tsconfig의 paths와 같은 해석을 쓴다. 두 곳이 어긋나면 테스트만 통과하는
    // 코드가 생긴다.
    alias: {
      "@lep/ui": resolve("../../packages/ui/src"),
      "@lep/api-client": resolve("../../packages/api-client/src"),
      "@": resolve("."),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: [
      "src/**/*.test.ts",
      "src/**/*.test.tsx",
      // app/ 아래의 테스트도 포함한다. 빠져 있는 동안 app/layout.test.tsx가
      // 한 번도 돌지 않았고, 브랜드가 바뀌어도 아무도 알려 주지 않았다.
      "app/**/*.test.ts",
      "app/**/*.test.tsx",
      "../../packages/ui/src/**/*.test.ts",
      "../../packages/ui/src/**/*.test.tsx",
    ],
  },
});
