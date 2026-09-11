import { cookies } from "next/headers";
import { ApiProblem, LepClient } from "@lep/api-client";
import type { DriveFile, MailCounts, MailMessage, MailStatusFilter } from "@lep/api-client";
import { mailMessagePath, mailMessageQuery } from "./mail-message-id";

/** 메일 승인 화면(ADR-021) 전용 조회 헬퍼.
 *
 * `gateway.ts`의 `listMail`/`getMail`은 옛 계약(무페이지네이션, 승인 이전
 * 프론트)을 쓰는 화면이 계속 참조하므로 손대지 않는다. 이 파일은 새 메일함이
 * 쓰는 상태/페이지 계약만 담당한다.
 */

const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";

export const MAIL_PAGE_SIZE = 6;

export const MAIL_STATUS_VALUES: readonly MailStatusFilter[] = [
  "unclassified",
  "project",
  "unrelated",
  "all",
];

async function client(): Promise<LepClient> {
  const jar = await cookies();
  const header = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  return new LepClient({
    baseUrl: BASE_URL,
    headers: header ? { cookie: header } : undefined,
  });
}

export interface MailListPage {
  messages: MailMessage[];
  total: number | null;
  hasMore: boolean;
}

export async function fetchMailPage(
  projectId: string,
  status: MailStatusFilter,
  page: number,
  suggested?: "yes" | "no",
): Promise<MailListPage> {
  const offset = mailOffset(page);
  const query = new URLSearchParams({
    status,
    offset: String(offset),
    limit: String(MAIL_PAGE_SIZE),
  });
  if (suggested) {
    query.set("suggested", suggested);
  }
  const envelope = await (
    await client()
  ).list<MailMessage>(`/api/v1/projects/${encodeURIComponent(projectId)}/mail?${query.toString()}`);
  return {
    messages: envelope.data,
    total: envelope.meta.total,
    hasMore: envelope.meta.has_more,
  };
}

export async function fetchMailCounts(projectId: string): Promise<MailCounts> {
  return (
    await (await client()).get<MailCounts>(`/api/v1/projects/${encodeURIComponent(projectId)}/mail/counts`)
  ).data;
}

/** 목록 페이지 밖의 승인된 메일 딥링크(드라이브 출처 링크)용 단건 조회.
 *
 * 서버가 actor 범위를 최종 검증한다. 호출부는 반드시 받은 메일의
 * classification/project_id(그리고 필요하면 linked_file_id)를 다시 검증하고,
 * 실패하면 다른 메일로 대체하지 않아야 한다(ADR-021).
 */
export async function fetchMailById(id: string): Promise<MailMessage> {
  return (
    await (await client()).get<MailMessage>(`/api/v1/mail/${mailMessagePath(id)}${mailMessageQuery(id)}`)
  ).data;
}

export const DRIVE_PAGE_SIZE = 50;

export interface DriveFilesPage {
  files: DriveFile[];
  total: number | null;
  hasMore: boolean;
}

/** 드라이브 파일 목록 페이지 조회.
 *
 * `gateway.listDriveFiles`는 배열만 돌려주고 `meta.total`/`has_more`를 버리므로,
 * 51번째 이후 파일에 닿을 수 있도록 이 파일에서 전용 헬퍼로 유지한다.
 */
export async function fetchDriveFilesPage(
  projectId: string,
  category: string | undefined,
  offset: number,
): Promise<DriveFilesPage> {
  const query = new URLSearchParams();
  if (category) query.set("category", category);
  query.set("offset", String(offset));
  query.set("limit", String(DRIVE_PAGE_SIZE));
  const envelope = await (
    await client()
  ).list<DriveFile>(`/api/v1/projects/${encodeURIComponent(projectId)}/drive/files?${query.toString()}`);
  return {
    files: envelope.data,
    total: envelope.meta.total,
    hasMore: envelope.meta.has_more,
  };
}

/** URL의 드라이브 `offset` 값을 안전한 0 이상의 정수로 정규화한다. */
export function normalizeDriveOffset(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) return 0;
  return parsed;
}

/** URL의 `status` 값을 안전한 필터로 정규화한다.
 *
 * 잘못된 값이나 nonadmin이 요청할 수 없는 탭(unclassified/unrelated/all)은
 * `project`로 되돌린다. 이 정규화는 UI 편의일 뿐이며, 서버가 최종 권한을
 * 강제한다(AGENTS.md 11절).
 */
export function normalizeMailStatus(
  value: string | undefined,
  isAdmin: boolean,
): MailStatusFilter {
  const fallback: MailStatusFilter = isAdmin ? "unclassified" : "project";
  if (!value || !MAIL_STATUS_VALUES.includes(value as MailStatusFilter)) return fallback;
  const status = value as MailStatusFilter;
  if (!isAdmin && status !== "project") return "project";
  return status;
}

/** URL의 `page` 값을 안전한 1 이상의 정수로 정규화한다. */
export function normalizeMailPage(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) return 1;
  return parsed;
}

export function mailOffset(page: number): number {
  return (page - 1) * MAIL_PAGE_SIZE;
}

export { ApiProblem };
