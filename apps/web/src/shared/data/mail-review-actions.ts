"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import type { MailMessage } from "@lep/api-client";
import { mailMessagePath, mailMessageQuery } from "./mail-message-id";

/** ADR-021 메일 승인 흐름 전용 서버 액션.
 *
 * `actions.ts`의 기존 `dismissMailAction`/`promoteMailAction`은 옛 계약(버전도
 * idempotency도 없고, 응답을 재검증하지 않음)을 쓰는 화면이 참조하므로
 * 손대지 않는다. 이 화면은 `promoteMailToNoteAction`을 포함해 모든 메일 액션을
 * 여기서 자체 계약(버전 증가·상태 전이 재검증)으로 다룬다.
 */

const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface MailActionResult {
  ok: boolean;
  status: "ok" | "conflict" | "forbidden" | "error";
  message: string;
  traceId?: string;
  mail?: MailMessage;
}

export interface AttachmentSelection {
  part_index: number;
  category: string;
}

async function cookieHeader(): Promise<Record<string, string>> {
  const jar = await cookies();
  const header = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  return header ? { cookie: header } : {};
}

function statusFor(httpStatus: number): MailActionResult["status"] {
  if (httpStatus === 409) return "conflict";
  if (httpStatus === 403) return "forbidden";
  return "error";
}

async function post(path: string, idempotencyKey: string, json: unknown): Promise<Response> {
  const headers: Record<string, string> = {
    ...(await cookieHeader()),
    "content-type": "application/json",
    "Idempotency-Key": idempotencyKey,
  };
  return fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(json),
    cache: "no-store",
  });
}

async function postNoBody(path: string): Promise<Response> {
  const headers: Record<string, string> = { ...(await cookieHeader()) };
  return fetch(`${BASE_URL}${path}`, { method: "POST", headers, cache: "no-store" });
}

/** 응답 본문이 RFC 7807 계약을 지키는지 최소한으로 확인한다.
 *
 * `code`/`status`/`title`이 모두 문자열/숫자로 있어야 신뢰하고, `detail`은
 * 있을 때만 문자열이어야 한다. 아니면 백엔드/네트워크 중간의 임의 본문을 그대로
 * 사용자에게 보여주지 않는다(정보 노출 금지).
 */
function isProblemDetails(
  body: unknown,
): body is { code: string; status: number; title: string; detail?: string; trace_id?: string } {
  if (!body || typeof body !== "object") return false;
  const candidate = body as Record<string, unknown>;
  if (typeof candidate.code !== "string") return false;
  if (typeof candidate.status !== "number") return false;
  if (typeof candidate.title !== "string") return false;
  if (candidate.detail !== undefined && typeof candidate.detail !== "string") return false;
  if (candidate.trace_id !== undefined && typeof candidate.trace_id !== "string") return false;
  return true;
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorResult(response: Response, body: unknown): MailActionResult {
  if (isProblemDetails(body)) {
    return {
      ok: false,
      status: statusFor(response.status),
      message: body.detail ?? body.title,
      traceId: body.trace_id,
    };
  }
  return {
    ok: false,
    status: statusFor(response.status),
    message: `요청을 처리하지 못했습니다. (HTTP ${response.status})`,
  };
}

/** 성공 응답이 최소한 우리가 요청한 그 메일임을 확인한다(신원 일치).
 *
 * HTTP 200에 빈 JSON이나 다른 메일이 와도 성공으로 보고하지 않는다.
 */
function hasMailIdentity(data: unknown, expectedMessageId: string): data is MailMessage {
  if (!data || typeof data !== "object") return false;
  const candidate = data as Partial<MailMessage>;
  return typeof candidate.id === "string" && candidate.id.length > 0 && candidate.id === expectedMessageId;
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

/** 선택한 첨부가 모두 응답에 `linked_file_id`로 연결되어 있는지 확인한다. */
function attachmentsLinked(candidate: MailMessage, attachments: AttachmentSelection[]): boolean {
  return attachments.every((selection) => {
    const file = candidate.attachments.find((item) => item.part_index === selection.part_index);
    return Boolean(file && nonEmptyString(file.linked_file_id));
  });
}

/** 신원 일치만으로는 부족하다: HTTP 200이어도 실제로 요청한 상태 전이가
 * 일어났는지(분류/대상 프로젝트/버전 증가/승인자 등) 각 작업별로 다시
 * 검증한다. 그래야 잘못된 상태·버전·대상에 대해서도 성공으로 보고하지
 * 않는다. 재시도(동일 idempotency key)는 expectedVersion이 그대로이므로
 * 여전히 `version > expectedVersion` 조건을 만족한다.
 */
function makeApproveValidator(
  expectedMessageId: string,
  targetProjectId: string,
  expectedVersion: number,
  attachments: AttachmentSelection[],
): (data: unknown) => data is MailMessage {
  return (data): data is MailMessage => {
    if (!hasMailIdentity(data, expectedMessageId)) return false;
    const candidate = data;
    if (candidate.classification !== "project") return false;
    if (candidate.project_id !== targetProjectId) return false;
    if (typeof candidate.version !== "number" || !(candidate.version > expectedVersion)) return false;
    if (!nonEmptyString(candidate.approved_by)) return false;
    if (!nonEmptyString(candidate.approved_at)) return false;
    return attachmentsLinked(candidate, attachments);
  };
}

function makeAttachmentsValidator(
  expectedMessageId: string,
  targetProjectId: string,
  expectedVersion: number,
  attachments: AttachmentSelection[],
): (data: unknown) => data is MailMessage {
  return (data): data is MailMessage => {
    if (!hasMailIdentity(data, expectedMessageId)) return false;
    const candidate = data;
    if (candidate.classification !== "project") return false;
    if (candidate.project_id !== targetProjectId) return false;
    if (typeof candidate.version !== "number" || !(candidate.version > expectedVersion)) return false;
    return attachmentsLinked(candidate, attachments);
  };
}

function makeDismissValidator(
  expectedMessageId: string,
  expectedVersion: number,
): (data: unknown) => data is MailMessage {
  return (data): data is MailMessage => {
    if (!hasMailIdentity(data, expectedMessageId)) return false;
    const candidate = data;
    if (candidate.classification !== "unrelated") return false;
    return typeof candidate.version === "number" && candidate.version > expectedVersion;
  };
}

async function toResult(
  response: Response,
  isValid: (data: unknown) => data is MailMessage,
): Promise<MailActionResult> {
  const body = await parseJson(response);

  if (!response.ok) return errorResult(response, body);

  const data = body && typeof body === "object" ? (body as { data?: unknown }).data : undefined;
  if (!isValid(data)) {
    return {
      ok: false,
      status: "error",
      message: "서버 응답을 확인할 수 없습니다. 다시 시도해 주세요.",
    };
  }

  return { ok: true, status: "ok", message: "처리했습니다.", mail: data };
}

async function guard(run: () => Promise<MailActionResult>): Promise<MailActionResult> {
  try {
    return await run();
  } catch {
    return { ok: false, status: "error", message: "백엔드에 연결하지 못했습니다." };
  }
}

function afterApprovalRevalidate(reviewProjectId: string, targetProjectId: string): void {
  const review = encodeURIComponent(reviewProjectId);
  const target = encodeURIComponent(targetProjectId);
  revalidatePath(`/projects/${review}/mail`);
  if (target !== review) {
    revalidatePath(`/projects/${target}/mail`);
  }
  revalidatePath(`/projects/${target}/drive`);
  revalidatePath("/home");
}

/** 미분류 메일을 프로젝트로 승인한다. 첨부 0개도 유효한 선택(메일만 승인)이다. */
export async function approveMailAction(
  reviewProjectId: string,
  messageId: string,
  targetProjectId: string,
  expectedVersion: number,
  attachments: AttachmentSelection[],
  idempotencyKey: string,
): Promise<MailActionResult> {
  const result = await guard(async () => {
    const response = await post(
      `/api/v1/mail/${mailMessagePath(messageId)}/approve${mailMessageQuery(messageId)}`,
      idempotencyKey,
      {
        project_id: targetProjectId,
        expected_version: expectedVersion,
        attachments,
      },
    );
    const outcome = await toResult(
      response,
      makeApproveValidator(messageId, targetProjectId, expectedVersion, attachments),
    );
    if (outcome.ok) {
      outcome.message =
        attachments.length > 0
          ? `메일을 승인하고 첨부 ${attachments.length}개를 연결했습니다.`
          : "메일만 승인했습니다.";
    }
    return outcome;
  });

  if (result.ok) afterApprovalRevalidate(reviewProjectId, targetProjectId);
  return result;
}

/** 미분류 메일을 프로젝트 무관으로 명시 제외한다. */
export async function dismissMailAction(
  reviewProjectId: string,
  messageId: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<MailActionResult> {
  const result = await guard(async () => {
    const response = await post(
      `/api/v1/mail/${mailMessagePath(messageId)}/dismiss${mailMessageQuery(messageId)}`,
      idempotencyKey,
      { expected_version: expectedVersion },
    );
    const outcome = await toResult(response, makeDismissValidator(messageId, expectedVersion));
    if (outcome.ok) outcome.message = "메일을 프로젝트 무관으로 제외했습니다.";
    return outcome;
  });

  if (result.ok) {
    revalidatePath(`/projects/${encodeURIComponent(reviewProjectId)}/mail`);
    revalidatePath("/home");
  }
  return result;
}

/** 이미 승인된 메일에서, 처음에는 선택하지 않았던 첨부를 나중에 추가로 연결한다.
 *
 * 대상 프로젝트는 최초 승인 시점에 고정되며 이 액션은 바꾸지 않는다. 이미
 * `linked_file_id`가 있는 첨부는 폼에서부터 선택할 수 없어야 한다.
 */
export async function approveMailAttachmentsAction(
  projectId: string,
  messageId: string,
  expectedVersion: number,
  attachments: AttachmentSelection[],
  idempotencyKey: string,
): Promise<MailActionResult> {
  if (attachments.length === 0) {
    return { ok: false, status: "error", message: "추가로 연결할 첨부를 선택해 주세요." };
  }

  const result = await guard(async () => {
    const response = await post(
      `/api/v1/mail/${mailMessagePath(messageId)}/attachments/approve${mailMessageQuery(messageId)}`,
      idempotencyKey,
      { expected_version: expectedVersion, attachments },
    );
    const outcome = await toResult(
      response,
      makeAttachmentsValidator(messageId, projectId, expectedVersion, attachments),
    );
    if (outcome.ok) outcome.message = `첨부 ${attachments.length}개를 새로 연결했습니다.`;
    return outcome;
  });

  if (result.ok) {
    const encodedProjectId = encodeURIComponent(projectId);
    revalidatePath(`/projects/${encodedProjectId}/mail`);
    revalidatePath(`/projects/${encodedProjectId}/drive`);
  }
  return result;
}

/** 이미 프로젝트로 승인된 메일을 볼트 노트로 지식화한다.
 *
 * 승인 게이트는 백엔드가 강제한다(승인되지 않은 메일이면 백엔드가 거부한다).
 * 이 액션은 별도의 idempotency 계약이 없으므로 body 없이 부른다.
 */
export async function promoteMailToNoteAction(
  projectId: string,
  messageId: string,
): Promise<MailActionResult> {
  const result = await guard(async () => {
    const response = await postNoBody(
      `/api/v1/mail/${mailMessagePath(messageId)}/promote-to-note${mailMessageQuery(messageId)}`,
    );
    const body = await parseJson(response);
    if (!response.ok) return errorResult(response, body);

    const data = body && typeof body === "object" ? (body as { data?: unknown }).data : undefined;
    const noteId =
      data && typeof data === "object" ? (data as { note_id?: unknown }).note_id : undefined;
    if (!nonEmptyString(noteId)) {
      return {
        ok: false,
        status: "error",
        message: "서버 응답을 확인할 수 없습니다. 다시 시도해 주세요.",
      };
    }

    return { ok: true, status: "ok", message: "볼트에 노트를 만들었습니다." };
  });

  if (result.ok) {
    const encodedProjectId = encodeURIComponent(projectId);
    revalidatePath(`/projects/${encodedProjectId}/mail`);
    revalidatePath(`/projects/${encodedProjectId}/vault`);
    revalidatePath("/home");
  }
  return result;
}
