import { afterEach, describe, expect, it, vi } from "vitest";
import type { NextRequest } from "next/server";

const cookieGetAll = vi.fn(() => [{ name: "lep_session", value: "test-session" }]);
vi.mock("next/headers", () => ({
  cookies: async () => ({ getAll: cookieGetAll }),
}));

import { GET } from "@/app/api/mail/[messageId]/attachments/[index]/route";

function context(messageId: string, index: string) {
  return { params: Promise.resolve({ messageId, index }) };
}

function requestWithUrl(url: string): NextRequest {
  return { nextUrl: new URL(url) } as unknown as NextRequest;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("메일 첨부 프록시", () => {
  it("성공 응답은 허용 헤더만 옮기고 nosniff/no-store/첨부 헤더를 강제한다", async () => {
    const upstream = new Response("file-bytes", {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-length": "10",
        "set-cookie": "backend_secret=abc",
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(upstream));

    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/pdf");
    expect(response.headers.get("content-disposition")).toBe("attachment");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("업스트림이 한글 파일명을 RFC5987로 인코딩한 content-disposition을 주면 그대로 존중한다", async () => {
    // Headers는 ByteString(Latin1)만 받으므로 raw 한글을 헤더 값에 넣으면 생성자가
    // 던진다. 실제 백엔드도 이 계약대로 filename*=UTF-8''로 인코딩해서 보낸다.
    const encodedDisposition = `attachment; filename="attachment.pdf"; filename*=UTF-8''${encodeURIComponent("견적서.pdf")}`;
    const upstream = new Response("file-bytes", {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": encodedDisposition,
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(upstream));

    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    expect(response.headers.get("content-disposition")).toBe(encodedDisposition);
    expect(response.headers.get("content-disposition")).toContain('filename="attachment.pdf"');
    expect(response.headers.get("content-disposition")).toContain(encodeURIComponent("견적서.pdf"));
  });

  it("404는 원본 삭제 가능성을 한국어로 안내하고 상태코드를 보존한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));

    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    expect(response.status).toBe(404);
    expect(response.headers.get("content-type")).toBe("text/plain; charset=utf-8");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    const text = await response.text();
    expect(text).toContain("삭제");
  });

  it("409는 checksum 불일치를 안내하고 상태코드를 보존한다(가짜 다운로드 없음)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 409 })));

    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    expect(response.status).toBe(409);
    const text = await response.text();
    expect(text).toContain("달라");
  });

  it("네트워크 실패는 502로 안전하게 응답한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    expect(response.status).toBe(502);
    const text = await response.text();
    expect(text.length).toBeGreaterThan(0);
  });

  it("linked_file_id 쿼리를 URL-encode해서 업스트림에 그대로 전달한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("file-bytes", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0?linked_file_id=file with space"),
      context("mail-1", "0"),
    );

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe(
      "http://127.0.0.1:8000/api/v1/mail/mail-1/attachments/0?linked_file_id=file%20with%20space",
    );
  });

  it("linked_file_id 이외의 임의 쿼리는 업스트림으로 전달하지 않는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("file-bytes", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      requestWithUrl(
        "http://localhost/api/mail/mail-1/attachments/0?linked_file_id=file-1&evil=http://attacker.example",
      ),
      context("mail-1", "0"),
    );

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe(
      "http://127.0.0.1:8000/api/v1/mail/mail-1/attachments/0?linked_file_id=file-1",
    );
  });

  it("linked_file_id가 없으면 쿼리 없이 그대로 요청한다(대기중 admin 미리보기)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("file-bytes", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0"),
      context("mail-1", "0"),
    );

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/mail-1/attachments/0");
  });

  it("지원하지 않는 id_encoding은 422로 거부하고 업스트림을 부르지 않는다", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(
      requestWithUrl("http://localhost/api/mail/mail-1/attachments/0?id_encoding=raw"),
      context("mail-1", "0"),
    );
    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("base64url marker와 linked_file_id를 함께 업스트림에 전달한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("file-bytes", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await GET(
      requestWithUrl("http://localhost/api/mail/token/attachments/0?id_encoding=base64url&linked_file_id=file-1"),
      context("token", "0"),
    );
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://127.0.0.1:8000/api/v1/mail/token/attachments/0?linked_file_id=file-1&id_encoding=base64url",
    );
  });
});
