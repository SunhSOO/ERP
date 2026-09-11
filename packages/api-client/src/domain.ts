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
export type SyncHealth = "ok" | "stale" | "mismatch" | "unknown" | "not_configured";
export type LinkHealth = "ok" | "stale" | "mismatch" | "expired" | "not_configured";
export type ViewRole = "vendor" | "client";

export interface Project {
  id: string;
  code: string;
  name: string;
  customer_name: string;
  role: ViewRole;
  pm_name: string;
  created_at: string;
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
  task_count: number;
  statement_count: number;
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
  /** 파싱이 실패했으면 사유. 성공으로 숨기지 않는다. */
  parse_error: string | null;
}

export interface Clause {
  id: string;
  article: string;
  task_title: string;
  category: string;
  confidence: Confidence;
  wbs_mapping: string | null;
  promoted_task_id: string | null;
  /** 절 본문 전체. */
  body: string;
  /** 십진 번호에서 온 깊이. `1`은 1, `1.1`은 2. */
  level: number;
  parent: string | null;
  /** 수행해서 완료할 수 있는 일인지. 계약 조건은 거짓이다. */
  actionable: boolean;
  /** 분류 근거, 또는 분류하지 못한 사유. */
  classified_reason: string | null;
  /** 어느 분류기가 답했는지. `fixture`면 아무것도 분류하지 않았다는 뜻이다. */
  classified_by: string | null;
}

export interface ClassificationRun {
  classifier: string;
  total: number;
  classified: number;
  failed: number;
  /** 실제 모델을 요청했는데 쓰지 못한 사유. */
  unavailable_reason: string | null;
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
  /** 메일 첨부에서 연결된 파일이면 원본 메일 ID. ADR-021. */
  source_mail_id: string | null;
  /** 원본 메일 안에서 몇 번째 첨부였는지. 다운로드 프록시 주소에 쓴다. */
  source_part_index: number | null;
  /** 연결 출처 종류. 현재는 `"mail_attachment"`만 존재한다. */
  source_kind: string | null;
  sha256: string | null;
}

export interface MailAttachment {
  filename: string;
  content_type: string;
  size_bytes: number;
  /** 메일 안에서 몇 번째 부분인지. 내려받기 주소에 쓴다. */
  part_index: number;
  /** 승인되어 드라이브에 연결된 documents 파일 ID. 미승인이면 `null`. */
  linked_file_id: string | null;
}

/** 메일함 탭이 쓰는 분류 필터. `all`은 admin 전용 통합 조회다. */
export type MailStatusFilter = "unclassified" | "project" | "unrelated" | "all";

export interface MailCounts {
  unclassified: number;
  project: number;
  unrelated: number;
  all: number;
}

export interface MailProjectSuggestion {
  project_id: string;
  project_name: string;
  confidence: Confidence;
  reasons: string[];
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
  /** 자동 분류가 추천하는 프로젝트. 승인 전에는 참고 정보일 뿐이다. ADR-021. */
  suggested_project_id: string | null;
  intent: string | null;
  confidence: Confidence | null;
  milestone_code: string | null;
  note_id: string | null;
  handled: boolean;
  /** 낙관적 잠금에 쓰는 버전. 승인/제외/추가승인 요청에 `expected_version`으로 보낸다. */
  version: number;
  approved_by: string | null;
  approved_at: string | null;
  /** 현재 사용자가 이 메일을 검토(승인/제외)할 수 있는지. 서버가 최종 판단한다. */
  can_review: boolean;
  /** 딸려 온 파일들. "자료 전달의 건"에서는 이쪽이 본론이다. */
  attachments: MailAttachment[];
  /** 프로젝트 맥락 기반 추천. 미분류 메일에만 계산한다 (Task 5). */
  suggestions?: MailProjectSuggestion[];
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

export interface VcsConnection {
  owner: string;
  repository: string;
  version: number;
  can_edit: boolean;
}

export interface RepositoryConnection {
  connected: boolean;
  repository: string | null;
  version: number;
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

export type LlmRuntimeStatus =
  | "connected"
  | "degraded"
  | "unavailable"
  | "fixture"
  | "not_configured";

export interface LlmServer {
  name: string;
  network_note: string;
  status: LlmRuntimeStatus;
  detail: string;
  /** GPU 사용률은 /models·/api/ps 어디에서도 보고되지 않는다. 항상 null. */
  gpu_usage_percent: number | null;
  /** 적재되어 실행 중인 모델 수. 측정할 수 없을 때만 null이며 0으로 꾸미지 않는다. */
  active_model_count: number | null;
  available_model_names: string[];
  running_model_names: string[];
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

// ── 인증 ────────────────────────────────────────────────────────────────

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "member";
  /** 상단바 아바타에 쓰는 한 글자. */
  initial: string;
}

export interface SignupState {
  /** 아직 아무도 가입하지 않았으면 다음 가입자가 관리자가 된다. */
  first_account: boolean;
}

// ── 업로드 ──────────────────────────────────────────────────────────────

export interface UploadLimits {
  max_bytes: number;
  suffixes: string[];
}
