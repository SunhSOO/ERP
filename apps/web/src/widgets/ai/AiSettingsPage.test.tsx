import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { LlmServer, ProjectModel } from "@lep/api-client";

// gateway는 HTTP를 통해 백엔드에 접근하므로(apps/web/src/shared/data/gateway.ts) 여기서는
// 전체를 모의해 네트워크 호출 없이 화면의 렌더링 규칙만 검증한다.
vi.mock("@/src/shared/data/gateway", () => ({
  gateway: {
    getServer: vi.fn(),
    listModels: vi.fn(),
    listCredentials: vi.fn(),
  },
}));

import { gateway } from "@/src/shared/data/gateway";
import AiSettingsPage from "@/app/(app)/projects/[projectId]/settings/ai/page";

const PROJECT_ID = "11111111-1111-4111-8111-111111111111";

function server(overrides: Partial<LlmServer> = {}): LlmServer {
  return {
    name: "테스트 공통 서버",
    network_note: "테스트 네트워크 참고 문구",
    status: "connected",
    detail: "테스트 상세 설명",
    gpu_usage_percent: null,
    active_model_count: null,
    available_model_names: [],
    running_model_names: [],
    project_count: 0,
    ...overrides,
  };
}

function projectModel(overrides: Partial<ProjectModel> = {}): ProjectModel {
  return {
    project_id: PROJECT_ID,
    project_name: "테스트 프로젝트",
    model: null,
    state: "stopped",
    priority: null,
    gpu_share_percent: null,
    ...overrides,
  };
}

async function renderPage() {
  const ui = await AiSettingsPage({ params: Promise.resolve({ projectId: PROJECT_ID }) });
  render(ui);
}

const mockedGateway = vi.mocked(gateway);

beforeEach(() => {
  mockedGateway.getServer.mockReset();
  mockedGateway.listModels.mockReset();
  mockedGateway.listCredentials.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("AiSettingsPage", () => {
  it("연결됨 상태에서 설치된 모델과 실행 중인 모델 부분집합을 각각 보여준다", async () => {
    mockedGateway.getServer.mockResolvedValue(
      server({
        status: "connected",
        available_model_names: ["synthetic-model-a", "synthetic-model-b"],
        running_model_names: ["synthetic-model-a"],
        gpu_usage_percent: null,
        active_model_count: 1,
      }),
    );
    mockedGateway.listModels.mockResolvedValue([]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    expect(
      screen.getByText("추론 서버의 연결 상태와 설치·적재된 모델을 확인합니다"),
    ).toBeInTheDocument();

    const installedHeading = screen.getByRole("heading", { name: "설치된 모델" });
    const installedList = installedHeading.nextElementSibling as HTMLElement;
    expect(installedList).not.toBeNull();
    expect(installedList.textContent).toContain("synthetic-model-a");
    expect(installedList.textContent).toContain("synthetic-model-b");

    const runningHeading = screen.getByRole("heading", { name: "실행 중(적재됨)인 모델" });
    const runningList = runningHeading.nextElementSibling as HTMLElement;
    expect(runningList.textContent).toContain("synthetic-model-a");
    expect(runningList.textContent).not.toContain("synthetic-model-b");

    expect(screen.getByText("미측정")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("연결됨 상태에서 빈 목록은 실패가 아닌 '없음'으로 표시한다", async () => {
    mockedGateway.getServer.mockResolvedValue(
      server({
        status: "connected",
        available_model_names: [],
        running_model_names: [],
        active_model_count: 0,
      }),
    );
    mockedGateway.listModels.mockResolvedValue([]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    expect(screen.getByText("설치된 모델이 없습니다.")).toBeInTheDocument();
    expect(screen.getByText("적재된 모델이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByText("확인할 수 없습니다.")).not.toBeInTheDocument();

    const activeCountValue = screen.getByText("적재된 모델 수").nextElementSibling as HTMLElement;
    expect(activeCountValue.textContent).toBe("0");

    const gpuValue = screen.getByText("GPU 사용률").nextElementSibling as HTMLElement;
    expect(gpuValue.textContent).toBe("미측정");
  });

  it("일부 확인 불가(degraded) 상태에서는 설치 목록은 그대로 보여주되 적재 수는 미측정으로 남긴다", async () => {
    mockedGateway.getServer.mockResolvedValue(
      server({
        status: "degraded",
        available_model_names: ["synthetic-model-known"],
        running_model_names: [],
        active_model_count: null,
      }),
    );
    mockedGateway.listModels.mockResolvedValue([]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    expect(screen.getByText("synthetic-model-known")).toBeInTheDocument();

    const runningHeading = screen.getByRole("heading", { name: "실행 중(적재됨)인 모델" });
    const runningSection = runningHeading.nextElementSibling as HTMLElement;
    expect(runningSection.textContent).toBe("확인할 수 없습니다.");

    const activeCountLabel = screen.getByText("적재된 모델 수");
    const activeCountValue = activeCountLabel.nextElementSibling as HTMLElement;
    expect(activeCountValue.textContent).toBe("미측정");
  });

  it("fixture 상태와 빈 프로젝트별 모델 표는 배정 불가를 설명하고 재시작 버튼을 두지 않는다", async () => {
    mockedGateway.getServer.mockResolvedValue(
      server({
        status: "fixture",
        available_model_names: [],
        running_model_names: [],
      }),
    );
    mockedGateway.listModels.mockResolvedValue([]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    expect(screen.getAllByText("확인할 수 없습니다.")).toHaveLength(2);
    expect(screen.getByText("등록된 프로젝트별 모델 배정이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText(/재시작/)).not.toBeInTheDocument();
  });

  it("이 프로젝트에 배정된 모델이 없으면 저장/연결되지 않았다고 꾸며내지 않는다", async () => {
    mockedGateway.getServer.mockResolvedValue(server({ status: "connected" }));
    mockedGateway.listModels.mockResolvedValue([
      projectModel({ project_id: "다른-프로젝트-id", project_name: "다른 프로젝트" }),
    ]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    expect(screen.queryByText("이 프로젝트의 모델")).not.toBeInTheDocument();
    expect(screen.getByText("다른 프로젝트")).toBeInTheDocument();
  });

  it("이 프로젝트에 배정된 모델이 있으면 저장/연결 여부를 명시하고 재시작을 지원하지 않는다고 표시한다", async () => {
    mockedGateway.getServer.mockResolvedValue(server({ status: "connected" }));
    mockedGateway.listModels.mockResolvedValue([
      projectModel({ model: "synthetic-project-model" }),
    ]);
    mockedGateway.listCredentials.mockResolvedValue([]);

    await renderPage();

    const currentCardTitle = screen.getByText("이 프로젝트의 모델");
    const currentCard = currentCardTitle.closest(".card") as HTMLElement;
    expect(currentCard).not.toBeNull();

    expect(within(currentCard).getByText("synthetic-project-model")).toBeInTheDocument();
    expect(within(currentCard).getByText(/아직 저장되지 않으며/)).toBeInTheDocument();
    expect(within(currentCard).getByText(/재시작은 아직 지원되지 않습니다/)).toBeInTheDocument();
    expect(within(currentCard).queryByRole("button")).not.toBeInTheDocument();
  });
});
