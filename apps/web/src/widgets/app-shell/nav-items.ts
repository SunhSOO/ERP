/** 좌측 메뉴 구성.
 *
 * 프로젝트 종속 항목은 홈에서 프로젝트를 고르기 전까지 잠긴다. 목업의
 * "프로젝트를 선택하면 열림" 그룹이다.
 *
 * 도메인 메뉴를 여기 한 곳에 등록해 두면 나중에 권한 서술자와 기능 플래그를
 * 붙이기 쉽다. WP-UI-001의 8번 절차가 요구하는 구조다.
 */

export interface NavItem {
  /** 프로젝트 경로 뒤에 붙는 조각. */
  segment: string;
  label: string;
  /** 미읽음 개수 등 뱃지에 쓸 키. 값은 화면에서 주입한다. */
  badgeKey?: "mail";
}

export const PROJECT_NAV_ITEMS: readonly NavItem[] = [
  { segment: "tasks", label: "과업지시서·태스크" },
  { segment: "wbs", label: "WBS·일정" },
  { segment: "vault", label: "지식 볼트" },
  { segment: "documents", label: "문서 생성·변환" },
  { segment: "drive", label: "드라이브" },
  { segment: "mail", label: "메일함", badgeKey: "mail" },
  { segment: "github", label: "깃허브 연동" },
  { segment: "meetings", label: "회의록" },
  { segment: "settings/ai", label: "AI·로컬 LLM 설정" },
];

export function projectHref(projectId: string, segment: string): string {
  return `/projects/${projectId}/${segment}`;
}
