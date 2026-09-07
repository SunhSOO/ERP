import { Card, CardTitle, StatBar, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { restartModelAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { linkHealth } from "@/src/shared/ui/status";

export const dynamic = "force-dynamic";

const PRIORITY_LABEL = { high: "높음", normal: "보통", low: "낮음" } as const;

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
        note="모델·볼트·연동은 프로젝트별로 각각 설정됩니다"
        title="AI · 로컬 LLM 설정"
      />

      <StatBar
        label="공통 서버 상태"
        stats={[
          { label: "공통 서버", value: server.name },
          { label: "GPU 전체 사용량", value: `${server.gpu_usage_percent}%` },
          { label: "활성 모델 수", value: server.active_model_count },
          { label: "프로젝트", value: `${server.project_count}개` },
        ]}
      />

      {/* 개인정보 처리 원칙. 목업이 화면에 명시하는 약속이라 그대로 유지한다. */}
      <p className="m-0 border border-divider p-3 text-[13px]">
        <span aria-hidden="true">○ </span>
        {server.network_note}
      </p>

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
          {models.map((model) => (
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
          ))}
        </tbody>
      </Table>

      {current ? (
        <Card blueprint>
          <CardTitle>이 프로젝트의 모델</CardTitle>
          <p className="m-0 font-mono text-[13px]">
            {current.model ?? "미설정"}
          </p>
          <p className="text-muted m-0 text-[12px]">
            이 프로젝트의 문서·메일·회의록은 위 모델로만 처리됩니다. 다른 프로젝트와 격리됩니다.
          </p>
          <div className="flex flex-wrap gap-2">
            <ActionButton
              action={restartModelAction.bind(null, projectId)}
              disabledReason={
                current.model === null ? "모델이 설정되지 않았습니다." : undefined
              }
            >
              재시작
            </ActionButton>
          </div>
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
        이 단계에서는 실제 비밀 값을 입력받지 않습니다. 자격증명 저장은 인증이 들어오는
        WP-PKD-021 이후에 열립니다.
      </p>
    </>
  );
}
