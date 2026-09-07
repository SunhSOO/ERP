import {
  AiPanel,
  Button,
  Card,
  CardBody,
  CardKicker,
  CardMeta,
  CardTitle,
  StatBar,
  StatusTag,
  Table,
  Tag,
  Th,
  formatDateKo,
  formatDateTimeKo,
  formatKrw,
  formatPercent,
  formatRelativeKo,
} from "@lep/ui";
import type { StatusTone } from "@lep/ui";
import { InputField, SelectField, TextareaField } from "@lep/ui";
import { DialogDemo } from "@/src/widgets/dev/DialogDemo";
import { SegDemo } from "@/src/widgets/dev/SegDemo";

/** 컴포넌트 갤러리.
 *
 * WP-UI-001의 7번 절차가 요구하는 화면이다. 각 컴포넌트를 상태별로 한자리에서
 * 확인한다. Storybook을 도입하지 않고 이 페이지가 그 역할을 한다.
 */

const TONES: { tone: StatusTone; label: string }[] = [
  { tone: "success", label: "정합" },
  { tone: "warning", label: "동기화 지연" },
  { tone: "danger", label: "불일치 2" },
  { tone: "info", label: "안내" },
  { tone: "progress", label: "진행 72%" },
  { tone: "idle", label: "중지" },
  { tone: "ai", label: "AI 제안" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-muted m-0 text-[11px] tracking-wide uppercase">{title}</h2>
      {children}
    </section>
  );
}

export default function ComponentsGallery() {
  const now = new Date("2026-09-07T05:00:00Z");

  return (
    <>
      <h1 className="m-0 text-[22px]">컴포넌트</h1>

      <Section title="StatusTag — 상태 배지">
        <p className="text-muted m-0 text-[12px]">
          색상 전용 속성이 없다. 색상만으로 상태를 구분하는 배지를 만들 수 없다.
          글리프와 텍스트가 항상 함께 나온다.
        </p>
        <div className="flex flex-wrap gap-2">
          {TONES.map(({ tone, label }) => (
            <StatusTag key={tone} tone={tone}>
              {label}
            </StatusTag>
          ))}
        </div>
      </Section>

      <Section title="Tag — 분류 배지">
        <div className="flex flex-wrap gap-2">
          <Tag variant="accent">accent</Tag>
          <Tag variant="accent-2">accent-2</Tag>
          <Tag variant="neutral">neutral</Tag>
          <Tag variant="outline">용역사</Tag>
        </div>
      </Section>

      <Section title="Button">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="primary">기본</Button>
          <Button variant="secondary">보조</Button>
          <Button variant="ghost">고스트</Button>
          <Button size="sm" variant="secondary">
            작은 버튼
          </Button>
          <Button disabled disabledReason="신뢰도가 낮아 사람 확인이 필요합니다." variant="secondary">
            비활성 (사유 있음)
          </Button>
        </div>
        <p className="text-muted m-0 text-[12px]">
          비활성 버튼에는 사유가 붙는다. 사유 없는 비활성은 만들지 않는다.
        </p>
      </Section>

      <Section title="Card">
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
          <Card>
            <CardKicker>일반 카드</CardKicker>
            <CardTitle>기본형</CardTitle>
            <CardBody>모서리 표식이 없는 형태.</CardBody>
            <CardMeta>메타 정보</CardMeta>
          </Card>
          <Card blueprint>
            <CardKicker>blueprint</CardKicker>
            <CardTitle>등록 표식</CardTitle>
            <CardBody>네 모서리에 표식을 그린다. 표식은 보조기술에서 감춘다.</CardBody>
          </Card>
          <Card elevation="md">
            <CardTitle>elevation md</CardTitle>
            <CardBody>그림자 단계.</CardBody>
          </Card>
        </div>
      </Section>

      <Section title="Form">
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
          <InputField hint="프로젝트 코드를 입력합니다." label="프로젝트 코드" />
          <InputField error="이미 사용 중인 코드입니다." label="오류 상태" />
          <SelectField label="GPU 우선순위">
            <option value="high">높음</option>
            <option value="normal">보통</option>
            <option value="low">낮음</option>
          </SelectField>
          <TextareaField label="차단 사유" />
        </div>
      </Section>

      <Section title="Seg — 세그먼티드 컨트롤">
        <SegDemo />
        <p className="text-muted m-0 text-[12px]">
          라디오 기반이라 좌우 방향키로 이동한다. fieldset과 숨김 legend를 가진다.
        </p>
      </Section>

      <Section title="Table">
        <Table caption="예시 표" showCaption>
          <thead>
            <tr>
              <Th sort="ascending">코드</Th>
              <Th>제목</Th>
              <Th>상태</Th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-mono text-[12px]">TSK-1038</td>
              <td>IF 정의서 v2</td>
              <td>
                <StatusTag tone="danger">차단</StatusTag>
              </td>
            </tr>
            <tr>
              <td className="font-mono text-[12px]">TSK-1042</td>
              <td>검수 시나리오 작성</td>
              <td>
                <StatusTag tone="progress">진행</StatusTag>
              </td>
            </tr>
          </tbody>
        </Table>
      </Section>

      <Section title="StatBar">
        <StatBar
          label="예시 지표"
          stats={[
            { label: "리포지토리", value: "daon-corp/logistics-platform" },
            { label: "열린 PR", value: 4 },
            { label: "정합률", value: "91%" },
          ]}
        />
      </Section>

      <Section title="AiPanel">
        <AiPanel
          actions={<Button size="sm" variant="secondary">근거 보기</Button>}
          title="AI 요약"
        >
          <p className="m-0">
            AI가 만든 내용은 전용 색상과 ◆ 표식으로 사람 입력과 구분한다.
          </p>
        </AiPanel>
      </Section>

      <Section title="Dialog">
        <DialogDemo />
        <p className="text-muted m-0 text-[12px]">
          네이티브 dialog를 쓴다. 포커스 트랩과 ESC 닫기가 플랫폼에서 온다.
        </p>
      </Section>

      <Section title="한국어 표시 형식">
        <Table caption="포맷터 출력" showCaption>
          <thead>
            <tr>
              <Th>함수</Th>
              <Th>출력</Th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-mono text-[12px]">formatDateKo</td>
              <td>{formatDateKo("2026-09-06T22:00:00Z")}</td>
            </tr>
            <tr>
              <td className="font-mono text-[12px]">formatDateTimeKo</td>
              <td>{formatDateTimeKo("2026-09-06T22:00:00Z")}</td>
            </tr>
            <tr>
              <td className="font-mono text-[12px]">formatKrw</td>
              <td>{formatKrw(12500000)}</td>
            </tr>
            <tr>
              <td className="font-mono text-[12px]">formatPercent</td>
              <td>{formatPercent(72)}</td>
            </tr>
            <tr>
              <td className="font-mono text-[12px]">formatRelativeKo</td>
              <td>{formatRelativeKo("2026-09-07T04:57:00Z", now)}</td>
            </tr>
          </tbody>
        </Table>
        <p className="text-muted m-0 text-[12px]">
          저장은 UTC, 표시는 Asia/Seoul이다. 위 첫 두 줄은 UTC로 09월 06일 22시인 값이
          서울에서 09월 07일로 넘어가는 것을 보여준다.
        </p>
      </Section>
    </>
  );
}
