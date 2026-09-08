"use server";

import { revalidatePath } from "next/cache";
import { ApiProblem, ApiUnreachable } from "@lep/api-client";
import { gateway } from "./gateway";

/** 서버 액션의 공통 결과.
 *
 * 실패를 성공으로 숨기지 않는다. `AGENTS.md` 19절. 화면은 `message`를 그대로
 * 보여주고, 추적 ID가 있으면 함께 노출한다.
 */
export interface ActionResult {
  ok: boolean;
  message: string;
  traceId?: string;
}

async function run(
  path: string,
  successMessage: string,
  operation: () => Promise<unknown>,
): Promise<ActionResult> {
  try {
    await operation();
  } catch (error) {
    if (error instanceof ApiProblem) {
      return { ok: false, message: error.message, traceId: error.traceId };
    }
    if (error instanceof ApiUnreachable) {
      return { ok: false, message: "백엔드에 연결하지 못했습니다." };
    }
    throw error;
  }
  // 성공 토스트만 믿지 않고 바뀐 데이터를 화면에 반영한다.
  // 06_UI_UX 15절 규칙이다.
  revalidatePath(path, "layout");
  return { ok: true, message: successMessage };
}

export async function promoteClauseAction(
  projectId: string,
  clauseId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "WBS에 반영했습니다.", () =>
    gateway.promoteClause(clauseId),
  );
}

export async function resolveMismatchAction(
  projectId: string,
  mismatchId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "불일치를 처리했습니다.", () =>
    gateway.resolveMismatch(mismatchId),
  );
}

export async function syncVcsAction(projectId: string): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "동기화했습니다.", () => gateway.syncVcs(projectId));
}

export async function syncVaultAction(projectId: string): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "동기화했습니다.", () => gateway.syncVault(projectId));
}

export async function applyMeetingAction(
  projectId: string,
  meetingId: string,
  mode: "wbs" | "vault_only" | "dismiss",
): Promise<ActionResult> {
  const label = {
    wbs: "WBS와 볼트에 반영했습니다.",
    vault_only: "볼트에만 지식화했습니다.",
    dismiss: "반영하지 않기로 기록했습니다.",
  }[mode];
  return run(`/projects/${projectId}`, label, () => gateway.applyMeeting(meetingId, mode));
}

export async function promoteMailAction(
  projectId: string,
  messageId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "볼트에 노트를 만들었습니다.", () =>
    gateway.promoteMailToNote(messageId),
  );
}

export async function applyMailToWbsAction(
  projectId: string,
  messageId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "WBS 일정에 반영했습니다.", () =>
    gateway.applyMailToWbs(messageId),
  );
}

export async function dismissMailAction(
  projectId: string,
  messageId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "분류 대상에서 제외했습니다.", () =>
    gateway.dismissMail(messageId),
  );
}

export async function retryDocumentAction(
  projectId: string,
  documentId: string,
): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "변환을 다시 시도했습니다.", () =>
    gateway.retryDocument(documentId),
  );
}

export async function restartModelAction(projectId: string): Promise<ActionResult> {
  return run(`/projects/${projectId}`, "모델을 재시작했습니다.", () =>
    gateway.restartModel(projectId),
  );
}
