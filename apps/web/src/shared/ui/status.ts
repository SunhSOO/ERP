import type { StatusTone } from "@lep/ui";
import type { LinkHealth, SyncHealth, TaskStatus } from "@lep/api-client";

/** 도메인 상태값을 배지 표현으로 옮긴다.
 *
 * 한 곳에 모아 두어야 같은 상태가 화면마다 다르게 보이지 않는다. 레이블은
 * 반드시 한국어 텍스트를 낸다. 색상만으로는 상태를 전달하지 않는다.
 */

const TASK_STATUS: Record<TaskStatus, { tone: StatusTone; label: string }> = {
  planned: { tone: "idle", label: "예정" },
  in_progress: { tone: "progress", label: "진행" },
  blocked: { tone: "danger", label: "차단" },
  done: { tone: "success", label: "완료" },
  vcs_only: { tone: "warning", label: "깃허브만" },
};

export function taskStatus(status: TaskStatus): { tone: StatusTone; label: string } {
  return TASK_STATUS[status];
}

const SYNC_HEALTH: Record<SyncHealth, StatusTone> = {
  ok: "success",
  stale: "warning",
  mismatch: "danger",
  unknown: "idle",
  not_configured: "idle",
};

export function syncTone(health: SyncHealth): StatusTone {
  return SYNC_HEALTH[health];
}

const LINK_HEALTH: Record<LinkHealth, { tone: StatusTone; label: string }> = {
  ok: { tone: "success", label: "연결됨" },
  stale: { tone: "warning", label: "동기화 지연" },
  mismatch: { tone: "danger", label: "불일치" },
  expired: { tone: "danger", label: "토큰 만료" },
  not_configured: { tone: "idle", label: "미설정" },
};

export function linkHealth(health: LinkHealth): { tone: StatusTone; label: string } {
  return LINK_HEALTH[health];
}

const VAULT_HEALTH: Record<"ok" | "stale" | "failed", StatusTone> = {
  ok: "success",
  stale: "warning",
  failed: "danger",
};

export function vaultTone(health: "ok" | "stale" | "failed"): StatusTone {
  return VAULT_HEALTH[health];
}

/** 문서 변환 파이프라인 다섯 단계의 이름. */
export const PIPELINE_STAGES = [
  "초안(md)",
  "변환 대기열",
  "hwpx 생성",
  "검토",
  "발송",
] as const;
