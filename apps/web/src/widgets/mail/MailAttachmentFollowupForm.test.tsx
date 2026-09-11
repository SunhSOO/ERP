import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MailMessage } from "@lep/api-client";

vi.mock("@/src/shared/data/mail-review-actions", () => ({
  approveMailAttachmentsAction: vi.fn(),
}));

import { approveMailAttachmentsAction } from "@/src/shared/data/mail-review-actions";
import type { MailActionResult } from "@/src/shared/data/mail-review-actions";
import { MailAttachmentFollowupForm } from "./MailAttachmentFollowupForm";

const mockedApprove = vi.mocked(approveMailAttachmentsAction);

function message(overrides: Partial<MailMessage> = {}): MailMessage {
  return {
    id: "mail-1",
    sender_name: "발신자",
    sender_org: "조직",
    received_at: "2026-09-09T09:00:00Z",
    subject: "제목",
    body: "본문",
    classification: "project",
    project_id: "proj-1",
    suggested_project_id: null,
    intent: null,
    confidence: null,
    milestone_code: null,
    note_id: null,
    handled: true,
    version: 5,
    approved_by: "admin@example.com",
    approved_at: "2026-09-09T10:00:00Z",
    can_review: true,
    attachments: [
      {
        filename: "이미승인.pdf",
        content_type: "application/pdf",
        size_bytes: 100,
        part_index: 0,
        linked_file_id: "file-1",
      },
      {
        filename: "새첨부.zip",
        content_type: "application/zip",
        size_bytes: 200,
        part_index: 1,
        linked_file_id: null,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  mockedApprove.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("MailAttachmentFollowupForm", () => {
  it("이미 연결된 첨부는 선택지에 없고 새 첨부만 고를 수 있다", () => {
    render(<MailAttachmentFollowupForm message={message()} projectId="proj-1" />);

    expect(screen.queryByLabelText("이미승인.pdf")).not.toBeInTheDocument();
    expect(screen.getByLabelText("새첨부.zip")).toBeInTheDocument();
    expect(screen.getByText(/이미 연결된 첨부: 이미승인\.pdf/)).toBeInTheDocument();
  });

  it("아무 것도 선택하지 않으면 연결 버튼이 비활성화된다", () => {
    render(<MailAttachmentFollowupForm message={message()} projectId="proj-1" />);
    expect(screen.getByRole("button", { name: "첨부 연결" })).toBeDisabled();
  });

  it("새 첨부를 선택·확인하면 대상 프로젝트가 고정된 채 정확한 payload로 연결한다", async () => {
    mockedApprove.mockResolvedValue({
      ok: true,
      status: "ok",
      message: "첨부 1개를 새로 연결했습니다.",
    });

    render(<MailAttachmentFollowupForm message={message()} projectId="proj-1" />);

    fireEvent.click(screen.getByLabelText("새첨부.zip"));
    fireEvent.change(screen.getByLabelText("새첨부.zip 분류"), { target: { value: "deliverable" } });
    fireEvent.click(screen.getByRole("button", { name: "연결 내용 확인" }));

    const summary = screen.getByText(/새로 연결할 첨부:/).closest("div") as HTMLElement;
    expect(within(summary).getByText(/새첨부\.zip \(산출물\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("위 내용대로 연결합니다"));
    fireEvent.click(screen.getByRole("button", { name: "첨부 연결" }));

    await screen.findByText("첨부 1개를 새로 연결했습니다.");

    expect(mockedApprove).toHaveBeenCalledTimes(1);
    const [projectId, messageId, expectedVersion, attachments, key] = mockedApprove.mock.calls[0];
    expect(projectId).toBe("proj-1");
    expect(messageId).toBe("mail-1");
    expect(expectedVersion).toBe(5);
    expect(attachments).toEqual([{ part_index: 1, category: "deliverable" }]);
    expect(typeof key).toBe("string");
  });

  it("전송 중에는 첨부 선택/확인 체크박스를 편집할 수 없다", async () => {
    let resolveApprove: (value: MailActionResult) => void = () => {};
    mockedApprove.mockReturnValue(
      new Promise((resolve) => {
        resolveApprove = resolve;
      }),
    );

    render(<MailAttachmentFollowupForm message={message()} projectId="proj-1" />);

    fireEvent.click(screen.getByLabelText("새첨부.zip"));
    fireEvent.click(screen.getByRole("button", { name: "연결 내용 확인" }));
    fireEvent.click(screen.getByLabelText("위 내용대로 연결합니다"));
    fireEvent.click(screen.getByRole("button", { name: "첨부 연결" }));

    expect(screen.getByLabelText("새첨부.zip")).toBeDisabled();
    expect(screen.getByLabelText("위 내용대로 연결합니다")).toBeDisabled();

    resolveApprove({ ok: true, status: "ok", message: "첨부 1개를 새로 연결했습니다." });
    await screen.findByText("첨부 1개를 새로 연결했습니다.");
  });

  it("classification이 project가 아니거나 새로 연결할 첨부가 없으면 렌더하지 않는다", () => {
    const { container: unclassifiedContainer } = render(
      <MailAttachmentFollowupForm
        message={message({ classification: "unclassified" })}
        projectId="proj-1"
      />,
    );
    expect(unclassifiedContainer).toBeEmptyDOMElement();
    cleanup();

    const allLinked = message({
      attachments: [
        {
          filename: "이미승인.pdf",
          content_type: "application/pdf",
          size_bytes: 100,
          part_index: 0,
          linked_file_id: "file-1",
        },
      ],
    });
    const { container: noNewContainer } = render(
      <MailAttachmentFollowupForm message={allLinked} projectId="proj-1" />,
    );
    expect(noNewContainer).toBeEmptyDOMElement();
  });
});
