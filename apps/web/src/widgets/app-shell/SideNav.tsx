"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { PROJECT_NAV_ITEMS, projectHref } from "./nav-items";

export interface SideNavProps {
  /** 뱃지에 표시할 수치. 지금은 미분류 메일 건수만 쓴다. */
  badges?: { mail?: number };
}

/** 좌측 메뉴.
 *
 * 프로젝트 컨텍스트는 라우트 구조가 이미 표현한다. useParams로 projectId 유무만
 * 보면 되고 별도 컨텍스트 제공자가 필요 없다.
 *
 * 잠긴 항목을 링크로 두지 않는다. 목업은 pointer-events:none을 건 실제 링크였는데
 * 그것은 탭으로 도달하고 엔터로 활성화되는 접근성 결함이다. span으로 렌더하고
 * aria-disabled와 사유 연결을 붙인다.
 */
export function SideNav({ badges }: SideNavProps) {
  const params = useParams();
  const pathname = usePathname();
  const projectId = typeof params.projectId === "string" ? params.projectId : null;
  const hintId = "sidenav-locked-hint";

  return (
    <nav aria-label="주요 메뉴" className="side flex flex-col overflow-auto border-r border-divider py-2">
      <Link aria-current={pathname === "/home" ? "page" : undefined} href="/home">
        홈
      </Link>

      {projectId ? null : (
        <p className="text-muted m-0 px-4 pt-3 pb-1 text-[10px] tracking-wide uppercase" id={hintId}>
          프로젝트를 선택하면 열림
        </p>
      )}

      <ul className="m-0 mt-1 ml-4 flex list-none flex-col border-l border-divider p-0">
        {PROJECT_NAV_ITEMS.map((item) => {
          const badge = item.badgeKey ? badges?.[item.badgeKey] : undefined;

          if (!projectId) {
            return (
              <li key={item.segment}>
                <span aria-describedby={hintId} aria-disabled="true" className="side-locked pl-6">
                  {item.label}
                </span>
              </li>
            );
          }

          const href = projectHref(projectId, item.segment);
          const active = pathname === href || pathname.startsWith(`${href}/`);

          return (
            <li key={item.segment}>
              <Link
                aria-current={active ? "page" : undefined}
                className={["pl-6", active ? "on" : null].filter(Boolean).join(" ")}
                href={href}
              >
                <span className="flex-1">{item.label}</span>
                {badge ? (
                  <span className="tag tag-warning" aria-label={`미분류 ${badge}건`}>
                    {badge}
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
