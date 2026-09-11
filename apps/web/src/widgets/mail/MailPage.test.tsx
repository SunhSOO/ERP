import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
    suggestions: [],
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

async function renderPage(searchParams: Record<string, string> = {}) {
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

describe("MailPage", () => {
  it("admin은 탭과 건수를 보고 기본으로 미분류 탭을 조회한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([project()]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 3, project: 5 }));
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    expect(mockedFetchMailPage).toHaveBeenCalledWith(PROJECT_ID, "unclassified", 1, undefined);
    expect(mockedFetchMailById).toHaveBeenCalledWith("mail-1");
    expect(screen.getByText("미분류 3건")).toBeInTheDocument();

    const tabs = screen.getByRole("navigation", { name: "메일 분류 탭" });
    const tabLinks = within(tabs).getAllByRole("link");
    const projectTab = tabLinks.find((link) => link.textContent?.includes("프로젝트별 분류됨"));
    expect(projectTab?.textContent).toContain("(5)");
  });

  it("현재 카테고리 탭은 aria-current로 표시된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 3, project: 5 }));

    await renderPage({ status: "unclassified", page: "4" });

    const tabs = screen.getByRole("navigation", { name: "메일 분류 탭" });
    expect(within(tabs).getByRole("link", { name: (name) => name.startsWith("미분류") })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      within(tabs).getByRole("link", { name: (name) => name.startsWith("프로젝트별 분류됨") }),
    ).not.toHaveAttribute("aria-current");
  });

  it("admin은 프로젝트별 분류됨 네비게이션에서 프로젝트 링크를 경로 인코딩해 렌더링한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([
      project({ id: "proj/a b&c", name: "특수 프로젝트" }),
      project({ id: "other", name: "다른 프로젝트" }),
    ]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ project: 1 }));
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ status: "project", page: "3" });

    const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
    expect(within(projectNav).getByRole("link", { name: "특수 프로젝트" })).toHaveAttribute(
      "href",
      "/projects/proj%2Fa%20b%26c/mail?status=project&page=1",
    );
  });

  it("admin은 분류 카테고리가 project일 때만 현재 프로젝트를 active 처리한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([
      project({ id: PROJECT_ID, name: "현재 프로젝트" }),
      project({ id: "other", name: "다른 프로젝트" }),
    ]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ project: 2 }));
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ status: "project", page: "2" });

    const projectNav = screen.getByRole("navigation", { name: "프로젝트별 분류됨" });
    expect(within(projectNav).getByRole("link", { name: "현재 프로젝트" })).toHaveAttribute("aria-current", "page");
    expect(within(projectNav).getByRole("link", { name: "다른 프로젝트" })).not.toHaveAttribute("aria-current");
  });

  it("nonadmin은 탭이 없고 project 상태만 조회하며 승인 폼도 없다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "member" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [], total: 0, hasMore: false });

    await renderPage({ status: "unclassified" });

    expect(mockedFetchMailPage).toHaveBeenCalledWith(PROJECT_ID, "project", 1, undefined);
    expect(mockedFetchMailCounts).not.toHaveBeenCalled();
    expect(screen.queryByRole("navigation", { name: "메일 분류 탭" })).not.toBeInTheDocument();
    expect(mockedGateway.listProjects).not.toHaveBeenCalled();
    expect(screen.queryByRole("navigation", { name: "프로젝트별 분류됨" })).not.toBeInTheDocument();
    expect(screen.getByText("이 프로젝트로 승인된 메일이 아직 없습니다.")).toBeInTheDocument();
  });

  it("카테고리 탭은 페이지를 1쪽으로 되돌린다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ status: "project", page: "3" });

    const tabs = screen.getByRole("navigation", { name: "메일 분류 탭" });
    const unclassifiedLink = within(tabs).getByRole("link", { name: (name) => name.startsWith("미분류") });
    expect(unclassifiedLink).toHaveAttribute("href", "?status=unclassified&page=1");
  });

  it("목록 밖이어도 승인된 현재 프로젝트 소스 메일이면 단건 조회로 보여준다(드라이브 출처 딥링크)", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "in-page", subject: "목록 안" })],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(
      mail({
        id: "outside-page",
        subject: "출처 메일",
        classification: "project",
        project_id: PROJECT_ID,
        can_review: false,
      }),
    );

    await renderPage({ status: "project", mail: "outside-page" });

    expect(mockedFetchMailById).toHaveBeenCalledWith("outside-page");
    expect(screen.getByRole("heading", { level: 2, name: "출처 메일" })).toBeInTheDocument();
  });

  it("목록에서 선택한 메일의 분류가 바뀌었어도 백엔드가 허용하면 보여준다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const pendingMail = mail({ id: "mail-pending", classification: "unclassified" });
    mockedFetchMailPage.mockResolvedValue({ messages: [pendingMail], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 1 }));
    // 백엔드에서 분류가 project로 변경됨
    mockedFetchMailById.mockResolvedValue(
      mail({
        ...pendingMail,
        classification: "project",
        project_id: PROJECT_ID,
      }),
    );

    await renderPage({ status: "unclassified", mail: "mail-pending" });

    expect(mockedFetchMailById).toHaveBeenCalledWith("mail-pending");
    expect(screen.getByRole("region", { name: "메일 상세" })).toHaveTextContent(pendingMail.subject);
    expect(screen.queryByText("이 메일을 볼 수 없습니다.")).not.toBeInTheDocument();
  });

  it("목록 밖 메일이 다른 프로젝트이거나 미승인이면 거부하고 목록의 다른 메일로 대체하지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "in-page", subject: "목록 안" })],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(
      mail({
        id: "outside-page",
        subject: "다른 프로젝트 메일 내용",
        classification: "project",
        project_id: "other-project",
      }),
    );

    await renderPage({ status: "project", mail: "outside-page" });

    expect(screen.queryByRole("heading", { level: 2, name: "목록 안" })).not.toBeInTheDocument();
    expect(screen.queryByText("다른 프로젝트 메일 내용")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "다른 프로젝트 메일 내용" })).not.toBeInTheDocument();
    expect(screen.getByText(/볼 수 없습니다/)).toBeInTheDocument();
  });

  it("목록 밖 메일 단건 조회가 실패(403/404)해도 목록의 다른 메일로 대체하지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "in-page", subject: "목록 안" })],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockRejectedValue(
      new ApiProblem({ type: "about:blank", title: "권한 없음", status: 403, code: "FORBIDDEN" }),
    );

    await renderPage({ status: "project", mail: "outside-page" });

    expect(screen.queryByRole("heading", { level: 2, name: "목록 안" })).not.toBeInTheDocument();
    expect(screen.getByText(/볼 수 없습니다/)).toBeInTheDocument();
  });

  it("linked_file_id가 첨부 목록에 없으면 출처를 사용할 수 없다고 표시하고 대체 메일을 보여주지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ id: "in-page", subject: "목록 안" })],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(
      mail({
        id: "outside-page",
        subject: "출처 메일",
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
      }),
    );

    await renderPage({ status: "project", mail: "outside-page", linked_file_id: "file-expected" });

    expect(screen.queryByRole("heading", { level: 2, name: "출처 메일" })).not.toBeInTheDocument();
    expect(screen.getByText(/원본.*사용할 수 없습니다/)).toBeInTheDocument();
  });

  it("서버가 필요 이상 자원을 직렬로 기다리지 않도록 목록/건수/프로젝트 선택지를 병렬로 조회한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    let listProjectsCalledBeforeListResolved = false;
    let resolveList: (value: Awaited<ReturnType<typeof fetchMailPage>>) => void = () => {};
    mockedFetchMailPage.mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );
    mockedGateway.listProjects.mockImplementation(async () => {
      listProjectsCalledBeforeListResolved = true;
      return [];
    });
    mockedFetchMailCounts.mockResolvedValue(counts());

    const pending = renderPage({});
    for (let i = 0; i < 20 && !listProjectsCalledBeforeListResolved; i += 1) {
      await Promise.resolve();
    }
    resolveList({ messages: [mail()], total: 1, hasMore: false });
    await pending;

    expect(listProjectsCalledBeforeListResolved).toBe(true);
  });

  it("페이지 번호와 전체 건수를 보여주고 이전/다음 링크는 조건에 맞을 때만 있다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 120, hasMore: true });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ page: "2" });

    expect(mockedFetchMailPage).toHaveBeenCalledWith(PROJECT_ID, "unclassified", 2, undefined);
    expect(screen.getByText(/2쪽 · 전체 120건/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "다음" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "이전" })).toBeInTheDocument();
  });

  it("403은 화면 전체를 갈아치우지 않고 금지 상태를 본문에 보여준다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "member" }));
    mockedFetchMailPage.mockRejectedValue(
      new ApiProblem({
        type: "about:blank",
        title: "권한 없음",
        status: 403,
        code: "FORBIDDEN",
      }),
    );

    await renderPage({});

    expect(screen.getByText("메일함")).toBeInTheDocument();
    expect(screen.getByText("이 화면을 볼 권한이 없습니다")).toBeInTheDocument();
  });

  it("승인된 메일은 지식화 버튼이 활성화된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const approved = mail({
      classification: "project",
      project_id: PROJECT_ID,
      approved_by: "admin@example.com",
      approved_at: "2026-09-09T10:00:00Z",
      can_review: false,
    });
    mockedFetchMailPage.mockResolvedValue({ messages: [approved], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(approved);

    await renderPage({ status: "project" });

    expect(screen.getByRole("button", { name: /지식화/ })).not.toBeDisabled();
  });

  it("미승인 메일은 지식화 버튼이 사유와 함께 비활성화된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const button = screen.getByRole("button", { name: /지식화/ });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("title", "승인된 메일만 지식화할 수 있습니다.");
  });

  it("연결된 첨부의 다운로드 링크는 linked_file_id 쿼리를 포함한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const withLinkedAttachment = mail({
      classification: "project",
      project_id: PROJECT_ID,
      approved_by: "admin@example.com",
      can_review: false,
      attachments: [
        {
          filename: "연결됨.pdf",
          content_type: "application/pdf",
          size_bytes: 10,
          part_index: 0,
          linked_file_id: "file-9",
        },
      ],
    });
    mockedFetchMailPage.mockResolvedValue({
      messages: [withLinkedAttachment],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(withLinkedAttachment);

    await renderPage({ status: "project" });

    expect(screen.getByRole("link", { name: "연결됨.pdf" })).toHaveAttribute(
      "href",
      "/api/mail/mail-1/attachments/0?linked_file_id=file-9",
    );
  });

  it("대기중 admin 미리보기 첨부는 linked_file_id 없이 링크한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const withUnlinkedAttachment = mail({
      classification: "unclassified",
      attachments: [
        {
          filename: "미승인.pdf",
          content_type: "application/pdf",
          size_bytes: 10,
          part_index: 0,
          linked_file_id: null,
        },
      ],
    });
    mockedFetchMailPage.mockResolvedValue({
      messages: [withUnlinkedAttachment],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(withUnlinkedAttachment);

    await renderPage({});

    expect(screen.getByRole("link", { name: "미승인.pdf" })).toHaveAttribute(
      "href",
      "/api/mail/mail-1/attachments/0",
    );
  });

  it("목록 미리보기(TOP200)는 첨부가 잘려 있을 수 있으므로 항상 단건 조회의 전체 첨부를 보여준다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const previewAttachment = {
      filename: "견적서.pdf",
      content_type: "application/pdf",
      size_bytes: 10,
      part_index: 0,
      linked_file_id: null,
    };
    const fullAttachment2 = {
      filename: "설계도.zip",
      content_type: "application/zip",
      size_bytes: 20,
      part_index: 1,
      linked_file_id: null,
    };
    mockedFetchMailPage.mockResolvedValue({
      messages: [mail({ attachments: [previewAttachment] })],
      total: 1,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(
      mail({ attachments: [previewAttachment, fullAttachment2] }),
    );

    await renderPage({});

    expect(mockedFetchMailById).toHaveBeenCalledWith("mail-1");
    expect(screen.getByRole("checkbox", { name: "설계도.zip" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "설계도.zip" }));
    expect(screen.getByRole("checkbox", { name: "설계도.zip" })).toBeChecked();
  });
});

describe("MailPage 건수 조회 실패 복원력", () => {
  it("건수 조회가 실패해도 목록/상세는 그대로 보여주고 건수만 확인 불가로 표시한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const approved = mail({
      classification: "project",
      project_id: PROJECT_ID,
      approved_by: "admin@example.com",
      approved_at: "2026-09-09T10:00:00Z",
      can_review: false,
    });
    mockedFetchMailPage.mockResolvedValue({ messages: [approved], total: 1, hasMore: false });
    mockedFetchMailCounts.mockRejectedValue(new Error("POP3 timeout"));
    mockedFetchMailById.mockResolvedValue(approved);

    await renderPage({ status: "project" });

    expect(screen.getByText("건수를 확인할 수 없습니다")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "제목" })).toBeInTheDocument();
    expect(screen.getByText(/승인 · admin@example.com/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /지식화/ })).not.toBeDisabled();
  });
});

describe("MailPage 추천 필터 URL 지속성", () => {
  it("메일 목록에서 메일을 선택할 때 suggested 필터를 URL에 유지한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    const firstMail = mail({ id: "mail-1", subject: "첫 번째 메일" });
    const secondMail = mail({ id: "mail-2", subject: "두 번째 메일" });
    mockedFetchMailPage.mockResolvedValue({
      messages: [firstMail, secondMail],
      total: 2,
      hasMore: false,
    });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 2 }));
    mockedFetchMailById.mockResolvedValue(secondMail);

    await renderPage({ status: "unclassified", page: "1", suggested: "yes" });

    const listLink = screen.getByRole("link", { name: /두 번째 메일/ });
    expect(listLink).toHaveAttribute(
      "href",
      expect.stringContaining("mail=mail-2"),
    );
    expect(listLink).toHaveAttribute(
      "href",
      expect.stringContaining("suggested=yes"),
    );
  });

  it("페이지 네비게이션(다음/이전)에서 suggested 필터를 유지한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 50, hasMore: true });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 50 }));
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ status: "unclassified", page: "2", suggested: "no" });

    const prevLink = screen.getByRole("link", { name: "이전" });
    const nextLink = screen.getByRole("link", { name: "다음" });

    expect(prevLink).toHaveAttribute(
      "href",
      "?status=unclassified&page=1&suggested=no",
    );
    expect(nextLink).toHaveAttribute(
      "href",
      "?status=unclassified&page=3&suggested=no",
    );
  });

  it("카테고리 탭 변경 시에는 suggested 필터를 리셋한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts({ unclassified: 5, project: 3, unrelated: 2 }));
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ status: "unclassified", page: "1", suggested: "yes" });

    const tabs = screen.getByRole("navigation", { name: "메일 분류 탭" });
    const projectTab = within(tabs).getByRole("link", { name: /프로젝트별 분류됨/ });

    expect(projectTab).toHaveAttribute("href", "?status=project&page=1");
    expect(projectTab).not.toHaveAttribute("href", expect.stringContaining("suggested"));
  });
});

describe("MailPage 경계잡힌 레이아웃", () => {
  it("메일 목록을 선택했을 때 데스크톱에서 리스트와 상세 패널이 함께 표시된다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const mailListSection = screen.getByRole("region", { name: "메일 목록" });
    expect(mailListSection).toBeInTheDocument();

    const detailSection = screen.getByRole("region", { name: "메일 상세" });
    expect(detailSection).toBeInTheDocument();
  });

  it("메일 목록 섹션은 데스크톱에서 overflow-y-auto와 min-h-0을 가진다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const mailListSection = screen.getByRole("region", { name: "메일 목록" });
    expect(mailListSection).toHaveClass("lg:overflow-y-auto");
    expect(mailListSection).toHaveClass("lg:min-h-0");
  });

  it("컨테이너는 데스크톱에서 flex-row, 높이 제한, overflow-hidden을 가진다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const mailListSection = screen.getByRole("region", { name: "메일 목록" });
    const container = mailListSection.parentElement;
    expect(container).toHaveClass("lg:flex-row");
    expect(container).toHaveClass("lg:overflow-hidden");
    expect(container).toHaveClass("lg:max-h-[calc(100vh-28rem)]");
  });

  it("모바일에서는 flex-col로 단일 열 레이아웃을 유지한다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const mailListSection = screen.getByRole("region", { name: "메일 목록" });
    const container = mailListSection.parentElement;
    expect(container).toHaveClass("flex");
    expect(container).toHaveClass("flex-col");
  });

  it("상세 섹션은 데스크톱에서 flex-1, overflow-y-auto, min-h-0을 가진다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 1, hasMore: false });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({});

    const detailSection = screen.getByRole("region", { name: "메일 상세" });
    const detailWrapper = detailSection.parentElement;
    expect(detailWrapper).toHaveClass("lg:flex-1");
    expect(detailWrapper).toHaveClass("lg:overflow-y-auto");
    expect(detailWrapper).toHaveClass("lg:min-h-0");
  });

  it("페이지네이션과 선택 상태는 변하지 않는다", async () => {
    mockedGateway.me.mockResolvedValue(user({ role: "admin" }));
    mockedGateway.listProjects.mockResolvedValue([]);
    mockedFetchMailPage.mockResolvedValue({ messages: [mail()], total: 120, hasMore: true });
    mockedFetchMailCounts.mockResolvedValue(counts());
    mockedFetchMailById.mockResolvedValue(mail());

    await renderPage({ page: "2" });

    expect(mockedFetchMailPage).toHaveBeenCalledWith(PROJECT_ID, "unclassified", 2, undefined);
    expect(screen.getByText(/2쪽 · 전체 120건/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "다음" })).toBeInTheDocument();
  });
});
