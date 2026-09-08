import { describe, expect, it } from "vitest";
import {
  formatDateKo,
  formatDateTimeKo,
  formatKrw,
  formatMonthDayKo,
  formatPercent,
  formatRelativeKo,
  formatTimeKo,
} from "./format";

/** WP-UI-001의 5번 절차가 저장 시각과 표시 시각의 차이를 테스트하라고 요구한다.
 * 이 차이는 날짜가 하루 넘어가는 곳에서 실제 버그가 된다. */
describe("저장 시각과 표시 시각", () => {
  const lateUtc = "2026-09-06T22:00:00Z";

  it("UTC 밤이면 서울에서는 다음 날이다", () => {
    // 서울은 UTC+9이므로 09-06 22시 UTC는 09-07 07시다.
    expect(formatDateKo(lateUtc)).toContain("09");
    expect(formatDateKo(lateUtc)).toContain("07");
    expect(formatTimeKo(lateUtc)).toBe("07:00");
  });

  it("날짜와 시각을 함께 낼 때도 같은 시간대를 쓴다", () => {
    const formatted = formatDateTimeKo(lateUtc);
    expect(formatted).toContain("07");
    expect(formatted).toContain("07:00");
  });

  it("월-일 표기는 서울 기준 날짜를 쓴다", () => {
    expect(formatMonthDayKo(lateUtc)).toBe("09-07");
  });

  it("UTC 이른 시각은 같은 날에 머문다", () => {
    expect(formatTimeKo("2026-09-07T01:00:00Z")).toBe("10:00");
    expect(formatMonthDayKo("2026-09-07T01:00:00Z")).toBe("09-07");
  });
});

describe("금액과 비율", () => {
  it("원화는 소수점을 쓰지 않는다", () => {
    expect(formatKrw(12500000)).toBe("₩12,500,000");
  });

  it("0원도 그대로 낸다", () => {
    expect(formatKrw(0)).toBe("₩0");
  });

  it("비율은 이미 백분율인 값을 받는다", () => {
    expect(formatPercent(72)).toBe("72%");
    expect(formatPercent(91.5, 1)).toBe("91.5%");
  });
});

describe("상대 시각", () => {
  // 시계에 의존하지 않도록 기준 시각을 주입한다.
  const now = new Date("2026-09-07T05:00:00Z");

  it("몇 분 전을 분 단위로 낸다", () => {
    expect(formatRelativeKo("2026-09-07T04:57:00Z", now)).toBe("3분 전");
  });

  it("열두 시간 전을 시간 단위로 낸다", () => {
    expect(formatRelativeKo("2026-09-06T17:00:00Z", now)).toBe("12시간 전");
  });

  it("1분 미만은 방금으로 낸다", () => {
    expect(formatRelativeKo("2026-09-07T04:59:30Z", now)).toBe("방금");
  });
});
