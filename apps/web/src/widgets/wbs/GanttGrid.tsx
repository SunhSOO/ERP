import type { Milestone, Task } from "@lep/api-client";
import { StatusTag } from "@lep/ui";
import { taskStatus } from "@/src/shared/ui/status";
import styles from "./gantt.module.css";

interface Row {
  id: string;
  label: string;
  status: Task["status"];
  start: string;
  end: string;
  isMilestone: boolean;
  note?: string | null;
}

function monthIndex(iso: string, firstMonth: number): number {
  const date = new Date(iso);
  return date.getUTCFullYear() * 12 + date.getUTCMonth() - firstMonth;
}

export interface GanttGridProps {
  milestones: Milestone[];
  tasks: Task[];
}

/** 간트 차트.
 *
 * 라이브러리를 쓰지 않고 CSS 그리드로 그린다. 의존성을 늘리지 않기 위해서다.
 *
 * 막대의 생김새가 의미를 가진다. 점선은 WBS에 정의되지 않았지만 저장소에서
 * 감지된 작업이고, 흐린 막대는 완료 표시됐지만 PR이 병합되지 않은 것이다.
 * 두 경우 모두 텍스트 배지가 함께 붙으므로 모양만으로 판단하지 않아도 된다.
 */
export function GanttGrid({ milestones, tasks }: GanttGridProps) {
  const rows: Row[] = [
    ...milestones.map((item) => ({
      id: item.id,
      label: `${item.code} ${item.name}`,
      status: item.status,
      start: item.start,
      end: item.end,
      isMilestone: true,
      note: item.status === "in_progress" ? `진행 ${item.progress_percent}%` : null,
    })),
    ...tasks.map((item) => ({
      id: item.id,
      label: `${item.code} ${item.title}`,
      status: item.status,
      start: item.start,
      end: item.end,
      isMilestone: false,
      note: item.vcs_ref,
    })),
  ].sort((a, b) => a.start.localeCompare(b.start));

  if (rows.length === 0) return null;

  const starts = rows.map((row) => new Date(row.start));
  const ends = rows.map((row) => new Date(row.end));
  const firstMonth = Math.min(
    ...starts.map((d) => d.getUTCFullYear() * 12 + d.getUTCMonth()),
  );
  const lastMonth = Math.max(...ends.map((d) => d.getUTCFullYear() * 12 + d.getUTCMonth()));
  const monthCount = lastMonth - firstMonth + 1;

  const months = Array.from({ length: monthCount }, (_, index) => {
    const absolute = firstMonth + index;
    return `${(absolute % 12) + 1}월`;
  });

  return (
    <div className="overflow-x-auto">
      <table className={styles.gantt} style={{ minWidth: `${320 + monthCount * 68}px` }}>
        <caption className="sr-only">
          마일스톤과 태스크의 기간. 점선 막대는 WBS 외 작업, 흐린 막대는 완료 표시됐으나 미병합.
        </caption>
        <thead>
          <tr>
            <th scope="col">태스크</th>
            {months.map((month) => (
              <th key={month} scope="col">
                {month}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const from = monthIndex(row.start, firstMonth);
            const to = monthIndex(row.end, firstMonth);
            const { tone, label } = taskStatus(row.status);

            return (
              <tr key={row.id}>
                <th className={row.isMilestone ? styles.milestone : undefined} scope="row">
                  <span className="flex items-center gap-2">
                    <span className="flex-1">{row.label}</span>
                    <StatusTag tone={tone}>{row.note ?? label}</StatusTag>
                  </span>
                </th>
                {months.map((month, index) => (
                  <td key={month}>
                    {index === from ? (
                      <span
                        className={[
                          styles.bar,
                          row.status === "vcs_only" ? styles.barDashed : "",
                          row.status === "done" ? styles.barDone : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        style={{ width: `calc(${to - from + 1} * 100% + ${to - from} * 1px)` }}
                      />
                    ) : null}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
