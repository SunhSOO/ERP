import type { ReactNode } from "react";

/** 로그인·가입 화면의 껍데기.
 *
 * 앱 셸을 쓰지 않는다. 아직 로그인하지 않은 사람에게 좌측 메뉴와 프로젝트
 * 검색창을 보여 줄 이유가 없고, 셸은 세션이 있다고 가정하고 그린다.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh place-items-center bg-bg px-4 py-10">
      <div className="flex w-full max-w-[380px] flex-col gap-5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="grid h-[26px] w-[26px] place-items-center bg-accent font-heading text-[15px] font-semibold text-bg"
          >
            L
          </span>
          <span className="font-heading text-[19px] font-semibold tracking-wide text-text">
            LUMINODE
          </span>
        </div>
        {children}
      </div>
    </div>
  );
}
