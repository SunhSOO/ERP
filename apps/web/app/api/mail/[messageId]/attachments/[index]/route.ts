import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

const BASE_URL = process.env.LEP_API_BASE_URL ?? "http://127.0.0.1:8000";

const SAFE_ERROR_HEADERS = {
  "content-type": "text/plain; charset=utf-8",
  "x-content-type-options": "nosniff",
  "cache-control": "private, no-store",
};

function errorResponse(status: number, message: string): Response {
  return new Response(message, { status, headers: SAFE_ERROR_HEADERS });
}

/** 원본 메일에서 온 것이라 상태별로 뜻이 다른 오류를 한국어로 정리한다.
 *
 * 404는 원본 메일/첨부가 이미 삭제된 것이고, 409는 승인 당시 확정한 checksum과
 * 지금 원본이 달라졌다는 뜻이다(ADR-021). 둘 다 "가져오지 못했습니다"로
 * 뭉뚱그리면 사용자가 재시도로 해결할 수 있는 문제인지 알 수 없다.
 */
function upstreamErrorMessage(status: number): string {
  if (status === 404) return "첨부를 찾을 수 없습니다. 원본 메일이 삭제되었을 수 있습니다.";
  if (status === 409) return "첨부 내용이 승인 당시와 달라 내려받을 수 없습니다.";
  if (status === 403) return "이 첨부를 볼 권한이 없습니다.";
  return "첨부를 가져오지 못했습니다.";
}

/** 메일 첨부를 내려받는 통로.
 *
 * 브라우저는 백엔드에 직접 닿지 못한다. api는 호스트로 포트를 내지 않고
 * compose 네트워크 안에만 있다. 그래서 웹이 대신 받아 그대로 흘려보낸다.
 *
 * 본문을 메모리에 통째로 올리지 않고 스트림으로 넘긴다. 3.6MB짜리 zip이
 * 오가는 메일함이고, 앞으로 더 큰 것도 온다.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ messageId: string; index: string }> },
) {
  const { messageId, index } = await context.params;

  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  // 드라이브/메일함이 다운로드에 붙이는 `linked_file_id`와 `id_encoding`만 옮긴다(ADR-021:
  // 계정 교체로 인한 UIDL 재사용을 백엔드가 이 값으로 방어한다). 그 외 쿼리는
  // 임의 URL/파라미터 주입을 막기 위해 버린다.
  const linkedFileId = request.nextUrl.searchParams.get("linked_file_id");
  const idEncoding = request.nextUrl.searchParams.get("id_encoding");
  if (idEncoding !== null && idEncoding !== "base64url") {
    return errorResponse(422, "잘못된 id_encoding입니다.");
  }
  const upstreamPath = `${BASE_URL}/api/v1/mail/${encodeURIComponent(messageId)}/attachments/${encodeURIComponent(index)}`;
  const queryParts: string[] = [];
  if (linkedFileId) queryParts.push(`linked_file_id=${encodeURIComponent(linkedFileId)}`);
  if (idEncoding === "base64url") queryParts.push(`id_encoding=${idEncoding}`);
  const upstreamUrl = queryParts.length ? `${upstreamPath}?${queryParts.join("&")}` : upstreamPath;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: "no-store",
    });
  } catch {
    return errorResponse(502, "첨부 서버에 연결하지 못했습니다.");
  }

  if (!upstream.ok) {
    // 실패를 파일인 척 내려보내지 않는다. 0바이트짜리 파일이 저장되면
    // 사용자는 첨부가 원래 비어 있었다고 생각한다.
    return errorResponse(upstream.status, upstreamErrorMessage(upstream.status));
  }

  // 허용 목록에 없는 업스트림 헤더(예: 백엔드 세션 쿠키)는 옮기지 않는다.
  const headers = new Headers();
  for (const name of ["content-type", "content-disposition", "content-length"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (!headers.has("content-disposition")) {
    headers.set("content-disposition", "attachment");
  }
  headers.set("x-content-type-options", "nosniff");
  headers.set("cache-control", "private, no-store");

  return new Response(upstream.body, { status: 200, headers });
}
