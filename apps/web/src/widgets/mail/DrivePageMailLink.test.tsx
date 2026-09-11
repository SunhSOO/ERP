import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DriveCategory, DriveFile } from "@lep/api-client";

vi.mock("@/src/shared/data/gateway", () => ({
  gateway: {
    getDrive: vi.fn(),
  },
}));

vi.mock("@/src/shared/data/mail-review", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/src/shared/data/mail-review")>();
  return {
    ...actual,
    fetchDriveFilesPage: vi.fn(),
  };
});

import { gateway } from "@/src/shared/data/gateway";
import { fetchDriveFilesPage } from "@/src/shared/data/mail-review";
import DrivePage from "@/app/(app)/projects/[projectId]/drive/page";

const PROJECT_ID = "11111111-1111-4111-8111-111111111111";

function category(overrides: Partial<DriveCategory> = {}): DriveCategory {
  return {
    category: "source",
    label: "소스",
    description: "설명",
    count: 1,
    read_only: false,
    warning: null,
    ...overrides,
  };
}

function file(overrides: Partial<DriveFile> = {}): DriveFile {
  return {
    id: "file-1",
    name: "견적서.pdf",
    category: "source",
    origin: "메일 원본 연결",
    size_bytes: 1000,
    modified: "2026-09-09",
    warning: null,
    source_mail_id: "mail-1",
    source_part_index: 0,
    source_kind: "mail_attachment",
    sha256: "abc123",
    ...overrides,
  };
}

const mockedGateway = vi.mocked(gateway);
const mockedFetchDriveFilesPage = vi.mocked(fetchDriveFilesPage);

async function renderPage(searchParams: Record<string, string> = {}) {
  const ui = await DrivePage({
    params: Promise.resolve({ projectId: PROJECT_ID }),
    searchParams: Promise.resolve(searchParams),
  });
  render(ui);
}

beforeEach(() => {
  mockedGateway.getDrive.mockReset();
  mockedFetchDriveFilesPage.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("DrivePage 메일 원본 연결 표시", () => {
  it("메일 첨부에서 온 파일은 출처 메일/다운로드 링크를 보여준다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category()]);
    mockedFetchDriveFilesPage.mockResolvedValue({ files: [file()], total: 1, hasMore: false });

    await renderPage();

    expect(screen.getByRole("link", { name: "출처 메일 보기" })).toHaveAttribute(
      "href",
      `/projects/${PROJECT_ID}/mail?status=project&mail=mail-1&linked_file_id=file-1`,
    );
    expect(screen.getByRole("link", { name: "다운로드" })).toHaveAttribute(
      "href",
      "/api/mail/mail-1/attachments/0?linked_file_id=file-1",
    );
  });

  it("출처 메일 ID가 없으면 링크를 만들지 않고 확인 불가로 표시한다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category()]);
    mockedFetchDriveFilesPage.mockResolvedValue({
      files: [file({ source_mail_id: null, source_part_index: null })],
      total: 1,
      hasMore: false,
    });

    await renderPage();

    expect(screen.queryByRole("link", { name: "출처 메일 보기" })).not.toBeInTheDocument();
    expect(screen.getByText("출처 메일을 확인할 수 없습니다")).toBeInTheDocument();
  });

  it("일반 파일은 메일 링크를 만들지 않는다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category()]);
    mockedFetchDriveFilesPage.mockResolvedValue({
      files: [
        file({
          id: "file-2",
          name: "일반파일.txt",
          origin: "직접 업로드",
          source_mail_id: null,
          source_part_index: null,
          source_kind: null,
        }),
      ],
      total: 1,
      hasMore: false,
    });

    await renderPage();

    const row = screen.getByText("일반파일.txt").closest("tr") as HTMLElement;
    expect(within(row).queryByRole("link", { name: "출처 메일 보기" })).not.toBeInTheDocument();
    expect(within(row).queryByRole("link", { name: "다운로드" })).not.toBeInTheDocument();
    expect(within(row).queryByText("출처 메일을 확인할 수 없습니다")).not.toBeInTheDocument();
  });
});

describe("DrivePage 페이지네이션", () => {
  it("category/offset 쿼리를 정제해서 조회 헬퍼에 넘긴다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category({ category: "source" })]);
    mockedFetchDriveFilesPage.mockResolvedValue({ files: [file()], total: 1, hasMore: false });

    await renderPage({ category: "source", offset: "-5" });

    expect(mockedFetchDriveFilesPage).toHaveBeenCalledWith(PROJECT_ID, "source", 0);
  });

  it("hasMore이면 다음 링크가 category와 offset+50을 유지한다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category({ category: "source" })]);
    mockedFetchDriveFilesPage.mockResolvedValue({
      files: [file()],
      total: 200,
      hasMore: true,
    });

    await renderPage({ category: "source", offset: "50" });

    const next = screen.getByRole("link", { name: "다음" });
    const url = new URL(next.getAttribute("href") ?? "", "http://localhost");
    expect(url.searchParams.get("category")).toBe("source");
    expect(url.searchParams.get("offset")).toBe("100");
  });

  it("offset이 0보다 크면 이전 링크가 category를 유지한 채 offset을 되돌린다", async () => {
    mockedGateway.getDrive.mockResolvedValue([category({ category: "source" })]);
    mockedFetchDriveFilesPage.mockResolvedValue({
      files: [file()],
      total: 200,
      hasMore: true,
    });

    await renderPage({ category: "source", offset: "50" });

    const prev = screen.getByRole("link", { name: "이전" });
    const url = new URL(prev.getAttribute("href") ?? "", "http://localhost");
    expect(url.searchParams.get("category")).toBe("source");
    expect(url.searchParams.get("offset")).toBe("0");
  });

  it("분류를 바꾸는 링크는 offset을 되돌린다(0)", async () => {
    mockedGateway.getDrive.mockResolvedValue([
      category({ category: "source" }),
      category({ category: "original", label: "원본" }),
    ]);
    mockedFetchDriveFilesPage.mockResolvedValue({ files: [file()], total: 1, hasMore: false });

    await renderPage({ category: "source", offset: "50" });

    const categoryLink = screen.getByRole("link", { name: /원본/ });
    const url = new URL(categoryLink.getAttribute("href") ?? "", "http://localhost");
    expect(url.searchParams.get("category")).toBe("original");
    expect(url.searchParams.has("offset")).toBe(false);
  });
});
