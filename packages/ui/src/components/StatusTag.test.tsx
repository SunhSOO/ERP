import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusTag } from "./StatusTag";

/** 06_UI_UX 7절: 색상만으로 상태를 표현하지 않는다.
 * 규칙이 문서에만 있으면 지켜지지 않으므로 여기서 고정한다. */
describe("StatusTag", () => {
  it("항상 텍스트를 함께 낸다", () => {
    render(<StatusTag tone="danger">불일치 2</StatusTag>);
    expect(screen.getByText("불일치 2")).toBeInTheDocument();
  });

  it("상태마다 다른 글리프를 붙인다", () => {
    const { container: success } = render(<StatusTag tone="success">정합</StatusTag>);
    const { container: danger } = render(<StatusTag tone="danger">불일치</StatusTag>);

    expect(success.textContent).toContain("●");
    expect(danger.textContent).toContain("✕");
  });

  it("글리프는 보조기술에서 감춘다", () => {
    const { container } = render(<StatusTag tone="warning">지연</StatusTag>);
    const glyph = container.querySelector("[aria-hidden='true']");

    expect(glyph).not.toBeNull();
    expect(glyph?.textContent).toBe("▲");
  });

  it("글리프를 숨겨도 텍스트는 남는다", () => {
    render(
      <StatusTag hideGlyph tone="idle">
        중지
      </StatusTag>,
    );
    expect(screen.getByText("중지")).toBeInTheDocument();
  });

  it("상태별로 다른 클래스를 쓴다", () => {
    const { container } = render(<StatusTag tone="ai">AI 제안</StatusTag>);
    expect(container.firstElementChild?.className).toContain("tag-ai");
  });
});
