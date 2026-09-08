import { describe, expect, it } from "vitest";
import { DEFAULT_TARGET, safeRedirectTarget } from "./redirect-target";

describe("safeRedirectTarget", () => {
  it("같은 사이트의 경로는 그대로 쓴다", () => {
    expect(safeRedirectTarget("/projects/abc/tasks")).toBe("/projects/abc/tasks");
    expect(safeRedirectTarget("/home?tab=all")).toBe("/home?tab=all");
  });

  it("다른 호스트로 보내려는 값은 거절한다", () => {
    // 프로토콜 상대 주소. 브라우저는 이것을 다른 사이트로 읽는다.
    expect(safeRedirectTarget("//evil.example")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("/\\evil.example")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("https://evil.example")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("javascript:alert(1)")).toBe(DEFAULT_TARGET);
  });

  it("인증 화면으로 되돌리지 않는다", () => {
    expect(safeRedirectTarget("/login")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("/login?next=/login")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("/signup")).toBe(DEFAULT_TARGET);
  });

  it("값이 없으면 홈으로 간다", () => {
    expect(safeRedirectTarget(undefined)).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget("")).toBe(DEFAULT_TARGET);
    expect(safeRedirectTarget(42)).toBe(DEFAULT_TARGET);
  });
});
