import type { MailCounts, MailMessage } from "@lep/api-client";

export type MailCountsResult = MailCounts | null;

export type MailDetailResult =
  | MailMessage
  | { error: "forbidden" | "notfound" | "unknown" | "linked_file_mismatch" };

export type MailProjectsResult =
  | { ok: true; projects: Array<{ id: string; name: string }> }
  | { ok: false };
