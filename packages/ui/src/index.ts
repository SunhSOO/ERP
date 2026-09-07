/** Luminode 공유 UI 라이브러리.
 *
 * 소비자는 이 배럴만 임포트한다. 하위 경로를 직접 임포트하면 tsconfig의 paths와
 * package.json의 exports 해석이 갈라진다.
 *
 * 스타일은 별도로 `@lep/ui/styles/index.css`를 임포트한다.
 */

export type UiStatus = "loading" | "empty" | "error" | "forbidden" | "conflict";

export { StatusTag, Tag } from "./components/StatusTag";
export type { StatusTone, StatusTagProps, TagProps, TagVariant } from "./components/StatusTag";

export { Button, LinkButton } from "./components/Button";
export type { ButtonProps, ButtonVariant, LinkButtonProps } from "./components/Button";

export { Card, CardBody, CardKicker, CardMeta, CardTitle, BlueprintCorners } from "./components/Card";
export type { BlueprintProps, CardProps } from "./components/Card";

export { InputField, SelectField, TextareaField } from "./components/Field";
export type { InputFieldProps, SelectFieldProps, TextareaFieldProps } from "./components/Field";

export { Seg } from "./components/Seg";
export type { SegOption, SegProps } from "./components/Seg";

export { Table, Th } from "./components/Table";
export type { SortDirection, TableProps, ThProps } from "./components/Table";

export { StatBar } from "./components/StatBar";
export type { Stat, StatBarProps } from "./components/StatBar";

export { AiPanel } from "./components/AiPanel";
export type { AiPanelProps } from "./components/AiPanel";

export { Dialog } from "./components/Dialog";
export type { DialogProps } from "./components/Dialog";

export {
  EmptyState,
  ErrorState,
  ForbiddenState,
  OfflineBanner,
  PartialFailureNotice,
  Skeleton,
  StaleBanner,
} from "./states/index";
export type {
  EmptyStateProps,
  ErrorStateProps,
  ForbiddenStateProps,
  PartialFailureNoticeProps,
  SkeletonProps,
  StaleBannerProps,
} from "./states/index";

export { WidgetBoundary } from "./states/WidgetBoundary";
export type { WidgetBoundaryProps } from "./states/WidgetBoundary";

export {
  formatDateKo,
  formatDateTimeKo,
  formatKrw,
  formatMonthDayKo,
  formatPercent,
  formatRelativeKo,
  formatTimeKo,
} from "./locale/format";
