import Link from "next/link";
import type { DriveFile } from "@lep/api-client";
import { mailMessagePath, mailMessageQuery } from "@/src/shared/data/mail-message-id";

export interface DriveMailLinkProps {
  file: DriveFile;
  /** 소스 메일이 속한(승인된) 프로젝트. 메일함 링크를 이 프로젝트로 보낸다. */
  projectId: string;
}

/** 메일 원본 연결 파일의 출처 메일 링크와 다운로드 링크. ADR-021.
 *
 * `source_mail_id`/`source_part_index`가 없으면 로컬에 파일이 있는 척 링크를
 * 만들지 않는다. 메일함 링크는 항상 현재 프로젝트의 `project` 탭으로 보내며,
 * 목록 페이지네이션 범위 밖의 메일이어도 승인된(현재 프로젝트로 확정된) 소스
 * 메일이면 메일함이 단건 조회로 그 딥링크를 보여준다(목록 범위 자체를
 * 벗어난 임의 메일 ID를 조회하게 만들지는 않는다 — classification/project_id를
 * 다시 검증한다).
 */
export function DriveMailLink({ file, projectId }: DriveMailLinkProps) {
  if (file.source_kind !== "mail_attachment") return null;

  if (file.source_mail_id === null || file.source_part_index === null) {
    return <span className="text-muted text-[11px]">출처 메일을 확인할 수 없습니다</span>;
  }

  const linkedFileId = encodeURIComponent(file.id);
  const mailHref = `/projects/${encodeURIComponent(projectId)}/mail?status=project&mail=${encodeURIComponent(file.source_mail_id)}&linked_file_id=${linkedFileId}`;
  const idQuery = mailMessageQuery(file.source_mail_id);
  const downloadHref = `/api/mail/${mailMessagePath(file.source_mail_id)}/attachments/${file.source_part_index}${idQuery}${idQuery ? "&" : "?"}linked_file_id=${linkedFileId}`;

  return (
    <span className="flex flex-wrap items-center gap-2 text-[11px]">
      <Link className="no-underline" href={mailHref}>
        출처 메일 보기
      </Link>
      <a href={downloadHref}>다운로드</a>
    </span>
  );
}
