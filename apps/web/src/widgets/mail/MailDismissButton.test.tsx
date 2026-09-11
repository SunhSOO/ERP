import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/src/shared/data/mail-review-actions", () => ({
  dismissMailAction: vi.fn(),
}));

import { dismissMailAction } from "@/src/shared/data/mail-review-actions";
import { MailDismissButton } from "./MailDismissButton";

const mockedDismiss = vi.mocked(dismissMailAction);

beforeEach(() => {
  mockedDismiss.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("MailDismissButton", () => {
  it("확인 체크 전에는 제외 버튼이 비활성화된다", () => {
    render(<MailDismissButton messageId="mail-1" reviewProjectId="proj-1" version={4} />);
    expect(screen.getByRole("button", { name: /프로젝트 무관으로 제외/ })).toBeDisabled();
  });

  it("확인 체크 후 제외하면 expected_version과 idempotency key를 그대로 넘긴다", async () => {
    mockedDismiss.mockResolvedValue({
      ok: true,
      status: "ok",
      message: "메일을 프로젝트 무관으로 제외했습니다.",
    });

    render(<MailDismissButton messageId="mail-1" reviewProjectId="proj-1" version={4} />);
    fireEvent.click(screen.getByLabelText("이 메일이 프로젝트와 무관함을 확인합니다"));
    fireEvent.click(screen.getByRole("button", { name: /프로젝트 무관으로 제외/ }));

    await screen.findByText("메일을 프로젝트 무관으로 제외했습니다.");

    expect(mockedDismiss).toHaveBeenCalledTimes(1);
    const [reviewProjectId, messageId, expectedVersion, key] = mockedDismiss.mock.calls[0];
    expect(reviewProjectId).toBe("proj-1");
    expect(messageId).toBe("mail-1");
    expect(expectedVersion).toBe(4);
    expect(typeof key).toBe("string");
  });

  it("전송 중에는 확인 체크박스를 편집할 수 없다", async () => {
    let resolveDismiss: (value: { ok: boolean; status: "ok"; message: string }) => void = () => {};
    mockedDismiss.mockReturnValue(
      new Promise((resolve) => {
        resolveDismiss = resolve;
      }),
    );

    render(<MailDismissButton messageId="mail-1" reviewProjectId="proj-1" version={4} />);
    fireEvent.click(screen.getByLabelText("이 메일이 프로젝트와 무관함을 확인합니다"));
    fireEvent.click(screen.getByRole("button", { name: /프로젝트 무관으로 제외/ }));

    expect(screen.getByLabelText("이 메일이 프로젝트와 무관함을 확인합니다")).toBeDisabled();

    resolveDismiss({ ok: true, status: "ok", message: "메일을 프로젝트 무관으로 제외했습니다." });
    await screen.findByText("메일을 프로젝트 무관으로 제외했습니다.");
  });

  it("409 충돌은 성공으로 표시하지 않는다", async () => {
    mockedDismiss.mockResolvedValue({ ok: false, status: "conflict", message: "이미 처리되었습니다." });

    render(<MailDismissButton messageId="mail-1" reviewProjectId="proj-1" version={4} />);
    fireEvent.click(screen.getByLabelText("이 메일이 프로젝트와 무관함을 확인합니다"));
    fireEvent.click(screen.getByRole("button", { name: /프로젝트 무관으로 제외/ }));

    await screen.findByText(/충돌: 이미 처리되었습니다\./);
  });
});
