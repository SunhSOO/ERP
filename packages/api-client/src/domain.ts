/** 목업 단계 임시 도메인 타입.
 *
 * 백엔드 스키마와 1:1로 맞춘다. OpenAPI 생성 클라이언트가 나오면 이 파일을
 * 대체한다. 그때까지는 이곳이 프론트엔드가 아는 유일한 계약이다.
 */

export type TaskStatus =
  | "planned"
  | "in_progress"
  | "blocked"
  | "done"
  /** WBS에 없지만 저장소에서 감지된 작업. ERP 트랙에 대응 상태가 없다. */
  | "vcs_only";

export type Confidence = "high" | "medium" | "low";
export type SyncHealth = "ok" | "stale" | "mismatch" | "unknown";
export type LinkHealth = "ok" | "stale" | "mismatch" | "expired" | "not_configured";
export type ViewRole = "vendor" | "client";

export interface Project {
  id: string;
  code: string;
  name: string;
  customer_name: string;
  role: ViewRole;
  pm_name: string;
}

export interface ProjectSummary {
  project_id: string;
  wbs_progress_percent: number | null;
  schedule_note: string | null;
  vault_health: SyncHealth;
  vault_note: string;
  unclassified_mail_count: number;
  vcs_health: SyncHealth;
  vcs_note: string;
}

export interface Milestone {
  id: string;
  code: string;
  name: string;
  status: TaskStatus;
  progress_percent: number;
  start: string;
  end: string;
}

export interface Task {
  id: string;
  code: string;
  title: string;
  milestone_id: string | null;
  status: TaskStatus;
  start: string;
  end: string;
  assignee: string | null;
  blocked_reason: string | null;
  blocked_owner: string | null;
  vcs_ref: string | null;
}

export interface Statement {
  id: string;
  filename: string;
  clause_count: number;
  classified_count: number;
  analysed: boolean;
}

export interface Clause {
  id: string;
  article: string;
  task_title: string;
  category: string;
  confidence: Confidence;
  wbs_mapping: string | null;
  promoted_task_id: string | null;
}

export interface VaultStatus {
  project_id: string;
  health: "ok" | "stale" | "failed";
  last_sync_at: string;
  note_count: number;
  vault_path: string;
}

export interface Backlink {
  target: string;
  label: string;
}

export interface Note {
  id: string;
  title: string;
  source: "meeting" | "statement" | "mail" | "manual";
  note_count: number;
  updated_at: string | null;
  body: string;
  backlinks: Backlink[];
  warning: string | null;
  task_code: string | null;
}

export interface Meeting {
  id: string;
  code: string;
  title: string;
  held_at: string;
  attendees: string[];
  apply_status: "pending" | "applied" | "dismissed";
  pending_count: number;
}

export interface Decision {
  id: string;
  ordinal: number;
  text: string;
  applied: boolean;
  milestone_code: string | null;
  new_end: string | null;
}

export interface ActionItem {
  id: string;
  text: string;
  owner: string | null;
  due: string | null;
  task_created: boolean;
  needs_approval: boolean;
}

export interface ScheduleShift {
  task_code: string;
  task_title: string;
  old_end: string;
  new_end: string;
}

export interface ApplyPreview {
  milestone_code: string | null;
  new_end: string | null;
  shifts: ScheduleShift[];
}

export interface MeetingDetail {
  meeting: Meeting;
  decisions: Decision[];
  action_items: ActionItem[];
  preview: ApplyPreview;
}

export interface LepDocument {
  id: string;
  title: string;
  /** 1 초안 · 2 변환 대기 · 3 hwpx 생성 · 4 검토 · 5 발송 */
  stage: 1 | 2 | 3 | 4 | 5;
  state: "running" | "done" | "failed";
  converter: string;
  author: string;
  updated_at: string;
  markdown: string;
  failure_reason: string | null;
}

export type DriveCategoryKey = "original" | "report" | "deliverable" | "source";

export interface DriveCategory {
  category: DriveCategoryKey;
  label: string;
  description: string;
  count: number;
  read_only: boolean;
  warning: string | null;
}

export interface DriveFile {
  id: string;
  name: string;
  category: DriveCategoryKey;
  origin: string;
  size_bytes: number;
  modified: string;
  warning: string | null;
}

export interface MailMessage {
  id: string;
  sender_name: string;
  sender_org: string;
  received_at: string;
  subject: string;
  body: string;
  classification: "project" | "unclassified" | "unrelated";
  project_id: string | null;
  intent: string | null;
  confidence: Confidence | null;
  milestone_code: string | null;
  note_id: string | null;
  handled: boolean;
}

export interface MailDetail {
  message: MailMessage;
  schedule_preview: ScheduleShift[];
}

export interface VcsStatus {
  repository: string;
  health: LinkHealth;
  last_sync_at: string;
  open_pull_requests: number;
  match_rate_percent: number;
}

export interface Mismatch {
  id: string;
  kind: "undefined_work" | "status_conflict";
  title: string;
  detail: string;
  task_code: string | null;
  vcs_ref: string;
  resolved: boolean;
}

export interface TaskMapping {
  task_code: string | null;
  task_title: string;
  vcs_ref: string;
  task_status: string;
  aligned: boolean;
}

export interface LlmServer {
  name: string;
  network_note: string;
  gpu_usage_percent: number;
  active_model_count: number;
  project_count: number;
}

export interface ProjectModel {
  project_id: string;
  project_name: string;
  model: string | null;
  state: "running" | "stopped";
  priority: "high" | "normal" | "low" | null;
  gpu_share_percent: number | null;
}

export interface Credential {
  kind: string;
  label: string;
  health: LinkHealth;
  detail: string;
  /** 실제 어댑터가 동작하려면 운영자가 넣어야 할 것. 비밀 값 자체는 담지 않는다. */
  missing_input: string | null;
}
