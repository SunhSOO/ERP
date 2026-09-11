import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import { metadata } from "./layout";

it("publishes GAILAB as the user-facing application title", () => {
  expect(metadata.title).toBe("GAILAB ERP Platform");
  expect(metadata.description).toContain("GAILAB");
});

/* 메타데이터만 보면 모자란다. 사용자가 매 화면에서 실제로 읽는 글자는
 * 상단바와 로그인 화면의 워드마크다. 제목만 바꾸고 워드마크를 두면 탭에는
 * GAILAB, 화면에는 LUMINODE가 뜬다. */
it.each([
  ["상단바", join(__dirname, "../src/widgets/app-shell/TopBar.tsx")],
  ["로그인 화면", join(__dirname, "(auth)/layout.tsx")],
])("shows GAILAB in the %s wordmark", (_label, path) => {
  const source = readFileSync(path, "utf-8");

  expect(source).toContain("GAILAB");
  expect(source).not.toContain("LUMINODE");
});
