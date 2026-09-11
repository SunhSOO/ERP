import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { startTransition } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiProblem } from "@lep/api-client";
import type { CurrentUser, MailCounts, MailMessage, Project } from "@lep/api-client";

vi.mock("@/src/shared/data/gateway", () => ({
  gateway: {
    me: vi.fn(),
    listProjects: vi.fn(),
  },
}));

vi.mock("@/src/shared/data/mail-review", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/src/shared/data/mail-review")>();
  return {
    ...actual,
    fetchMailPage: vi.fn(),
    fetchMailCounts: vi.fn(),
    fetchMailById: vi.fn(),
  };
});

vi.mock("@/src/shared/data/mail-review-actions", () => ({
  promoteMailToNoteAction: vi.fn(),
}));

import { gateway } from "@/src/shared/data/gateway";
import { fetchMailById, fetchMailCounts, fetchMailPage } from "@/src/shared/data/mail-review";
import MailPage from "@/app/(app)/projects/[projectId]/mail/page";

const PROJECT_ID = "11111111-1111-4111-8111-111111111111";

function user(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: "u1",
    email: "reviewer@example.com",
    display_name: "검토자",
    role: "admin",
    initial: "검",
    ...overrides,
  };
}

function mail(overrides: Partial<MailMessage> = {}): MailMessage {
  return {
    id: "mail-1",
    sender_name: "발신자",
    sender_org: "발신 조직",
    received_at: "2026-09-09T09:00:00Z",
    subject: "제목",
    body: "본문",
    classification: "unclassified",
    project_id: null,
    suggested_project_id: null,
    intent: null,
    confidence: null,
    milestone_code: null,
    note_id: null,
    handled: false,
    version: 0,
    approved_by: null,
    approved_at: null,
    can_review: true,
    attachments: [],
    ...overrides,
  };
}

function counts(overrides: Partial<MailCounts> = {}): MailCounts {
  return { unclassified: 0, project: 0, unrelated: 0, all: 0, ...overrides };
}

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "proj-2",
    code: "PRJ-2",
    name: "다른 프로젝트",
    customer_name: "고객사",
    role: "vendor",
    pm_name: "PM",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const mockedGateway = vi.mocked(gateway);
const mockedFetchMailPage = vi.mocked(fetchMailPage);
const mockedFetchMailCounts = vi.mocked(fetchMailCounts);
const mockedFetchMailById = vi.mocked(fetchMailById);

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve: (value: T) => void = () => {};
  let reject: (reason?: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function renderPage(searchParams: Record<string, unknown> = {}) {
  const ui = await MailPage({
    params: Promise.resolve({ projectId: PROJECT_ID }),
    searchParams: Promise.resolve(searchParams),
  });
  await act(async () => {
    render(ui);
  });
}

beforeEach(() => {
  mockedGateway.me.mockReset();
  mockedGateway.listProjects.mockReset();
  mockedFetchMailPage.mockReset();
  mockedFetchMailCounts.mockReset();
  mockedFetchMailById.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("MailPage 병렬 요청 개시", () => {
  it("건수/프로젝트는 목록 조회 전에 이미 시작된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    let countsOrProjectsStarted = false;
    let listStarted = false;

    mockedFetchMailCounts.mockImplementation(async () => {
      countsOrProjectsStarted = true;
      return counts();
    });

    mockedGateway.listProjects.mockImplementation(async () => {
      countsOrProjectsStarted = true;
      return [];
    });

    mockedFetchMailPage.mockImplementation(async () => {
      listStarted = true;
      // Verify that counts/projects were started before list (via callbacks being set)
      expect(countsOrProjectsStarted).toBe(true);
      return { messages: [mail()], total: 1, hasMore: false };
    });

    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});
    expect(listStarted).toBe(true);
  });
});

describe("MailPage 독립 로딩 (deferred counts/detail/projects)", () => {
  it("건수 조회가 지연되어도 메일 목록과 페이지 네비게이션이 렌더링된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 지연
    const countsDeferred = deferred<MailCounts>();
    mockedFetchMailCounts.mockReturnValue(countsDeferred.promise);

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(mail());

    try {
      await renderPage({});

      // 목록이 렌더되어야 함
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
      const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
      expect(within(mailDetailSection).getByText("제목")).toBeInTheDocument();
      expect(screen.getByText(/1쪽 · 전체 1건/)).toBeInTheDocument();

      // 건수가 아직 없어도 목록은 보임
      expect(screen.queryByText(/미분류 \d+건/)).not.toBeInTheDocument();

      // 건수 로딩 표시가 있어야 함
      expect(screen.queryByText("건수 불러오는 중…")).toBeInTheDocument();

      // 건수 조회가 완료되면 카운트가 업데이트됨
      await act(async () => {
        countsDeferred.resolve(counts({ unclassified: 3, project: 5 }));
        await Promise.resolve();
      });

      expect(screen.getByText(/미분류 3건/)).toBeInTheDocument();
    } finally {
      countsDeferred.reject(new Error("cleanup"));
    }
  });

  it("메일 상세 조회가 지연되어도 메일 목록이 렌더링된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시 반환
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 지연
    const detailDeferred = deferred<MailMessage>();
    mockedFetchMailById.mockReturnValue(detailDeferred.promise);

    try {
      await renderPage({});

      // 목록이 렌더되어야 함
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
      expect(screen.getByText("제목")).toBeInTheDocument();

      // 상세 로딩 표시가 있어야 함
      expect(screen.queryByText("메일 본문 불러오는 중…")).toBeInTheDocument();

      // 상세 본문은 아직 없음
      expect(screen.queryByText("본문")).not.toBeInTheDocument();

      // 상세 조회가 완료되면 본문이 업데이트됨
      await act(async () => {
        detailDeferred.resolve(mail());
        await Promise.resolve();
      });

      expect(screen.getByText("본문")).toBeInTheDocument();
    } finally {
      detailDeferred.reject(new Error("cleanup"));
    }
  });

  it("프로젝트 선택지 조회가 지연되어도 메일 목록이 렌더링된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시 반환
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 지연
    const projectsDeferred = deferred<Project[]>();
    mockedGateway.listProjects.mockReturnValue(projectsDeferred.promise);

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(mail());

    try {
      await renderPage({});

      // 목록이 렌더되어야 함
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
      const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
      expect(within(mailDetailSection).getByText("제목")).toBeInTheDocument();

      // 프로젝트 로딩 표시가 있어야 함
      expect(screen.queryByText("프로젝트 불러오는 중…")).toBeInTheDocument();

      // 프로젝트 선택지는 아직 없음
      const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
      expect(within(projectNav).queryByText("등록된 프로젝트가 없습니다")).not.toBeInTheDocument();

      // 프로젝트 조회가 완료되면 업데이트됨
      await act(async () => {
        projectsDeferred.resolve([project({ id: PROJECT_ID, name: "현재 프로젝트" })]);
        await Promise.resolve();
      });

      expect(within(projectNav).getByRole("link", { name: "현재 프로젝트" })).toBeInTheDocument();
    } finally {
      projectsDeferred.reject(new Error("cleanup"));
    }
  });

  it("건수 조회 오류는 목록과 상세 렌더링을 막지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수 조회 오류
    mockedFetchMailCounts.mockRejectedValue(new Error("POP3 timeout"));

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    // 목록이 렌더되어야 함
    const mailList = screen.getByRole("region", { name: "메일 목록" });
    expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
    const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
    expect(within(mailDetailSection).getByText("제목")).toBeInTheDocument();
    expect(within(mailDetailSection).getByText("본문")).toBeInTheDocument();

    // 건수 오류 메시지는 건수 영역에만 표시
    expect(screen.getByText("건수를 확인할 수 없습니다")).toBeInTheDocument();

    // 목록과 상세 오류는 없음
    expect(screen.queryByText("메일함을 불러오지 못했습니다")).not.toBeInTheDocument();
  });

  it("상세 조회 오류(401)는 목록 렌더링을 막지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시 반환
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세 조회 오류
    mockedFetchMailById.mockRejectedValue(
      new ApiProblem({
        type: "about:blank",
        title: "권한 없음",
        status: 403,
        code: "FORBIDDEN",
      })
    );

    await renderPage({});

    // 목록이 렌더되어야 함
    const mailList = screen.getByRole("region", { name: "메일 목록" });
    expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
    expect(within(mailList).getByText("제목")).toBeInTheDocument();

    // 상세 오류 메시지는 에러 문단만 표시, 상세 영역 없음
    expect(screen.getByText(/이 메일을 볼 수 없습니다/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "메일 상세" })).not.toBeInTheDocument();
    expect(screen.queryByText("본문")).not.toBeInTheDocument();

    // 목록 오류는 없음
    expect(screen.queryByText("메일함을 불러오지 못했습니다")).not.toBeInTheDocument();
  });

  it("권한 없는 지연 상세는 본문과 액션을 표시하지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시 반환
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 지연 후 403
    const detailDeferred = deferred<MailMessage>();
    mockedFetchMailById.mockReturnValue(detailDeferred.promise);

    try {
      await renderPage({});

      // 목록이 렌더되어야 함
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();

      // 상세 로딩 중
      expect(screen.queryByText("메일 본문 불러오는 중…")).toBeInTheDocument();

      // 상세 오류 반환
      await act(async () => {
        detailDeferred.reject(
          new ApiProblem({
            type: "about:blank",
            title: "권한 없음",
            status: 403,
            code: "FORBIDDEN",
          })
        );
        await Promise.resolve();
      });

      expect(screen.getByText(/볼 수 없습니다/)).toBeInTheDocument();

      // 본문이나 승인 폼 없음
      expect(screen.queryByText("본문")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /승인/ })).not.toBeInTheDocument();
    } finally {
      detailDeferred.reject(new Error("cleanup"));
    }
  });

  it("카테고리 탭과 페이지 네비게이션은 건수 조회 지연 중에도 클릭 가능하다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수는 지연
    const countsDeferred = deferred<MailCounts>();
    mockedFetchMailCounts.mockReturnValue(countsDeferred.promise);

    // 프로젝트 선택지는 즉시 반환
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(mail());

    try {
      await renderPage({});

      // 카테고리 탭 링크가 있고 클릭 가능
      const tabs = screen.getByRole("navigation", { name: "메일 분류 탭" });
      const projectTabLink = within(tabs).getAllByRole("link").find((link) =>
        link.textContent?.includes("프로젝트별 분류됨")
      );
      expect(projectTabLink).toBeInTheDocument();
      expect(projectTabLink).toHaveAttribute("href", "?status=project&page=1");

      // 페이지 네비게이션이 있고 클릭 가능
      const pageNav = screen.getByRole("navigation", { name: "메일 목록 페이지" });
      expect(pageNav).toBeInTheDocument();
    } finally {
      countsDeferred.reject(new Error("cleanup"));
    }
  });

  it("여러 지연 요청이 동시에 해결될 때 각각의 영역이 업데이트된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시 반환
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail()],
      total: 1,
      hasMore: false,
    });

    // 건수, 프로젝트, 상세 모두 지연
    const countsDeferred = deferred<MailCounts>();
    const projectsDeferred = deferred<Project[]>();
    const detailDeferred = deferred<MailMessage>();

    mockedFetchMailCounts.mockReturnValue(countsDeferred.promise);
    mockedGateway.listProjects.mockReturnValue(projectsDeferred.promise);
    mockedFetchMailById.mockReturnValue(detailDeferred.promise);

    try {
      await renderPage({});

      // 목록만 렌더됨
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();

      // 모든 지연 요청 로딩 표시
      expect(screen.queryByText("건수 불러오는 중…")).toBeInTheDocument();
      expect(screen.queryByText("메일 본문 불러오는 중…")).toBeInTheDocument();
      expect(screen.queryByText("프로젝트 불러오는 중…")).toBeInTheDocument();

      // 모든 요청 동시에 해결
      await act(async () => {
        countsDeferred.resolve(counts({ unclassified: 5 }));
        projectsDeferred.resolve([project()]);
        detailDeferred.resolve(mail());
        await Promise.resolve();
      });

      // 각각의 영역이 업데이트됨
      expect(screen.getByText(/미분류 5건/)).toBeInTheDocument();
      const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
      expect(within(mailDetailSection).getByText("본문")).toBeInTheDocument();
      const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
      expect(within(projectNav).getByText("다른 프로젝트")).toBeInTheDocument();
    } finally {
      countsDeferred.reject(new Error("cleanup"));
      projectsDeferred.reject(new Error("cleanup"));
      detailDeferred.reject(new Error("cleanup"));
    }
  });

  it("지연된 상세가 403 에러면 제약 검증 실패를 표시한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 unclassified 상태
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ classification: "unclassified" })],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 즉시
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 403 에러
    mockedFetchMailById.mockRejectedValue(
      new ApiProblem({
        type: "about:blank",
        title: "권한 없음",
        status: 403,
        code: "FORBIDDEN",
      })
    );

    await renderPage({ status: "unclassified" });

    // 목록이 렌더됨
    const mailList = screen.getByRole("region", { name: "메일 목록" });
    expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();

    // 403 에러 - 에러 메시지만 표시, 상세 영역 없음
    expect(screen.getByText(/이 메일을 볼 수 없습니다/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "메일 상세" })).not.toBeInTheDocument();
    expect(screen.queryByText("본문")).not.toBeInTheDocument();
  });

  it("목록에서 선택한 메일은 분류가 바뀌었어도 백엔드가 허용하면 표시된다(지연 상세)", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 unclassified 상태
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "mail-1", classification: "unclassified" })],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 선택지는 즉시
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세는 지연 후 분류가 바뀌었지만 백엔드가 허용
    const detailDeferred = deferred<MailMessage>();
    mockedFetchMailById.mockReturnValue(detailDeferred.promise);

    try {
      await renderPage({ status: "unclassified" });

      // 목록이 렌더됨
      const mailList = screen.getByRole("region", { name: "메일 목록" });
      expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();

      // 상세 로딩 중
      expect(screen.queryByText("메일 본문 불러오는 중…")).toBeInTheDocument();

      // 상세 해결 - 분류가 변경되었지만 백엔드가 승인함
      await act(async () => {
        detailDeferred.resolve(
          mail({
            id: "mail-1",
            classification: "project",
            project_id: PROJECT_ID,
          })
        );
        await Promise.resolve();
      });

      // 목록에서 선택한 메일은 백엔드 허용시 표시됨
      expect(screen.getByRole("region", { name: "메일 상세" })).toHaveTextContent("제목");
      expect(screen.queryByText(/이 메일을 볼 수 없습니다/)).not.toBeInTheDocument();
    } finally {
      detailDeferred.reject(new Error("cleanup"));
    }
  });

  it("프로젝트 로드 실패: 승인된 상세는 폼 없이 목록/본문만 표시, 네비만 오류", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    const approved = mail({
      classification: "project",
      project_id: PROJECT_ID,
      approved_by: "admin@example.com",
      can_review: false,
    });

    // 목록은 즉시
    mockedFetchMailPage.mockResolvedValue({
      messages: [approved],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 로드 실패
    mockedGateway.listProjects.mockRejectedValue(new Error("network error"));

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(approved);

    await renderPage({ status: "project" });

    // 목록과 상세 본문 표시됨
    const mailList = screen.getByRole("region", { name: "메일 목록" });
    expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
    const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
    expect(within(mailDetailSection).getByText("본문")).toBeInTheDocument();

    // 프로젝트 네비게이션에만 오류
    const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
    expect(within(projectNav).getByText(/프로젝트를 불러올 수 없습니다\./)).toBeInTheDocument();

    // 승인 폼은 보이지 않음 (can_review=false이므로)
    expect(screen.queryByText(/승인 프로젝트를 불러올 수 없습니다\./)).not.toBeInTheDocument();
  });

  it("프로젝트 로드 실패: 미분류 상세는 본문 표시 후 폼 오류 표시", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    const unclassified = mail({
      classification: "unclassified",
      can_review: true,
    });

    // 목록은 즉시
    mockedFetchMailPage.mockResolvedValue({
      messages: [unclassified],
      total: 1,
      hasMore: false,
    });

    // 건수는 즉시
    mockedFetchMailCounts.mockResolvedValue(counts());

    // 프로젝트 로드 실패
    mockedGateway.listProjects.mockRejectedValue(new Error("network error"));

    // 상세는 즉시 반환
    mockedFetchMailById.mockResolvedValue(unclassified);

    await renderPage({});

    // 목록과 상세 본문 표시됨
    const mailList = screen.getByRole("region", { name: "메일 목록" });
    expect(within(mailList).getByText(/발신자/)).toBeInTheDocument();
    const mailDetailSection = screen.getByRole("region", { name: "메일 상세" });
    expect(within(mailDetailSection).getByText("본문")).toBeInTheDocument();

    // 프로젝트 네비에 오류
    const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
    expect(within(projectNav).getByText(/프로젝트를 불러올 수 없습니다\./)).toBeInTheDocument();

    // 승인 폼에 프로젝트 로드 오류 표시
    expect(screen.getByText(/승인 프로젝트를 불러올 수 없습니다\./)).toBeInTheDocument();
  });

  it("linked_file_id 미일치는 원본 소스 연결 오류 메시지 표시", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 목록은 즉시
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "in-page" })],
      total: 1,
      hasMore: false,
    });

    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedGateway.listProjects.mockResolvedValue([]);

    // 상세: linked_file_id 불일치
    mockedFetchMailById.mockResolvedValue(
      mail({
        id: "outside-page",
        classification: "project",
        project_id: PROJECT_ID,
        attachments: [
          {
            filename: "a.pdf",
            content_type: "application/pdf",
            size_bytes: 10,
            part_index: 0,
            linked_file_id: "file-other",
          },
        ],
      })
    );

    await renderPage({
      status: "project",
      mail: "outside-page",
      linked_file_id: "file-expected",
    });

    expect(screen.getByText(/원본 소스를 사용할 수 없습니다/)).toBeInTheDocument();
    expect(screen.getByText(/첨부 연결 정보가 일치하지 않습니다/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "메일 상세" })).not.toBeInTheDocument();
    expect(screen.queryByText("본문")).not.toBeInTheDocument();
  });

  it("nonadmin은 건수 헤더나 로딩 표시 없고 카테고리 섹션에 freshness 안내만 표시", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "member" }));

    const approvedMail = mail({
      classification: "project",
      project_id: PROJECT_ID,
      approved_by: "admin@example.com",
    });

    mockedFetchMailPage.mockResolvedValue({
      messages: [approvedMail],
      total: 1,
      hasMore: false,
    });

    mockedFetchMailById.mockResolvedValue(approvedMail);

    await renderPage({});

    expect(screen.queryByText("건수 불러오는 중…")).not.toBeInTheDocument();
    expect(screen.queryByText(/미분류 \d+건/)).not.toBeInTheDocument();
    expect(screen.getByText(/새 메일은 최대 30초 후 목록에 반영될 수 있습니다\./)).toBeInTheDocument();
  });

  it("메일 선택 변경 시 이전 상세/폼이 사라지고 새로운 로딩 표시가 나타난다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));

    // 두 개의 미분류 메일 (고유 본문)
    const mail1 = mail({ id: "mail-1", subject: "첫 번째", body: "첫 번째 본문" });
    const mail2 = mail({ id: "mail-2", subject: "두 번째", body: "두 번째 본문" });

    // 목록은 즉시 반환 (두 메일)
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail1, mail2],
      total: 2,
      hasMore: false,
    });

    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedGateway.listProjects.mockResolvedValue([]);

    // 첫 번째 메일 상세는 즉시, 두 번째는 지연
    const mail2DetailDeferred = deferred<MailMessage>();
    mockedFetchMailById.mockImplementation(async (id: string) => {
      if (id === "mail-1") return mail1;
      if (id === "mail-2") return mail2DetailDeferred.promise;
      return mail();
    });

    try {
      // 초기: mail-1 선택
      const initialUi = await MailPage({
        params: Promise.resolve({ projectId: PROJECT_ID }),
        searchParams: Promise.resolve({ mail: "mail-1" }),
      });

      let rerender: (ui: React.ReactElement) => void = () => {};
      await act(async () => {
        const result = render(initialUi);
        rerender = result.rerender;
      });

      const mailList = screen.getByRole("region", { name: "메일 목록" });
      let detailSection = screen.getByRole("region", { name: "메일 상세" });
      expect(within(detailSection).getByText("첫 번째")).toBeInTheDocument();
      expect(within(detailSection).getByText("첫 번째 본문")).toBeInTheDocument();

      // mail-2로 선택 변경 (startTransition으로 네비게이션 시뮬레이션)
      const nextUi = await MailPage({
        params: Promise.resolve({ projectId: PROJECT_ID }),
        searchParams: Promise.resolve({ mail: "mail-2" }),
      });

      await act(async () => {
        startTransition(() => {
          rerender(nextUi);
        });
      });

      // 트랜지션 커밋 대기: 이전 detail heading/body 사라짐, 새로운 로딩 표시
      await waitFor(() => {
        expect(screen.queryByText("첫 번째 본문")).not.toBeInTheDocument();
        expect(screen.queryByText("메일 본문 불러오는 중…")).toBeInTheDocument();
      });

      // 목록은 여전히 있음
      expect(within(mailList).getAllByText(/발신자/)).toHaveLength(2); // mail1, mail2 both in list

      // 새 상세 해결
      await act(async () => {
        mail2DetailDeferred.resolve(mail2);
        await Promise.resolve();
      });

      detailSection = screen.getByRole("region", { name: "메일 상세" });
      expect(within(detailSection).getByText("두 번째")).toBeInTheDocument();
      expect(within(detailSection).getByText("두 번째 본문")).toBeInTheDocument();
    } finally {
      mail2DetailDeferred.reject(new Error("cleanup"));
    }
  });
});
