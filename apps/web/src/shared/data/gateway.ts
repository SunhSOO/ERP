import { cookies } from "next/headers";
import { ApiProblem, LepClient } from "@lep/api-client";
import type {
  Clause,
  Credential,
  CurrentUser,
  DriveCategory,
  DriveFile,
  LepDocument,
  LlmServer,
  MailMessage,
  Milestone,
  Mismatch,
  Note,
  Project,
  ProjectModel,
  ProjectSummary,
  RepositoryConnection,
  SignupState,
  Statement,
  Task,
  TaskMapping,
  UploadLimits,
  VaultStatus,
  VcsStatus,
} from "@lep/api-client";

/** 백엔드 주소. 컨테이너 안에서는 compose 네트워크의 서비스 이름을 쓴다. */
const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";

/** 브라우저의 세션 쿠키를 그대로 백엔드에 넘기는 클라이언트.
 *
 * 서버 컴포넌트는 브라우저가 아니므로 쿠키가 자동으로 붙지 않는다. 여기서
 * 넘기지 않으면 로그인한 사용자의 요청이 백엔드에서 401이 된다.
 */
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

async function get<T>(path: string): Promise<T> {
  return (await (await client()).get<T>(path)).data;
}

async function list<T>(path: string): Promise<T[]> {
  return (await (await client()).list<T>(path)).data;
}

/** 화면이 데이터에 닿는 유일한 통로. */
export const gateway = {
  // ── 인증 ────────────────────────────────────────────────────────────
  signupState: (): Promise<SignupState> => get<SignupState>("/api/v1/auth/signup-state"),

  /** 로그인하지 않았으면 ``null``. 401을 예외로 올리지 않는다. */
  me: async (): Promise<CurrentUser | null> => {
    try {
      return await get<CurrentUser>("/api/v1/auth/me");
    } catch (error) {
      if (error instanceof ApiProblem && error.problem.status === 401) return null;
      throw error;
    }
  },

  // ── 프로젝트 ────────────────────────────────────────────────────────
  listProjects: (): Promise<Project[]> => list<Project>("/api/v1/projects"),

  getProject: (id: string): Promise<Project> => get<Project>(`/api/v1/projects/${id}`),

  getSummary: (id: string): Promise<ProjectSummary> =>
    get<ProjectSummary>(`/api/v1/projects/${id}/summary`),

  // ── 과업지시서와 WBS ────────────────────────────────────────────────
  listStatements: (id: string): Promise<Statement[]> =>
    list<Statement>(`/api/v1/projects/${id}/statements`),

  listClauses: (statementId: string): Promise<Clause[]> =>
    list<Clause>(`/api/v1/statements/${statementId}/clauses`),

  uploadLimits: (): Promise<UploadLimits> => get<UploadLimits>("/api/v1/upload-limits"),

  listMilestones: (id: string): Promise<Milestone[]> =>
    list<Milestone>(`/api/v1/projects/${id}/milestones`),

  listTasks: (id: string): Promise<Task[]> => list<Task>(`/api/v1/projects/${id}/tasks`),

  // ── 볼트 ────────────────────────────────────────────────────────────
  getVault: (id: string): Promise<VaultStatus> =>
    get<VaultStatus>(`/api/v1/projects/${id}/vault`),

  listNotes: (id: string): Promise<Note[]> => list<Note>(`/api/v1/projects/${id}/notes`),

  getNote: (id: string, noteId: string): Promise<Note> =>
    get<Note>(`/api/v1/projects/${id}/notes/${noteId}`),

  // ── 그 밖의 화면 ────────────────────────────────────────────────────
  listDocuments: (id: string): Promise<LepDocument[]> =>
    list<LepDocument>(`/api/v1/projects/${id}/documents`),

  getDrive: (id: string): Promise<DriveCategory[]> =>
    list<DriveCategory>(`/api/v1/projects/${id}/drive`),

  listDriveFiles: (id: string, category?: string): Promise<DriveFile[]> =>
    list<DriveFile>(
      `/api/v1/projects/${id}/drive/files${category ? `?category=${category}` : ""}`,
    ),

  listMail: (id: string): Promise<MailMessage[]> =>
    list<MailMessage>(`/api/v1/projects/${id}/mail`),

  getMail: (messageId: string): Promise<MailMessage> =>
    get<MailMessage>(`/api/v1/mail/${messageId}`),

  getVcs: (id: string): Promise<VcsStatus> => get<VcsStatus>(`/api/v1/projects/${id}/vcs`),

  getConnection: (id: string): Promise<RepositoryConnection> =>
    get<RepositoryConnection>(`/api/v1/projects/${id}/vcs/connection`),

  listMismatches: (id: string): Promise<Mismatch[]> =>
    list<Mismatch>(`/api/v1/projects/${id}/vcs/mismatches`),

  listMappings: (id: string): Promise<TaskMapping[]> =>
    list<TaskMapping>(`/api/v1/projects/${id}/vcs/mappings`),

  getServer: (): Promise<LlmServer> => get<LlmServer>("/api/v1/ai/server"),

  listModels: (): Promise<ProjectModel[]> => list<ProjectModel>("/api/v1/ai/models"),

  listCredentials: (id: string): Promise<Credential[]> =>
    list<Credential>(`/api/v1/projects/${id}/integrations`),
};
