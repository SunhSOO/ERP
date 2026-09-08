import { redirect } from "next/navigation";

/** 시작 지점. 세션 유무는 `(app)` 레이아웃이 판단한다. */
export default function RootPage() {
  redirect("/home");
}
