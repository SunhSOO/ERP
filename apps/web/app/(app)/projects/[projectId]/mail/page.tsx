import Link from "next/link";
import { AiPanel, Card, EmptyState, StatusTag } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { dismissMailAction, promoteMailAction } from "@/src/shared/data/actions";
import { ActionButton } from "@/src/shared/ui/ActionButton";
import { PageHeader } from "@/src/shared/ui/PageHeader";

export const dynamic = "force-dynamic";

const CONFIDENCE_LABEL = { high: "높음", medium: "중", low: "낮음" } as const;

/** 06 메일함. */
export default async function MailPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ mail?: string }>;
}) {
  const { projectId } = await params;
  const { mail: selectedId } = await searchParams;

  const messages = await gateway.listMail(projectId);

  if (messages.length === 0) {
    return (
      <>
        <PageHeader title="메일함" />
        <EmptyState
          description="하이웍스 연동이 설정되면 프로젝트 관련 메일이 여기에 모입니다."
          title="아직 메일이 없습니다"
          variant="no-data"
        />
      </>
    );
  }

  const [message, user] = await Promise.all([
    gateway.getMail(selectedId ?? messages[0].id),
    gateway.me(),
  ]);
  const unclassified = messages.filter(
    (item) => item.classification === "unclassified" && !item.handled,
  );

  return (
    <>
      <PageHeader note={`미분류 ${unclassified.length}건`} title="메일함" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(280px,380px)_1fr]">
        <section aria-label="메일 목록">
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {messages.map((item) => (
              <li key={item.id}>
                <Link className="block no-underline" href={`?mail=${item.id}`}>
                  <Card className={item.id === message.id ? "border-accent" : undefined}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-[13px]">
                        {item.sender_name} ({item.sender_org})
                      </span>
                      <span className="text-muted text-[11px] tabular-nums">
                        {item.received_at.slice(11, 16)}
                      </span>
                    </div>
                    <span className="text-[13px]">{item.subject}</span>
                    {item.classification === "unclassified" && !item.handled ? (
                      <StatusTag tone="warning">
                        {item.intent ? `${item.intent} 추정` : "미분류"}
                      </StatusTag>
                    ) : item.classification === "unrelated" ? (
                      <StatusTag tone="idle">프로젝트 무관</StatusTag>
                    ) : (
                      <StatusTag tone="success">분류됨</StatusTag>
                    )}
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="메일 상세" className="flex flex-col gap-3">
          <h2 className="m-0 text-[17px]">{message.subject}</h2>
          <p className="text-muted m-0 text-[12px]">
            {message.sender_name} ({message.sender_org}) → {user?.display_name} ·{" "}
            <span className="tabular-nums">{message.received_at.slice(11, 16)}</span>
          </p>

          {message.intent && message.confidence ? (
            <StatusTag tone="warning">
              분류: {message.intent} (신뢰도 {CONFIDENCE_LABEL[message.confidence]})
            </StatusTag>
          ) : null}

          <p className="m-0 border border-divider p-3 text-[13px] whitespace-pre-wrap">
            {message.body}
          </p>

          <AiPanel
            actions={
              <>
                <ActionButton
                  action={promoteMailAction.bind(null, projectId, message.id)}
                  disabledReason={
                    message.note_id ? "이미 지식화된 메일입니다." : undefined
                  }
                >
                  지식화 (볼트에 노트 생성)
                </ActionButton>
                <ActionButton action={dismissMailAction.bind(null, projectId, message.id)}>
                  분류 아님
                </ActionButton>
              </>
            }
            title="AI 분석"
          >
            {message.intent ? (
              <p className="m-0">
                이 메일은 {message.milestone_code ?? "해당 프로젝트"} 관련{" "}
                <strong>{message.intent}</strong>으로 보입니다
                {message.confidence ? ` (신뢰도 ${CONFIDENCE_LABEL[message.confidence]})` : ""}.
              </p>
            ) : (
              <p className="m-0">추가로 제안할 조치가 없습니다.</p>
            )}
            <p className="text-muted m-0 mt-2 text-[12px]">
              메일 내용으로 일정을 자동 변경하지 않습니다. 필요한 변경은 WBS 화면에서
              직접 반영해 주세요.
            </p>
          </AiPanel>
        </section>
      </div>
    </>
  );
}
