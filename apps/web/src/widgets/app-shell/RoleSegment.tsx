"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Seg } from "@lep/ui";

export type ViewRole = "vendor" | "client";

const OPTIONS = [
  { value: "vendor", label: "용역사" },
  { value: "client", label: "발주사" },
] as const;

export function parseRole(value: string | null | undefined): ViewRole {
  return value === "client" ? "client" : "vendor";
}

/** 발주사와 용역사 보기 전환.
 *
 * 선택을 URL에 반영한다. 화면 상태를 주소로 공유할 수 있어야 한다는
 * `AGENTS.md` 11절 규칙이다.
 *
 * 지금은 보기 설정이다. 권한 경계인지 여부는 인증이 들어오는 WP-PKD-021에서
 * 확정한다. 권한 경계라면 서버가 강제해야 하고 클라이언트 토글로 둘 수 없다.
 */
export function RoleSegment() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const role = parseRole(searchParams.get("role"));

  const handleChange = (next: ViewRole) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "vendor") {
      params.delete("role");
    } else {
      params.set("role", next);
    }
    const query = params.toString();
    router.replace(query ? `?${query}` : "?", { scroll: false });
  };

  return <Seg legend="보기 역할" onChange={handleChange} options={OPTIONS} value={role} />;
}
