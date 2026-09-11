import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { DriveFile } from "@lep/api-client";
import { DriveMailLink } from "./DriveMailLink";

function file(overrides: Partial<DriveFile> = {}): DriveFile {
  return {
    id: "file-1",
    name: "견적서.pdf",
    category: "original",
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

afterEach(() => {
  cleanup();
});

describe("DriveMailLink", () => {
  it("메일 첨부 출처면 출처 메일 링크와 다운로드 링크를 만든다", () => {
    render(<DriveMailLink file={file()} projectId="proj-1" />);

    const mailLink = screen.getByRole("link", { name: "출처 메일 보기" });
    expect(mailLink).toHaveAttribute(
      "href",
      "/projects/proj-1/mail?status=project&mail=mail-1&linked_file_id=file-1",
    );

    const downloadLink = screen.getByRole("link", { name: "다운로드" });
    expect(downloadLink).toHaveAttribute(
      "href",
      "/api/mail/mail-1/attachments/0?linked_file_id=file-1",
    );
  });

  it("projectId를 encodeURIComponent로 감싼다", () => {
    render(<DriveMailLink file={file()} projectId="proj with space" />);

    expect(screen.getByRole("link", { name: "출처 메일 보기" })).toHaveAttribute(
      "href",
      "/projects/proj%20with%20space/mail?status=project&mail=mail-1&linked_file_id=file-1",
    );
  });

  it("delimiter UIDL은 다운로드 경로에서 base64url로 운반한다", () => {
    render(<DriveMailLink file={file({ source_mail_id: "uid/with?delim#hash" })} projectId="proj-1" />);
    expect(screen.getByRole("link", { name: "다운로드" })).toHaveAttribute(
      "href",
      "/api/mail/dWlkL3dpdGg_ZGVsaW0jaGFzaA/attachments/0?id_encoding=base64url&linked_file_id=file-1",
    );
  });

  it("출처 정보가 없으면 가짜 링크를 만들지 않는다", () => {
    render(<DriveMailLink file={file({ source_mail_id: null })} projectId="proj-1" />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("출처 메일을 확인할 수 없습니다")).toBeInTheDocument();
  });

  it("메일 첨부 출처가 아니면 아무것도 렌더하지 않는다", () => {
    const { container } = render(<DriveMailLink file={file({ source_kind: null })} projectId="proj-1" />);
    expect(container).toBeEmptyDOMElement();
  });
});
