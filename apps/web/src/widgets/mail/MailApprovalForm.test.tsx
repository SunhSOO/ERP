import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MailMessage } from "@lep/api-client";

vi.mock("@/src/shared/data/mail-review-actions", () => ({
  approveMailAction: vi.fn(),
}));

import { approveMailAction } from "@/src/shared/data/mail-review-actions";
import type { MailActionResult } from "@/src/shared/data/mail-review-actions";
import { MailApprovalForm } from "./MailApprovalForm";

const mockedApprove = vi.mocked(approveMailAction);

function message(overrides: Partial<MailMessage> = {}): MailMessage {
  return {
    id: "mail-1",
    sender_name: "발신자",
    sender_org: "조직",
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
    version: 3,
    approved_by: null,
    approved_at: null,
    can_review: true,
    attachments: [
      {
        filename: "견적서.pdf",
        content_type: "application/pdf",
        size_bytes: 1000,
        part_index: 0,
        linked_file_id: null,
      },
      {
        filename: "설계도.zip",
        content_type: "application/zip",
        size_bytes: 2000,
        part_index: 1,
        linked_file_id: null,
      },
    ],
    suggestions: [],
    ...overrides,
  };
}

const projects = [
  { id: "proj-1", name: "다온 스마트팩토리" },
  { id: "proj-2", name: "라온 물류센터" },
];

beforeEach(() => {
  mockedApprove.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("MailApprovalForm", () => {
  it("대상 프로젝트는 비어 있고 첨부는 모두 미선택 상태로 시작한다", () => {
    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    expect(screen.getByLabelText("대상 프로젝트")).toHaveValue("");
    for (const checkbox of screen.getAllByRole("checkbox")) {
      expect(checkbox).not.toBeChecked();
    }
    expect(screen.getByRole("button", { name: "메일 승인" })).toBeDisabled();
  });

  it("프로젝트만 골라도 요약 확인·동의 전에는 최종 승인이 막힌다", () => {
    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-2" } });
    expect(screen.getByRole("button", { name: "메일 승인" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));
    expect(screen.getByRole("button", { name: "메일 승인" })).toBeDisabled();
  });

  it("프로젝트 선택 후 첨부와 분류를 고르고 요약·확인을 거치면 정확한 payload로 승인한다", async () => {
    mockedApprove.mockResolvedValue({
      ok: true,
      status: "ok",
      message: "메일을 승인하고 첨부 1개를 연결했습니다.",
    });

    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-2" } });
    fireEvent.click(screen.getByLabelText("견적서.pdf"));
    fireEvent.change(screen.getByLabelText("견적서.pdf 분류"), { target: { value: "report" } });

    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));
    const summary = screen.getByText(/연결할 첨부:/).closest("div") as HTMLElement;
    expect(within(summary).getByText(/견적서\.pdf \(보고서\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("위 내용대로 승인합니다"));
    const submit = screen.getByRole("button", { name: "메일 승인" });
    expect(submit).not.toBeDisabled();

    fireEvent.click(submit);
    await screen.findByText("메일을 승인하고 첨부 1개를 연결했습니다.");

    expect(mockedApprove).toHaveBeenCalledTimes(1);
    const [reviewProjectId, messageId, targetProjectId, expectedVersion, attachments, key] =
      mockedApprove.mock.calls[0];
    expect(reviewProjectId).toBe("proj-1");
    expect(messageId).toBe("mail-1");
    expect(targetProjectId).toBe("proj-2");
    expect(expectedVersion).toBe(3);
    expect(attachments).toEqual([{ part_index: 0, category: "report" }]);
    expect(typeof key).toBe("string");
    expect(key.length).toBeGreaterThan(0);
  });

  it("첨부 없이도 메일만 승인이 유효한 선택이다", () => {
    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-1" } });
    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));

    expect(screen.getByText(/없음 \(메일만 승인\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("위 내용대로 승인합니다"));
    expect(screen.getByRole("button", { name: "메일 승인" })).not.toBeDisabled();
  });

  it("실패 후 같은(변경 없는) 입력으로 재시도하면 key가 유지되고, 입력을 바꾸면 새 key를 쓴다", async () => {
    mockedApprove.mockResolvedValueOnce({
      ok: false,
      status: "error",
      message: "백엔드에 연결하지 못했습니다.",
    });

    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-2" } });
    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));
    fireEvent.click(screen.getByLabelText("위 내용대로 승인합니다"));
    fireEvent.click(screen.getByRole("button", { name: "메일 승인" }));

    await screen.findByText("백엔드에 연결하지 못했습니다.");
    const firstKey = mockedApprove.mock.calls[0][5];

    // 전송 실패 후에도 폼은 그대로다(확인 체크박스가 이미 체크된 상태). 같은 입력으로
    // 재시도할 때는 체크박스를 다시 누르지 않는다 — 이미 체크된 걸 다시 누르면
    // 오히려 해제되어 버튼이 막힌다.
    expect(screen.getByLabelText("위 내용대로 승인합니다")).toBeChecked();
    mockedApprove.mockResolvedValueOnce({ ok: true, status: "ok", message: "메일만 승인했습니다." });
    fireEvent.click(screen.getByRole("button", { name: "메일 승인" }));

    await screen.findByText("메일만 승인했습니다.");
    const secondKey = mockedApprove.mock.calls[1][5];
    expect(secondKey).toBe(firstKey);

    mockedApprove.mockResolvedValueOnce({ ok: true, status: "ok", message: "메일만 승인했습니다." });
    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-1" } });
    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));
    fireEvent.click(screen.getByLabelText("위 내용대로 승인합니다"));
    fireEvent.click(screen.getByRole("button", { name: "메일 승인" }));

    await screen.findByText("메일만 승인했습니다.");
    const thirdKey = mockedApprove.mock.calls[2][5];
    expect(thirdKey).not.toBe(secondKey);
  });

  it("전송 중에는 대상 프로젝트/첨부 선택/확인 체크박스를 편집할 수 없다", async () => {
    let resolveApprove: (value: MailActionResult) => void = () => {};
    mockedApprove.mockReturnValue(
      new Promise((resolve) => {
        resolveApprove = resolve;
      }),
    );

    render(<MailApprovalForm message={message()} projects={projects} reviewProjectId="proj-1" />);

    fireEvent.change(screen.getByLabelText("대상 프로젝트"), { target: { value: "proj-2" } });
    fireEvent.click(screen.getByRole("button", { name: "승인 내용 확인" }));
    fireEvent.click(screen.getByLabelText("위 내용대로 승인합니다"));
    fireEvent.click(screen.getByRole("button", { name: "메일 승인" }));

    expect(screen.getByLabelText("대상 프로젝트")).toBeDisabled();
    expect(screen.getByLabelText("견적서.pdf")).toBeDisabled();
    expect(screen.getByLabelText("위 내용대로 승인합니다")).toBeDisabled();

    resolveApprove({ ok: true, status: "ok", message: "메일만 승인했습니다." });
    await screen.findByText("메일만 승인했습니다.");
  });

  it("can_review가 거짓이거나 이미 분류된 메일이면 렌더하지 않는다", () => {
    const { container: notReviewable } = render(
      <MailApprovalForm
        message={message({ can_review: false })}
        projects={projects}
        reviewProjectId="proj-1"
      />,
    );
    expect(notReviewable).toBeEmptyDOMElement();
    cleanup();

    const { container: alreadyClassified } = render(
      <MailApprovalForm
        message={message({ classification: "project" })}
        projects={projects}
        reviewProjectId="proj-1"
      />,
    );
    expect(alreadyClassified).toBeEmptyDOMElement();
  });

  it("상위 추천 프로젝트를 시각적으로 표시하고 초기값으로 선택한다", () => {
    render(
      <MailApprovalForm
        message={message({
          suggestions: [
            {
              project_id: "proj-2",
              project_name: "라온 물류센터",
              confidence: "high",
              reasons: ["관련 키워드 매칭"],
            },
          ],
        })}
        projects={projects}
        reviewProjectId="proj-1"
      />,
    );

    expect(screen.getByText(/추천 프로젝트: 라온 물류센터/)).toBeInTheDocument();
    expect(screen.getByLabelText("대상 프로젝트")).toHaveValue("proj-2");
  });

  it("상위 추천을 초기 선택했지만 사용자가 다른 프로젝트로 변경할 수 있다", () => {
    render(
      <MailApprovalForm
        message={message({
          suggestions: [
            {
              project_id: "proj-2",
              project_name: "라온 물류센터",
              confidence: "high",
              reasons: ["관련 키워드 매칭"],
            },
          ],
        })}
        projects={projects}
        reviewProjectId="proj-1"
      />,
    );

    const projectSelect = screen.getByLabelText("대상 프로젝트");
    expect(projectSelect).toHaveValue("proj-2");

    fireEvent.change(projectSelect, { target: { value: "proj-1" } });
    expect(projectSelect).toHaveValue("proj-1");
  });

  it("상위 추천이 다른 프로젝트 이름일 때도 초기값으로 선택되고 userEvent로 변경할 수 있다", () => {
    render(
      <MailApprovalForm
        message={message({
          suggestions: [
            {
              project_id: "proj-2",
              project_name: "다른 프로젝트",
              confidence: "high",
              reasons: ["프로젝트 코드: PRJ-2"],
            },
          ],
        })}
        projects={projects}
        reviewProjectId="proj-1"
      />,
    );

    const projectSelect = screen.getByLabelText("대상 프로젝트");
    expect(projectSelect).toHaveValue("proj-2");

    fireEvent.change(projectSelect, { target: { value: "proj-1" } });
    expect(projectSelect).toHaveValue("proj-1");
  });
});
