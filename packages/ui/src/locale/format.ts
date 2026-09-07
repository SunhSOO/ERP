/** 한국어 표시 형식.
 *
 * 저장은 UTC로 하고 표시는 Asia/Seoul로 한다. 두 값이 다르다는 점이 중요하다.
 * 예를 들어 `2026-09-06T22:00:00Z`는 서울에서 09월 07일 07시다. 날짜가 하루
 * 넘어간다. 이 차이를 테스트로 고정한다.
 */

const TIME_ZONE = "Asia/Seoul";
const LOCALE = "ko-KR";

function toDate(value: Date | string): Date {
  return value instanceof Date ? value : new Date(value);
}

/** 2026. 9. 7. 형태. 표는 좁으므로 두 자리로 맞춘다. */
export function formatDateKo(value: Date | string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(toDate(value));
}

/** 목업의 표에 쓰인 09-06 형태. 연도가 맥락에서 자명할 때만 쓴다. */
export function formatMonthDayKo(value: Date | string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    month: "2-digit",
    day: "2-digit",
  })
    .format(toDate(value))
    .replace(/\.\s?/g, "-")
    .replace(/-$/, "");
}

/** 2026. 09. 07. 15:30 형태. */
export function formatDateTimeKo(value: Date | string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(toDate(value));
}

/** 14:20 형태. 오늘 안의 시각에만 쓴다. */
export function formatTimeKo(value: Date | string): string {
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(toDate(value));
}

/** 원화. 소수점을 쓰지 않는다. */
export function formatKrw(amount: number): string {
  return new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: "KRW",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** 72% 형태. 0에서 1 사이가 아니라 이미 백분율인 값을 받는다. */
export function formatPercent(value: number, fractionDigits = 0): string {
  return `${new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value)}%`;
}

const RELATIVE_UNITS: readonly (readonly [Intl.RelativeTimeFormatUnit, number])[] = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

/** "3분 전", "12시간 전" 형태. 목업의 동기화 상태 표시에 쓴다.
 *
 * `now`를 주입받는다. 테스트가 시계에 의존하지 않게 하기 위해서다. */
export function formatRelativeKo(value: Date | string, now: Date = new Date()): string {
  const diff = toDate(value).getTime() - now.getTime();
  const formatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });

  for (const [unit, ms] of RELATIVE_UNITS) {
    if (Math.abs(diff) >= ms) {
      return formatter.format(Math.round(diff / ms), unit);
    }
  }
  return "방금";
}
