import { LepClient } from "@lep/api-client";
import type {
  ApplyPreview,
  Clause,
  Credential,
  DriveCategory,
  DriveFile,
  LepDocument,
  LlmServer,
  MailDetail,
  MailMessage,
  MeetingDetail,
  Meeting,
  Milestone,
  Mismatch,
  Note,
  Project,
  ProjectModel,
  ProjectSummary,
  ScheduleShift,
  Statement,
  Task,
  TaskMapping,
  VaultStatus,
  VcsStatus,
} from "@lep/api-client";

/** 백엔드 주소. 개발 기본값은 uvicorn 기본 포트다. */
const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";

const client = new LepClient({ baseUrl: BASE_URL });

/** 화면이 데이터에 닿는 유일한 통로.
 *
 * 목 데이터는 백엔드 픽스처 어댑터 한 곳에만 있다. 프론트엔드에 따로 두지
 * 않는다. 그래야 WP-PKD-020에서 PostgreSQL로 바뀔 때 화면이 그대로 남는다.
 */
export const gateway = {
  listProjects: async (): Promise<Project[]> =>
    (await client.list<Project>("/api/v1/projects")).data,

  getProject: async (id: string): Promise<Project> =>
    (await client.get<Project>(`/api/v1/projects/${id}`)).data,

  getSummary: async (id: string): Promise<ProjectSummary> =>
    (await client.get<ProjectSummary>(`/api/v1/projects/${id}/summary`)).data,

  listMilestones: async (id: string): Promise<Milestone[]> =>
    (await client.list<Milestone>(`/api/v1/projects/${id}/milestones`)).data,

  listTasks: async (id: string): Promise<Task[]> =>
    (await client.list<Task>(`/api/v1/projects/${id}/tasks`)).data,

  listStatements: async (id: string): Promise<Statement[]> =>
    (await client.list<Statement>(`/api/v1/projects/${id}/statements`)).data,

  listClauses: async (statementId: string): Promise<Clause[]> =>
    (await client.list<Clause>(`/api/v1/statements/${statementId}/clauses`)).data,

  promoteClause: async (clauseId: string): Promise<Task> =>
    (await client.post<{ data: Task }>(`/api/v1/clauses/${clauseId}/promote-to-task`)).data,

  getVault: async (id: string): Promise<VaultStatus> =>
    (await client.get<VaultStatus>(`/api/v1/projects/${id}/vault`)).data,

  syncVault: async (id: string): Promise<VaultStatus> =>
    (await client.post<{ data: VaultStatus }>(`/api/v1/projects/${id}/vault/sync`)).data,

  listNotes: async (id: string): Promise<Note[]> =>
    (await client.list<Note>(`/api/v1/projects/${id}/notes`)).data,

  getNote: async (noteId: string): Promise<Note> =>
    (await client.get<Note>(`/api/v1/notes/${noteId}`)).data,

  listMeetings: async (id: string): Promise<Meeting[]> =>
    (await client.list<Meeting>(`/api/v1/projects/${id}/meetings`)).data,

  getMeeting: async (meetingId: string): Promise<MeetingDetail> =>
    (await client.get<MeetingDetail>(`/api/v1/meetings/${meetingId}`)).data,

  applyMeeting: async (
    meetingId: string,
    mode: "wbs" | "vault_only" | "dismiss",
  ): Promise<ApplyPreview> =>
    (await client.post<{ data: ApplyPreview }>(`/api/v1/meetings/${meetingId}/apply`, { mode }))
      .data,

  listDocuments: async (id: string): Promise<LepDocument[]> =>
    (await client.list<LepDocument>(`/api/v1/projects/${id}/documents`)).data,

  getDocument: async (documentId: string): Promise<LepDocument> =>
    (await client.get<LepDocument>(`/api/v1/documents/${documentId}`)).data,

  retryDocument: async (documentId: string): Promise<LepDocument> =>
    (await client.post<{ data: LepDocument }>(`/api/v1/documents/${documentId}/retry`)).data,

  getDrive: async (id: string): Promise<DriveCategory[]> =>
    (await client.list<DriveCategory>(`/api/v1/projects/${id}/drive`)).data,

  listDriveFiles: async (id: string, category?: string): Promise<DriveFile[]> =>
    (
      await client.list<DriveFile>(
        `/api/v1/projects/${id}/drive/files${category ? `?category=${category}` : ""}`,
      )
    ).data,

  listMail: async (id: string): Promise<MailMessage[]> =>
    (await client.list<MailMessage>(`/api/v1/projects/${id}/mail`)).data,

  getMail: async (messageId: string): Promise<MailDetail> =>
    (await client.get<MailDetail>(`/api/v1/mail/${messageId}`)).data,

  promoteMailToNote: async (messageId: string): Promise<string> =>
    (await client.post<{ data: { note_id: string } }>(
      `/api/v1/mail/${messageId}/promote-to-note`,
    )).data.note_id,

  applyMailToWbs: async (messageId: string): Promise<ScheduleShift[]> =>
    (await client.post<{ data: ScheduleShift[] }>(`/api/v1/mail/${messageId}/apply-to-wbs`))
      .data,

  dismissMail: async (messageId: string): Promise<MailMessage> =>
    (await client.post<{ data: MailMessage }>(`/api/v1/mail/${messageId}/dismiss`)).data,

  getVcs: async (id: string): Promise<VcsStatus> =>
    (await client.get<VcsStatus>(`/api/v1/projects/${id}/vcs`)).data,

  syncVcs: async (id: string): Promise<VcsStatus> =>
    (await client.post<{ data: VcsStatus }>(`/api/v1/projects/${id}/vcs/sync`)).data,

  listMismatches: async (id: string): Promise<Mismatch[]> =>
    (await client.list<Mismatch>(`/api/v1/projects/${id}/vcs/mismatches`)).data,

  listMappings: async (id: string): Promise<TaskMapping[]> =>
    (await client.list<TaskMapping>(`/api/v1/projects/${id}/vcs/mappings`)).data,

  resolveMismatch: async (mismatchId: string): Promise<Mismatch> =>
    (await client.post<{ data: Mismatch }>(`/api/v1/vcs/mismatches/${mismatchId}/resolve`)).data,

  getServer: async (): Promise<LlmServer> =>
    (await client.get<LlmServer>("/api/v1/ai/server")).data,

  listModels: async (): Promise<ProjectModel[]> =>
    (await client.list<ProjectModel>("/api/v1/ai/models")).data,

  restartModel: async (id: string): Promise<ProjectModel> =>
    (await client.post<{ data: ProjectModel }>(`/api/v1/projects/${id}/ai/restart`)).data,

  listCredentials: async (id: string): Promise<Credential[]> =>
    (await client.list<Credential>(`/api/v1/projects/${id}/integrations`)).data,
};
