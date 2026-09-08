/** 로그인·가입 뒤 돌아갈 곳을 정한다.
 *
 * 값이 사용자 입력(주소창의 `?next=`)에서 오므로 그대로 믿지 않는다. 같은
 * 사이트의 절대 경로만 받는다. 열린 리다이렉트는 로그인 화면이 그럴듯하게
 * 보이는 만큼 위험하다. 로그인한 직후 낯선 사이트로 튕기면 사용자는 그것이
 * 우리 흐름의 일부라고 믿는다.
 */
export const DEFAULT_TARGET = "/home";

export function safeRedirectTarget(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) return DEFAULT_TARGET;

  // 다른 호스트로 가는 모든 표기를 막는다. `//evil.example`은 프로토콜 상대
  // 주소이고, `/\evil.example`은 일부 브라우저가 같게 읽는다.
  if (!value.startsWith("/")) return DEFAULT_TARGET;
  if (value.startsWith("//") || value.startsWith("/\\")) return DEFAULT_TARGET;

  // 인증 화면으로 되돌리면 고리가 된다.
  if (value === "/login" || value.startsWith("/login?")) return DEFAULT_TARGET;
  if (value === "/signup" || value.startsWith("/signup?")) return DEFAULT_TARGET;

  return value;
}
