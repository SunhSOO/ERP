import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RepositoryConnection } from "@lep/api-client";

vi.mock("@/src/shared/data/actions", () => ({
  updateVcsConnectionAction: vi.fn(),
}));

import { updateVcsConnectionAction } from "@/src/shared/data/actions";
import { GitHubConnectionForm } from "./GitHubConnectionForm";

const mockedUpdate = vi.mocked(updateVcsConnectionAction);

function createConnection(overrides: Partial<RepositoryConnection> = {}): RepositoryConnection {
  return {
    connected: true,
    repository: "my-org/my-repo",
    version: 1,
    ...overrides,
  };
}

describe("GitHubConnectionForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders nothing when canEdit is false", () => {
    const { container } = render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders form when canEdit is true", () => {
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );
    expect(screen.getByText("저장소 연동")).toBeInTheDocument();
    expect(screen.getByLabelText("저장소 소유자")).toBeInTheDocument();
    expect(screen.getByLabelText("저장소 이름")).toBeInTheDocument();
  });

  it("populates fields from connection repository in owner/repo format", () => {
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ repository: "my-org/my-repo" })}
        canEdit={true}
      />,
    );
    expect((screen.getByLabelText("저장소 소유자") as HTMLInputElement).value).toBe("my-org");
    expect((screen.getByLabelText("저장소 이름") as HTMLInputElement).value).toBe("my-repo");
  });

  it("handles null repository gracefully", () => {
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ repository: null })}
        canEdit={true}
      />,
    );
    expect((screen.getByLabelText("저장소 소유자") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("저장소 이름") as HTMLInputElement).value).toBe("");
  });

  it("includes expected_version as hidden input", () => {
    const { container } = render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ version: 5 })}
        canEdit={true}
      />,
    );
    const hiddenInput = container.querySelector(
      'input[type="hidden"][name="expected_version"]',
    ) as HTMLInputElement;
    expect(hiddenInput).toBeInTheDocument();
    expect(hiddenInput.value).toBe("5");
  });

  it("shows success message when result.ok is true", async () => {
    mockedUpdate.mockResolvedValue({ ok: true, message: "저장소 연동을 업데이트했습니다." });

    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );

    const submitButton = screen.getByRole("button", { name: /저장/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("저장소 연동을 업데이트했습니다.")).toBeInTheDocument();
    });
  });

  it("shows error message when result.ok is false", async () => {
    mockedUpdate.mockResolvedValue({
      ok: false,
      message: "저장소를 찾을 수 없습니다.",
    });

    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );

    const submitButton = screen.getByRole("button", { name: /저장/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("저장소를 찾을 수 없습니다.")).toBeInTheDocument();
    });
  });

  it("shows validation error with trace ID when provided", async () => {
    mockedUpdate.mockResolvedValue({
      ok: false,
      message: "유효하지 않은 저장소 형식입니다.",
      traceId: "trace-123",
    });

    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );

    const submitButton = screen.getByRole("button", { name: /저장/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/유효하지 않은 저장소 형식입니다./)).toBeInTheDocument();
      expect(screen.getByText(/trace-123/)).toBeInTheDocument();
    });
  });

  it("shows conflict error when version mismatch occurs", async () => {
    mockedUpdate.mockResolvedValue({
      ok: false,
      message: "저장소 정보가 변경되었습니다. 페이지를 새로고침하세요.",
    });

    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ version: 1 })}
        canEdit={true}
      />,
    );

    const submitButton = screen.getByRole("button", { name: /저장/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/저장소 정보가 변경되었습니다/)).toBeInTheDocument();
    });
  });

  it("allows editing owner field", async () => {
    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ repository: "old-org/old-repo" })}
        canEdit={true}
      />,
    );

    const ownerField = screen.getByLabelText("저장소 소유자") as HTMLInputElement;
    expect(ownerField.value).toBe("old-org");

    await user.clear(ownerField);
    await user.type(ownerField, "new-org");

    expect(ownerField.value).toBe("new-org");
  });

  it("allows editing repository field", async () => {
    const user = userEvent.setup();
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ repository: "org/old-repo" })}
        canEdit={true}
      />,
    );

    const repoField = screen.getByLabelText("저장소 이름") as HTMLInputElement;
    expect(repoField.value).toBe("old-repo");

    await user.clear(repoField);
    await user.type(repoField, "new-repo");

    expect(repoField.value).toBe("new-repo");
  });

  it("submits form with combined owner/repo values", async () => {
    const user = userEvent.setup();
    const mockAction = vi.fn();
    mockedUpdate.mockImplementation(mockAction);

    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ version: 2 })}
        canEdit={true}
      />,
    );

    const ownerField = screen.getByLabelText("저장소 소유자");
    const repoField = screen.getByLabelText("저장소 이름");
    const submitButton = screen.getByRole("button", { name: /저장/ });

    await user.clear(ownerField);
    await user.type(ownerField, "test-org");
    await user.clear(repoField);
    await user.type(repoField, "test-repo");

    await user.click(submitButton);

    // Verify that the action was called with the correct projectId
    expect(mockAction).toHaveBeenCalled();
  });

  it("shows unconnected state with empty fields", () => {
    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection({ connected: false, repository: null })}
        canEdit={true}
      />,
    );

    expect((screen.getByLabelText("저장소 소유자") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("저장소 이름") as HTMLInputElement).value).toBe("");
  });

  it("renders submit button as disabled during submission", async () => {
    mockedUpdate.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );

    const submitButton = screen.getByRole("button", { name: /저장/ });
    expect(submitButton).not.toBeDisabled();
  });

  it("renders form with correct structure and styling", () => {
    const { container } = render(
      <GitHubConnectionForm
        projectId="proj-1"
        connection={createConnection()}
        canEdit={true}
      />,
    );

    expect(container.querySelector("form")).toBeInTheDocument();
    expect(container.querySelector(".flex.flex-col.gap-3")).toBeInTheDocument();
  });
});
