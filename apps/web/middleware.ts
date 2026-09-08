import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "lep_session";

/** 세션이 없으면 화면을 그리기 전에 로그인으로 보낸다.
 *
 * 레이아웃에서만 막으면 늦다. Next는 레이아웃과 페이지를 나란히 렌더하므로
 * 레이아웃이 리다이렉트를 결정하는 동안 페이지의 데이터 요청이 이미 나가고,
 * 그 401이 오류 경계에 잡혀 "불러오지 못했습니다"가 뜬다. 로그인이 필요한 것과
 * 무언가 고장난 것은 다른 상황이고 사용자에게 다르게 보여야 한다.
 *
 * 미들웨어는 쿠키가 있는지만 본다. 유효한지는 백엔드만 안다. 만료된 쿠키는
 * 여기를 통과하고 `(app)` 레이아웃의 `me()`가 걸러낸다. 두 겹이 필요하다.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.next();
  }

  const login = new URL("/login", request.url);
  // 로그인 뒤에 원래 가려던 곳으로 돌려보내기 위해 남긴다.
  if (pathname !== "/home") {
    login.searchParams.set("next", `${pathname}${search}`);
  }
  return NextResponse.redirect(login);
}

export const config = {
  /* 보호할 경로만 고른다. /login과 /signup은 당연히 빠지고, 정적 자산과
     이미지 최적화 경로도 뺀다. 여기에 걸리면 매 요청이 미들웨어를 거친다. */
  matcher: ["/home/:path*", "/projects/:path*"],
};
