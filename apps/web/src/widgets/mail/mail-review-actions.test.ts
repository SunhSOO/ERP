import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { revalidatePathMock } = vi.hoisted(() => ({ revalidatePathMock: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath: revalidatePathMock }));

const cookieGetAll = vi.fn(() => [{ name: "lep_session", value: "test-session" }]);
vi.mock("next/headers", () => ({
  cookies: async () => ({ getAll: cookieGetAll }),
}));

import type { MailMessage } from "@lep/api-client";
import {
  approveMailAction,
  approveMailAttachmentsAction,
  dismissMailAction,
  promoteMailToNoteAction,
} from "@/src/shared/data/mail-review-actions";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function mail(overrides: Partial<MailMessage> = {}): MailMessage {
  return {
    id: "mail-1",
    sender_name: "발신자",
    sender_org: "조직",
    received_at: "2026-09-09T09:00:00Z",
    subject: "제목",
    body: "본문",
    classification: "unclassified",
    project_id: null,
    suggested_project_id: null,
    intent: null,
    confidence: null,
    milestone_code: null,
    note_id: null,
    handled: false,
    version: 0,
    approved_by: null,
    approved_at: null,
    can_review: true,
    attachments: [],
    ...overrides,
  };
}

beforeEach(() => {
  revalidatePathMock.mockReset();
  cookieGetAll.mockReturnValue([{ name: "lep_session", value: "test-session" }]);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("approveMailAction", () => {
  it("정확한 엔드포인트/본문/Idempotency-Key/쿠키를 보내고 재검증한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: mail({
          classification: "project",
          project_id: "target-project",
          version: 1,
          approved_by: "admin@example.com",
          approved_at: "2026-09-09T10:00:00Z",
          attachments: [
            {
              filename: "견적서.pdf",
              content_type: "application/pdf",
              size_bytes: 10,
              part_index: 0,
              linked_file_id: "file-9",
            },
          ],
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveMailAction(
      "review-project",
      "mail-1",
      "target-project",
      0,
      [{ part_index: 0, category: "report" }],
      "key-abc",
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/mail-1/approve");
    expect(init.method).toBe("POST");
    expect(init.headers["Idempotency-Key"]).toBe("key-abc");
    expect(init.headers.cookie).toBe("lep_session=test-session");
    expect(JSON.parse(init.body)).toEqual({
      project_id: "target-project",
      expected_version: 0,
      attachments: [{ part_index: 0, category: "report" }],
    });
    expect(result.ok).toBe(true);
    expect(result.message).toBe("메일을 승인하고 첨부 1개를 연결했습니다.");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/review-project/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/target-project/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/target-project/drive");
    expect(revalidatePathMock).toHaveBeenCalledWith("/home");
  });

  it("첨부 0개는 메일만 승인하는 유효한 선택이다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: mail({
          id: "m1",
          classification: "project",
          project_id: "p1",
          version: 1,
          approved_by: "admin@example.com",
          approved_at: "2026-09-09T10:00:00Z",
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveMailAction("p1", "m1", "p1", 0, [], "key-1");

    expect(JSON.parse(fetchMock.mock.calls[0][1].body).attachments).toEqual([]);
    expect(result.ok).toBe(true);
    expect(result.message).toBe("메일만 승인했습니다.");
  });

  it("409 충돌은 성공으로 표시하지 않고 재검증도 하지 않는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          code: "VERSION_CONFLICT",
          status: 409,
          title: "버전 충돌",
          detail: "다른 사용자가 먼저 처리했습니다.",
          trace_id: "trace-1",
        },
        409,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("conflict");
    expect(result.message).toBe("다른 사용자가 먼저 처리했습니다.");
    expect(result.traceId).toBe("trace-1");
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("백엔드 연결 실패는 오류로 처리하고 재검증하지 않는다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("HTTP 200이어도 data.id가 없거나 요청한 메일과 다르면 성공으로 보지 않고 재검증하지 않는다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ data: {} })));

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("HTTP 200에 다른 메일 id가 오면 성공으로 보지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ data: mail({ id: "other-mail" }) })),
    );

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
  });

  it("응답이 분류/대상 프로젝트가 요청과 다르면 성공으로 보지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          data: mail({
            classification: "project",
            project_id: "other-project",
            version: 1,
            approved_by: "admin@example.com",
            approved_at: "2026-09-09T10:00:00Z",
          }),
        }),
      ),
    );

    const result = await approveMailAction("p1", "m1", "target-project", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
  });

  it("응답 버전이 expected_version보다 크지 않으면 성공으로 보지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          data: mail({
            classification: "project",
            project_id: "target-project",
            version: 0,
            approved_by: "admin@example.com",
            approved_at: "2026-09-09T10:00:00Z",
          }),
        }),
      ),
    );

    const result = await approveMailAction("p1", "m1", "target-project", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
  });

  it("선택한 첨부에 linked_file_id가 없으면 성공으로 보지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          data: mail({
            classification: "project",
            project_id: "target-project",
            version: 1,
            approved_by: "admin@example.com",
            approved_at: "2026-09-09T10:00:00Z",
            attachments: [
              {
                filename: "견적서.pdf",
                content_type: "application/pdf",
                size_bytes: 10,
                part_index: 0,
                linked_file_id: null,
              },
            ],
          }),
        }),
      ),
    );

    const result = await approveMailAction(
      "p1",
      "m1",
      "target-project",
      0,
      [{ part_index: 0, category: "original" }],
      "key-1",
    );

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
  });

  it("오류 응답은 code/status/title이 모두 있는 ProblemDetails일 때만 detail/title을 쓰고, 임의 본문은 노출하지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ unexpected: { nested: "leak-me" }, message: "raw upstream" }, 500),
      ),
    );

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.message).not.toContain("leak-me");
    expect(result.message).not.toContain("raw upstream");
  });

  it("정확한 ProblemDetails 형태의 오류는 detail/trace_id를 그대로 보여준다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            type: "about:blank",
            title: "권한 없음",
            status: 403,
            code: "FORBIDDEN",
            detail: "이 메일을 승인할 권한이 없습니다.",
            trace_id: "trace-9",
          },
          403,
        ),
      ),
    );

    const result = await approveMailAction("p1", "m1", "p2", 0, [], "key-1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("forbidden");
    expect(result.message).toBe("이 메일을 승인할 권한이 없습니다.");
    expect(result.traceId).toBe("trace-9");
  });

  it("delimiter messageId를 base64url transport로 보낸다", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: { id: "mail with space/slash" } }));
    vi.stubGlobal("fetch", fetchMock);

    await approveMailAction("p1", "mail with space/slash", "p2", 0, [], "key-1");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/bWFpbCB3aXRoIHNwYWNlL3NsYXNo/approve?id_encoding=base64url");
  });
});

describe("dismissMailAction", () => {
  it("expected_version만 담아 dismiss 엔드포인트로 보내고 재검증한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ data: mail({ id: "m1", classification: "unrelated", version: 3 }) }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await dismissMailAction("p1", "m1", 2, "key-2");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/m1/dismiss");
    expect(JSON.parse(init.body)).toEqual({ expected_version: 2 });
    expect(init.headers["Idempotency-Key"]).toBe("key-2");
    expect(result.ok).toBe(true);
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p1/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/home");
  });

  it("messageId를 base64url transport로 dismiss 경로에 보낸다", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: mail({ id: "mail with space" }) }));
    vi.stubGlobal("fetch", fetchMock);

    await dismissMailAction("p1", "mail with space", 2, "key-2");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/bWFpbCB3aXRoIHNwYWNl/dismiss?id_encoding=base64url");
  });

  it("응답 분류가 unrelated가 아니거나 버전이 증가하지 않으면 성공으로 보지 않는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ data: mail({ id: "m1", classification: "unclassified", version: 3 }) }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const wrongState = await dismissMailAction("p1", "m1", 2, "key-2");
    expect(wrongState.ok).toBe(false);

    fetchMock.mockResolvedValue(
      jsonResponse({ data: mail({ id: "m1", classification: "unrelated", version: 2 }) }),
    );
    const staleVersion = await dismissMailAction("p1", "m1", 2, "key-2");
    expect(staleVersion.ok).toBe(false);
  });

  it("projectId를 encodeURIComponent로 감싸 재검증 경로를 만든다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ data: mail({ id: "m1", classification: "unrelated", version: 3 }) }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await dismissMailAction("p with space", "m1", 2, "key-2");

    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p%20with%20space/mail");
  });
});

describe("approveMailAttachmentsAction", () => {
  it("최소 1개 선택을 요구하고 백엔드를 부르지 않는다", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveMailAttachmentsAction("p1", "m1", 1, [], "key-3");

    expect(result.ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("대상 프로젝트를 바꾸지 않고 선택한 첨부만 연결 요청에 담는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: mail({
          id: "m1",
          classification: "project",
          project_id: "p1",
          version: 2,
          approved_by: "admin@example.com",
          approved_at: "2026-09-09T10:00:00Z",
          attachments: [
            {
              filename: "설계도.zip",
              content_type: "application/zip",
              size_bytes: 20,
              part_index: 2,
              linked_file_id: "file-2",
            },
          ],
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveMailAttachmentsAction(
      "p1",
      "m1",
      1,
      [{ part_index: 2, category: "source" }],
      "key-4",
    );

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/m1/attachments/approve");
    expect(JSON.parse(init.body)).toEqual({
      expected_version: 1,
      attachments: [{ part_index: 2, category: "source" }],
    });
    expect(init.headers["Idempotency-Key"]).toBe("key-4");
    expect(result.ok).toBe(true);
    expect(result.message).toBe("첨부 1개를 새로 연결했습니다.");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p1/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p1/drive");
  });

  it("messageId를 URL-encode해서 attachments/approve 경로 세그먼트로 보낸다", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: mail({ id: "mail with space" }) }));
    vi.stubGlobal("fetch", fetchMock);

    await approveMailAttachmentsAction(
      "p1",
      "mail with space",
      1,
      [{ part_index: 0, category: "original" }],
      "key-5",
    );

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe(
      "http://127.0.0.1:8000/api/v1/mail/bWFpbCB3aXRoIHNwYWNl/attachments/approve?id_encoding=base64url",
    );
  });

  it("응답 대상 프로젝트가 다르거나 새로 선택한 첨부에 linked_file_id가 없으면 성공으로 보지 않는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: mail({
          id: "m1",
          classification: "project",
          project_id: "other-project",
          version: 2,
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const wrongTarget = await approveMailAttachmentsAction(
      "p1",
      "m1",
      1,
      [{ part_index: 2, category: "source" }],
      "key-4",
    );
    expect(wrongTarget.ok).toBe(false);

    fetchMock.mockResolvedValue(
      jsonResponse({
        data: mail({
          id: "m1",
          classification: "project",
          project_id: "p1",
          version: 2,
          attachments: [
            {
              filename: "설계도.zip",
              content_type: "application/zip",
              size_bytes: 20,
              part_index: 2,
              linked_file_id: null,
            },
          ],
        }),
      }),
    );
    const missingLink = await approveMailAttachmentsAction(
      "p1",
      "m1",
      1,
      [{ part_index: 2, category: "source" }],
      "key-4",
    );
    expect(missingLink.ok).toBe(false);
  });

  it("projectId를 encodeURIComponent로 감싸 재검증 경로를 만든다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: mail({
          id: "m1",
          classification: "project",
          project_id: "p with space",
          version: 2,
          attachments: [
            {
              filename: "설계도.zip",
              content_type: "application/zip",
              size_bytes: 20,
              part_index: 2,
              linked_file_id: "file-2",
            },
          ],
        }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await approveMailAttachmentsAction(
      "p with space",
      "m1",
      1,
      [{ part_index: 2, category: "source" }],
      "key-4",
    );

    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p%20with%20space/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/p%20with%20space/drive");
  });
});

describe("promoteMailToNoteAction", () => {
  it("본문 없이 promote-to-note를 POST하고 note_id를 검증한 뒤 재검증한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ data: { note_id: "note-1" } }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await promoteMailToNoteAction("proj-1", "m1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/m1/promote-to-note");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(init.headers.cookie).toBe("lep_session=test-session");
    expect(result.ok).toBe(true);
    expect(result.message).toBe("볼트에 노트를 만들었습니다.");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/proj-1/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/proj-1/vault");
    expect(revalidatePathMock).toHaveBeenCalledWith("/home");
  });

  it("messageId는 base64url, projectId는 URL-encode한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ data: { note_id: "note-1" } }));
    vi.stubGlobal("fetch", fetchMock);

    await promoteMailToNoteAction("proj with space", "mail with space");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/v1/mail/bWFpbCB3aXRoIHNwYWNl/promote-to-note?id_encoding=base64url");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/proj%20with%20space/mail");
    expect(revalidatePathMock).toHaveBeenCalledWith("/projects/proj%20with%20space/vault");
  });

  it("note_id가 없거나 빈 문자열이면 성공으로 보지 않고 재검증하지 않는다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ data: { note_id: "" } })));

    const result = await promoteMailToNoteAction("proj-1", "m1");

    expect(result.ok).toBe(false);
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("승인되지 않은 메일이면 백엔드의 409/403을 그대로 오류로 전달한다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            type: "about:blank",
            title: "승인되지 않음",
            status: 409,
            code: "NOT_APPROVED",
            detail: "승인된 메일만 지식화할 수 있습니다.",
          },
          409,
        ),
      ),
    );

    const result = await promoteMailToNoteAction("proj-1", "m1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("conflict");
    expect(result.message).toBe("승인된 메일만 지식화할 수 있습니다.");
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("백엔드 연결 실패는 오류로 처리한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const result = await promoteMailToNoteAction("proj-1", "m1");

    expect(result.ok).toBe(false);
    expect(result.status).toBe("error");
  });
});
