import Link from "next/link";
import { Card, CardTitle, EmptyState, StatusTag, Table, Th } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { DRIVE_PAGE_SIZE, fetchDriveFilesPage, normalizeDriveOffset } from "@/src/shared/data/mail-review";
import { PageHeader } from "@/src/shared/ui/PageHeader";
import { DriveMailLink } from "@/src/widgets/mail/DriveMailLink";

export const dynamic = "force-dynamic";

function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)}MB`;
  return `${Math.round(bytes / 1000)}KB`;
}

function categoryHref(category: string): string {
  // 분류를 바꾸는 링크는 항상 offset을 되돌린다(쿼리 생략 = 0쪽).
  return `?${new URLSearchParams({ category }).toString()}`;
}

function pageOffsetHref(category: string | undefined, offset: number): string {
  const query = new URLSearchParams();
  if (category) query.set("category", category);
  query.set("offset", String(offset));
  return `?${query.toString()}`;
}

/** 10 프로젝트 드라이브. */
export default async function DrivePage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ category?: string; offset?: string }>;
}) {
  const { projectId } = await params;
  const { category, offset: offsetParam } = await searchParams;
  const offset = normalizeDriveOffset(offsetParam);

  const categories = await gateway.getDrive(projectId);
  const active = categories.find((item) => item.category === category) ?? categories[0];
  const { files, hasMore } = await fetchDriveFilesPage(projectId, active?.category, offset);

  return (
    <>
      <PageHeader title="프로젝트 드라이브" />

      <section aria-label="문서 분류">
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4 p-0">
          {categories.map((item) => (
            <li key={item.category}>
              <Link className="block no-underline" href={categoryHref(item.category)}>
                <Card className={item.category === active?.category ? "border-accent" : undefined}>
                  <div className="flex items-baseline justify-between gap-2">
                    <CardTitle>{item.label}</CardTitle>
                    <span className="tabular-nums text-[15px]">{item.count}</span>
                  </div>
                  <p className="text-muted m-0 text-[12px]">{item.description}</p>
                  {item.warning ? (
                    <StatusTag tone="warning">{item.warning}</StatusTag>
                  ) : null}
                  {item.read_only ? <StatusTag tone="idle">읽기 전용</StatusTag> : null}
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <nav aria-label="드라이브 파일 페이지" className="flex items-center gap-2">
        {offset > 0 ? (
          <Link
            className="no-underline"
            href={pageOffsetHref(active?.category, Math.max(0, offset - DRIVE_PAGE_SIZE))}
          >
            이전
          </Link>
        ) : null}
        {hasMore ? (
          <Link
            className="no-underline"
            href={pageOffsetHref(active?.category, offset + DRIVE_PAGE_SIZE)}
          >
            다음
          </Link>
        ) : null}
      </nav>

      {files.length === 0 ? (
        <EmptyState
          description="다른 분류를 선택하거나 파일을 올려 보세요."
          title="이 분류에 파일이 없습니다"
          variant="no-results"
        />
      ) : (
        <Table caption={`${active?.label ?? "전체"} 파일 목록`}>
          <thead>
            <tr>
              <Th>이름</Th>
              <Th>출처</Th>
              <Th>크기</Th>
              <Th>수정일</Th>
            </tr>
          </thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.id}>
                <td>
                  <span aria-hidden="true">📄 </span>
                  {file.name}
                  {file.warning ? (
                    <>
                      {" "}
                      <StatusTag tone="warning">{file.warning}</StatusTag>
                    </>
                  ) : null}
                </td>
                <td className="text-muted">
                  {file.origin}
                  {file.source_kind === "mail_attachment" ? (
                    <>
                      {" "}
                      <DriveMailLink file={file} projectId={projectId} />
                    </>
                  ) : null}
                </td>
                <td className="tabular-nums">{formatSize(file.size_bytes)}</td>
                <td className="tabular-nums">{file.modified}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {active?.read_only ? (
        <p className="text-muted m-0 text-[12px]">
          원본문서는 수정할 수 없습니다. 변경이 필요하면 새 버전을 산출문서 폴더에 올리세요.
          메일·회의록에서 자동 수집된 파일은 출처가 표시됩니다.
        </p>
      ) : null}
    </>
  );
}
