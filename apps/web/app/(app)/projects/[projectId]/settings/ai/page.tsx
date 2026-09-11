import type { LlmRuntimeStatus } from "@lep/api-client";
import { Card, CardTitle, StatBar, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { linkHealth } from "@/src/shared/ui/status";

export const dynamic = "force-dynamic";

const PRIORITY_LABEL = { high: "높음", normal: "보통", low: "낮음" } as const;

const RUNTIME_LABEL: Record<LlmRuntimeStatus, string> = {
  connected: "연결됨",
  degraded: "일부 확인 불가",
  unavailable: "연결 불가",
  fixture: "미설정 (픽스처)",
  not_configured: "설정 미완료",
};

/** 설치 모델 목록(``/models``)이 실제로 조회된 상태. 이 상태에서 빈 배열은
 * 측정된 0개이지, 조회 실패가 아니다. */
const AVAILABLE_MEASURED_STATUSES = new Set<LlmRuntimeStatus>(["connected", "degraded"]);

/** 09 로컬 LLM · AI 설정. */
export default async function AiSettingsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [server, models, credentials] = await Promise.all([
    gateway.getServer(),
    gateway.listModels(),
    gateway.listCredentials(projectId),
  ]);

  const current = models.find((model) => model.project_id === projectId);

  return (
    <>
      <PageHeader
        note="추론 서버의 연결 상태와 설치·적재된 모델을 확인합니다"
        title="AI · 로컬 LLM 설정"
      />

      <StatBar
        label="공통 서버 상태"
        stats={[
          { label: "공통 서버", value: server.name },
          { label: "연결 상태", value: RUNTIME_LABEL[server.status] },
          {
            label: "GPU 사용률",
            value: server.gpu_usage_percent === null ? "미측정" : `${server.gpu_usage_percent}%`,
          },
          {
            label: "적재된 모델 수",
            value: server.active_model_count === null ? "미측정" : server.active_model_count,
          },
          { label: "프로젝트", value: `${server.project_count}개` },
        ]}
      />

      {/* 서버 쪽 문구(fixtures.py _SERVER). 여기서 하드코딩하지 않는다. */}
      <p className="m-0 border border-divider p-3 text-[13px]">
        <span aria-hidden="true">○ </span>
        {server.network_note}
      </p>

      <p className="text-muted m-0 text-[12px]">{server.detail}</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">설치된 모델</h2>
          {server.available_model_names.length > 0 ? (
            <ul className="m-0 list-none p-0 font-mono text-[12px]">
              {server.available_model_names.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          ) : (
            <p className="text-muted m-0 text-[12px]">
              {AVAILABLE_MEASURED_STATUSES.has(server.status)
                ? "설치된 모델이 없습니다."
                : "확인할 수 없습니다."}
            </p>
          )}
        </div>
        <div>
          <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">
            실행 중(적재됨)인 모델
          </h2>
          {server.running_model_names.length > 0 ? (
            <ul className="m-0 list-none p-0 font-mono text-[12px]">
              {server.running_model_names.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          ) : (
            <p className="text-muted m-0 text-[12px]">
              {server.status === "connected" ? "적재된 모델이 없습니다." : "확인할 수 없습니다."}
            </p>
          )}
        </div>
      </div>

      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">프로젝트별 모델</h2>
      <Table caption="프로젝트별 모델 배정과 GPU 할당">
        <thead>
          <tr>
            <Th>프로젝트</Th>
            <Th>모델</Th>
            <Th>상태</Th>
            <Th>GPU 할당</Th>
          </tr>
        </thead>
        <tbody>
          {models.length > 0 ? (
            models.map((model) => (
              <tr key={model.project_id}>
                <td>{model.project_name}</td>
                <td className="font-mono text-[12px]">
                  {model.model ?? <span className="text-muted">미설정 (공통 모델 사용)</span>}
                </td>
                <td>
                  <StatusTag tone={model.state === "running" ? "success" : "idle"}>
                    {model.state === "running" ? "실행 중" : "중지"}
                  </StatusTag>
                </td>
                <td className="tabular-nums">
                  {model.priority && model.gpu_share_percent !== null ? (
                    `우선순위 ${PRIORITY_LABEL[model.priority]} · ${model.gpu_share_percent}%`
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={4} className="text-muted text-[12px]">
                등록된 프로젝트별 모델 배정이 없습니다.
              </td>
            </tr>
          )}
        </tbody>
      </Table>

      {current ? (
        <Card blueprint>
          <CardTitle>이 프로젝트의 모델</CardTitle>
          <p className="m-0 font-mono text-[13px]">
            {current.model ?? "미설정"}
          </p>
          <p className="text-muted m-0 text-[12px]">
            이 배정은 아직 저장되지 않으며, 문서·메일·회의록 처리가 실제로 이 모델을
            사용하도록 연결돼 있지도 않습니다.
          </p>
          <p className="text-muted m-0 text-[12px]">
            재시작은 아직 지원되지 않습니다. 이 화면은 서버 상태를 읽기만 합니다.
          </p>
        </Card>
      ) : null}

      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">연동 자격증명</h2>
      <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4 p-0">
        {credentials.map((credential) => {
          const health = linkHealth(credential.health);
          return (
            <li key={credential.kind}>
              <Card>
                <div className="flex items-baseline justify-between gap-2">
                  <CardTitle>{credential.label}</CardTitle>
                  <StatusTag tone={health.tone}>{health.label}</StatusTag>
                </div>
                <p className="text-muted m-0 text-[12px]">{credential.detail}</p>
                {credential.missing_input ? (
                  <p className="m-0 text-[12px]">
                    필요한 입력: <strong>{credential.missing_input}</strong>
                  </p>
                ) : null}
              </Card>
            </li>
          );
        })}
      </ul>

      <p className="text-muted m-0 text-[12px]">
        이 화면에서는 연결 상태만 조회합니다. 연결 설정 변경은 관리자에게 문의해 주세요.
      </p>
    </>
  );
}
