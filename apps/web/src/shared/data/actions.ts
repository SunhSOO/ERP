"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { ApiProblem, ApiUnreachable } from "@lep/api-client";
import { safeRedirectTarget } from "./redirect-target";

const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";
const SESSION_COOKIE = "lep_session";

/** 서버 액션의 공통 결과.
 *
 * 실패를 성공으로 숨기지 않는다. `AGENTS.md` 19절. 화면은 `message`를 그대로
 * 보여주고, 추적 ID가 있으면 함께 낸다.
 */
export interface ActionResult {
  ok: boolean;
  message: string;
  traceId?: string;
}

async function cookieHeader(): Promise<Record<string, string>> {
  const jar = await cookies();
  const header = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  return header ? { cookie: header } : {};
}

/** 백엔드가 내려준 세션 쿠키를 브라우저로 넘긴다.
 *
 * 서버 액션은 브라우저와 백엔드 사이에 있으므로 Set-Cookie를 직접 옮겨야 한다.
 * httponly와 samesite는 백엔드가 정한 값을 그대로 따른다.
 */
async function adoptSession(response: Response): Promise<void> {
  const raw = response.headers.getSetCookie?.() ?? [];
  const jar = await cookies();
  for (const entry of raw) {
    const [pair] = entry.split(";");
    const index = pair.indexOf("=");
    if (index < 0) continue;
    const name = pair.slice(0, index).trim();
    const value = pair.slice(index + 1).trim();
    if (name !== SESSION_COOKIE) continue;
    jar.set({
      name,
      value,
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      secure: entry.toLowerCase().includes("secure"),
    });
  }
}

interface CallOptions {
  method?: string;
  json?: unknown;
  body?: BodyInit;
}

async function call(path: string, options: CallOptions = {}): Promise<Response> {
  const headers: Record<string, string> = await cookieHeader();
  if (options.json !== undefined) headers["content-type"] = "application/json";

  return fetch(`${BASE_URL}${path}`, {
    method: options.method ?? "POST",
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
    cache: "no-store",
  });
}

async function toProblem(response: Response): Promise<ActionResult> {
  try {
    const body = await response.json();
    return {
      ok: false,
      message: body.detail ?? body.title ?? "요청을 처리하지 못했습니다.",
      traceId: body.trace_id,
    };
  } catch {
    return { ok: false, message: `요청을 처리하지 못했습니다. (HTTP ${response.status})` };
  }
}

async function guard(run: () => Promise<ActionResult>): Promise<ActionResult> {
  try {
    return await run();
  } catch (error) {
    if (error instanceof ApiProblem) {
      return { ok: false, message: error.message, traceId: error.traceId };
    }
    if (error instanceof ApiUnreachable || error instanceof TypeError) {
      return { ok: false, message: "백엔드에 연결하지 못했습니다." };
    }
    throw error;
  }
}

// ── 인증 ──────────────────────────────────────────────────────────────

export async function signupAction(
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call("/api/v1/auth/signup", {
      json: {
        email: String(form.get("email") ?? ""),
        display_name: String(form.get("display_name") ?? ""),
        password: String(form.get("password") ?? ""),
      },
    });
    if (!response.ok) return toProblem(response);
    await adoptSession(response);
    return { ok: true, message: "가입했습니다." };
  });

  if (result.ok) redirect(safeRedirectTarget(form.get("next")));
  return result;
}

export async function loginAction(
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call("/api/v1/auth/login", {
      json: {
        email: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
      },
    });
    if (!response.ok) return toProblem(response);
    await adoptSession(response);
    return { ok: true, message: "로그인했습니다." };
  });

  if (result.ok) redirect(safeRedirectTarget(form.get("next")));
  return result;
}

export async function logoutAction(): Promise<void> {
  try {
    await call("/api/v1/auth/logout");
  } catch {
    // 백엔드에 닿지 못해도 브라우저 쿠키는 지운다. 남겨 두면 다음 요청이
    // 계속 실패한다.
  }
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}

// ── 프로젝트 ──────────────────────────────────────────────────────────

export async function createProjectAction(
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  let createdId: string | null = null;

  const result = await guard(async () => {
    const response = await call("/api/v1/projects", {
      json: {
        name: String(form.get("name") ?? ""),
        code: String(form.get("code") ?? "") || null,
        customer_name: String(form.get("customer_name") ?? ""),
        role: String(form.get("role") ?? "vendor"),
        pm_name: String(form.get("pm_name") ?? ""),
      },
    });
    if (!response.ok) return toProblem(response);
    const body = await response.json();
    createdId = body.data.id;
    return { ok: true, message: "프로젝트를 만들었습니다." };
  });

  if (result.ok && createdId) {
    revalidatePath("/home");
    redirect(`/projects/${createdId}/tasks`);
  }
  return result;
}

export async function archiveProjectAction(projectId: string): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/archive`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "프로젝트를 보관했습니다." };
  });
  if (result.ok) revalidatePath("/home");
  return result;
}

// ── 과업지시서 업로드 ──────────────────────────────────────────────────

export async function uploadStatementAction(
  projectId: string,
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, message: "파일을 선택해 주세요." };
  }

  const result = await guard(async () => {
    const payload = new FormData();
    payload.append("file", file, file.name);
    const response = await call(`/api/v1/projects/${projectId}/statements`, {
      body: payload,
    });
    if (!response.ok) return toProblem(response);

    const body = (await response.json()).data;
    if (body.parse_error) {
      // 업로드는 됐지만 분석이 실패했다. 반쪽 성공을 성공이라 하지 않는다.
      return {
        ok: false,
        message: `업로드했지만 분석하지 못했습니다: ${body.parse_error}`,
      };
    }
    if (body.clause_count === 0) {
      return {
        ok: true,
        message: "업로드했습니다. 다만 조항을 찾지 못했습니다. 문서 형식을 확인해 주세요.",
      };
    }
    return { ok: true, message: `업로드했습니다. 조항 ${body.clause_count}개를 찾았습니다.` };
  });

  revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

export async function promoteClauseAction(
  projectId: string,
  clauseId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/clauses/${clauseId}/promote-to-task`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "WBS에 반영했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

// ── 볼트 ──────────────────────────────────────────────────────────────

export async function syncVaultAction(projectId: string): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/vault/sync`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "볼트를 다시 읽었습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

// ── 문서 변환 ─────────────────────────────────────────────────────────

export async function retryDocumentAction(
  projectId: string,
  documentId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/documents/${documentId}/retry`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "변환을 다시 요청했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/documents`);
  return result;
}

// ── 깃허브 정합 ───────────────────────────────────────────────────────

export async function updateVcsConnectionAction(
  projectId: string,
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const owner = String(form.get("owner") ?? "").trim();
    const repo = String(form.get("repository") ?? "").trim();
    const response = await call(`/api/v1/projects/${projectId}/vcs/connection`, {
      method: "PUT",
      json: {
        repository: `${owner}/${repo}`,
        expected_version: Number(form.get("expected_version") ?? 0),
      },
    });
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "저장소 연동을 업데이트했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/github`);
  return result;
}

export async function syncVcsAction(projectId: string): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/vcs/sync`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "저장소를 다시 읽었습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/github`);
  return result;
}

export async function setConnectionAction(
  projectId: string,
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/vcs/connection`, {
      method: "PUT",
      json: {
        repository: String(form.get("repository") ?? ""),
        expected_version: parseInt(String(form.get("expected_version") ?? "0"), 10),
      },
    });
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "저장소를 연결했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/github`);
  return result;
}

export async function resolveMismatchAction(
  projectId: string,
  mismatchId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/vcs/mismatches/${mismatchId}/resolve`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "확인 처리했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/github`);
  return result;
}

// ── 메일 ──────────────────────────────────────────────────────────────

export async function promoteMailAction(
  projectId: string,
  messageId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/mail/${messageId}/promote-to-note`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "볼트에 노트를 만들었습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

export async function dismissMailAction(
  projectId: string,
  messageId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/mail/${messageId}/dismiss`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "처리 완료로 표시했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/mail`);
  return result;
}

// ── 과업지시서 분류 ───────────────────────────────────────────────────

/** 조항을 분류한다. 모델이 절마다 몇 초씩 걸려 오래 걸릴 수 있다. */
export async function classifyStatementAction(
  projectId: string,
  statementId: string,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/statements/${statementId}/classify`);
    if (!response.ok) return toProblem(response);

    const run = (await response.json()).data;

    // 픽스처가 답했다는 것은 아무것도 분류하지 않았다는 뜻이다. 완료로 쓰지 않는다.
    if (run.classifier === "fixture") {
      return {
        ok: false,
        message:
          run.unavailable_reason ??
          "로컬 LLM이 설정되지 않아 분류하지 않았습니다. AI 설정을 확인해 주세요.",
      };
    }
    if (run.classified === 0) {
      return {
        ok: false,
        message: `${run.classifier}가 ${run.total}개 조항을 하나도 분류하지 못했습니다. 각 조항의 사유를 확인해 주세요.`,
      };
    }
    if (run.failed > 0) {
      // 절반의 성공을 성공이라 하지 않는다.
      return {
        ok: true,
        message: `${run.classified}개를 분류했습니다. ${run.failed}개는 실패했고 사유가 조항에 남아 있습니다.`,
      };
    }
    return { ok: true, message: `${run.classified}개 조항을 모두 분류했습니다.` };
  });

  revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

// ── 회의록 ────────────────────────────────────────────────────────────

/** 회의록은 볼트의 `meetings` 폴더에 있는 노트다. 별도 저장소가 없다. */
export async function createMeetingNoteAction(
  projectId: string,
  _previous: ActionResult | null,
  form: FormData,
): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/notes`, {
      json: {
        title: String(form.get("title") ?? ""),
        body: String(form.get("body") ?? ""),
        folder: "meetings",
      },
    });
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "회의록을 볼트에 저장했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

// ── AI 설정 ───────────────────────────────────────────────────────────

export async function restartModelAction(projectId: string): Promise<ActionResult> {
  const result = await guard(async () => {
    const response = await call(`/api/v1/projects/${projectId}/ai/restart`);
    if (!response.ok) return toProblem(response);
    return { ok: true, message: "모델을 다시 시작했습니다." };
  });
  if (result.ok) revalidatePath(`/projects/${projectId}/settings/ai`);
  return result;
}
