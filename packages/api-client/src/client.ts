/** 백엔드 호출 클라이언트.
 *
 * 응답 봉투와 RFC 7807 오류를 해석하는 곳은 여기 하나뿐이다. 화면은 fetch를
 * 직접 부르지 않는다. `AGENTS.md` 11절이 페이지에 API 호출 로직을 넣지 말라고
 * 요구한다.
 */

export interface Meta {
  trace_id: string | null;
}

export interface ListMeta extends Meta {
  next_cursor: string | null;
  has_more: boolean;
  total: number | null;
}

export interface Envelope<T> {
  data: T;
  meta: Meta;
}

export interface ListEnvelope<T> {
  data: T[];
  meta: ListMeta;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail?: string;
  instance?: string;
  trace_id?: string;
  errors?: { field: string; message: string }[];
}

/** 백엔드가 계약대로 돌려준 오류. 화면은 이 안의 trace_id를 사용자에게 보여준다. */
export class ApiProblem extends Error {
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title);
    this.name = "ApiProblem";
    this.problem = problem;
  }

  get traceId(): string {
    return this.problem.trace_id ?? "알 수 없음";
  }

  get code(): string {
    return this.problem.code;
  }
}

/** 백엔드에 닿지도 못한 경우. 서버가 내려가 있으면 여기로 온다. */
export class ApiUnreachable extends Error {
  constructor(cause: unknown) {
    super("백엔드에 연결하지 못했습니다.");
    this.name = "ApiUnreachable";
    this.cause = cause;
  }
}

export interface ClientOptions {
  baseUrl: string;
  fetchImpl?: typeof fetch;
}

export class LepClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor({ baseUrl, fetchImpl }: ClientOptions) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetchImpl = fetchImpl ?? fetch;
  }

  async get<T>(path: string): Promise<Envelope<T>> {
    return this.request<Envelope<T>>(path, { method: "GET" });
  }

  async list<T>(path: string): Promise<ListEnvelope<T>> {
    return this.request<ListEnvelope<T>>(path, { method: "GET" });
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        ...init,
        // 목업 단계에서는 매 요청 신선한 값을 읽는다. 캐시 전략은 실데이터가
        // 들어오는 WP-PKD-020에서 정한다.
        cache: "no-store",
      });
    } catch (cause) {
      throw new ApiUnreachable(cause);
    }

    if (!response.ok) {
      throw new ApiProblem(await this.readProblem(response));
    }
    return (await response.json()) as T;
  }

  private async readProblem(response: Response): Promise<ProblemDetails> {
    try {
      const body = (await response.json()) as ProblemDetails;
      if (typeof body?.code === "string") {
        return body;
      }
    } catch {
      // 계약을 지키지 않는 응답. 아래에서 최소한의 형태로 채운다.
    }
    return {
      type: "about:blank",
      title: "요청을 처리하지 못했습니다.",
      status: response.status,
      code: "INTERNAL_ERROR",
      trace_id: response.headers.get("x-trace-id") ?? undefined,
    };
  }
}
