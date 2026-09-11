import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const cookieGetAll = vi.fn(() => [{ name: "lep_session", value: "test-session" }]);
vi.mock("next/headers", () => ({
  cookies: async () => ({ getAll: cookieGetAll }),
}));

import {
  DRIVE_PAGE_SIZE,
  MAIL_PAGE_SIZE,
  fetchDriveFilesPage,
  fetchMailById,
  fetchMailCounts,
  fetchMailPage,
  mailOffset,
  normalizeDriveOffset,
  normalizeMailPage,
  normalizeMailStatus,
} from "@/src/shared/data/mail-review";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  cookieGetAll.mockReturnValue([{ name: "lep_session", value: "test-session" }]);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("normalizeMailStatus", () => {
  it("admin은 없거나 잘못된 값이면 unclassified로 되돌아간다", () => {
    expect(normalizeMailStatus(undefined, true)).toBe("unclassified");
    expect(normalizeMailStatus("bogus", true)).toBe("unclassified");
  });

  it("admin은 네 탭 모두 요청할 수 있다", () => {
    expect(normalizeMailStatus("project", true)).toBe("project");
    expect(normalizeMailStatus("unrelated", true)).toBe("unrelated");
    expect(normalizeMailStatus("all", true)).toBe("all");
  });

  it("nonadmin은 project 이외 값을 요청할 수 없다", () => {
    expect(normalizeMailStatus(undefined, false)).toBe("project");
    expect(normalizeMailStatus("unclassified", false)).toBe("project");
    expect(normalizeMailStatus("unrelated", false)).toBe("project");
    expect(normalizeMailStatus("all", false)).toBe("project");
    expect(normalizeMailStatus("project", false)).toBe("project");
  });
});

describe("normalizeMailPage", () => {
  it("1 미만이거나 정수가 아니면 1로 되돌아간다", () => {
    expect(normalizeMailPage(undefined)).toBe(1);
    expect(normalizeMailPage("0")).toBe(1);
    expect(normalizeMailPage("-3")).toBe(1);
    expect(normalizeMailPage("abc")).toBe(1);
    expect(normalizeMailPage("2.5")).toBe(1);
  });

  it("유효한 정수는 그대로 쓴다", () => {
    expect(normalizeMailPage("3")).toBe(3);
  });
});

describe("fetchMailPage", () => {
  it("offset/limit 쿼리와 세션 쿠키를 실어 목록 엔드포인트를 부른다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: true, total: 120 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchMailPage("proj-1", "project", 3);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(
      `http://127.0.0.1:8000/api/v1/projects/proj-1/mail?status=project&offset=${mailOffset(3)}&limit=${MAIL_PAGE_SIZE}`,
    );
    expect(init.headers.cookie).toBe("lep_session=test-session");
    expect(result).toEqual({ messages: [], total: 120, hasMore: true });
  });

  it("메시지 목록은 6단위 페이지 이동으로 offset/limit이 계산된다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: true, total: 120 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchMailPage("proj-1", "project", 3);

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("offset=12");
    expect(url).toContain("limit=6");
  });

  it("projectId를 encodeURIComponent로 감싼다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: false, total: 0 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchMailPage("proj with space", "project", 1);

    const [url] = fetchMock.mock.calls[0];
    expect(url.startsWith("http://127.0.0.1:8000/api/v1/projects/proj%20with%20space/mail?")).toBe(true);
  });
});

describe("fetchMailCounts", () => {
  it("counts 엔드포인트를 부르고 객체 data를 그대로 돌려준다", async () => {
    const counts = { unclassified: 2, project: 5, unrelated: 1, all: 8 };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: counts, meta: { trace_id: null } }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchMailCounts("proj-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/projects/proj-1/mail/counts",
      expect.any(Object),
    );
    expect(result).toEqual(counts);
  });

  it("projectId를 encodeURIComponent로 감싼다", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: {}, meta: { trace_id: null } }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchMailCounts("proj with space");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/projects/proj%20with%20space/mail/counts",
      expect.any(Object),
    );
  });
});

describe("mailOffset", () => {
  it("1쪽은 offset 0이다", () => {
    expect(mailOffset(1)).toBe(0);
  });

  it("2쪽부터는 페이지 크기만큼 밀린다", () => {
    expect(mailOffset(2)).toBe(MAIL_PAGE_SIZE);
  });
});

describe("mail page size", () => {
  it("메일 목록 크기는 6으로 고정된다", () => {
    expect(MAIL_PAGE_SIZE).toBe(6);
  });
});

describe("fetchMailById", () => {
  it("단건 조회 엔드포인트를 encodeURIComponent로 감싼 id로 부르고 data를 그대로 돌려준다", async () => {
    const message = { id: "mail with space", subject: "제목" };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ data: message, meta: { trace_id: null } }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchMailById("mail with space");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/mail/bWFpbCB3aXRoIHNwYWNl?id_encoding=base64url",
      expect.any(Object),
    );
    expect(result).toEqual(message);
  });

  it("delimiter UIDL은 base64url transport로 조회한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ data: { id: "uid/with?delim#hash" } }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchMailById("uid/with?delim#hash");
    expect(fetchMock.mock.calls[0][0]).toContain("/mail/dWlkL3dpdGg_ZGVsaW0jaGFzaA?id_encoding=base64url");
  });
});

describe("normalizeDriveOffset", () => {
  it("음수/정수 아님/없음은 0으로 되돌아간다", () => {
    expect(normalizeDriveOffset(undefined)).toBe(0);
    expect(normalizeDriveOffset("-5")).toBe(0);
    expect(normalizeDriveOffset("abc")).toBe(0);
    expect(normalizeDriveOffset("2.5")).toBe(0);
  });

  it("0 이상의 정수는 그대로 쓴다", () => {
    expect(normalizeDriveOffset("50")).toBe(50);
    expect(normalizeDriveOffset("0")).toBe(0);
  });
});

describe("fetchDriveFilesPage", () => {
  it("category/offset/limit 쿼리를 실어 부르고 meta.total/has_more를 그대로 돌려준다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: true, total: 120 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchDriveFilesPage("proj-1", "source", 50);

    expect(fetchMock).toHaveBeenCalledWith(
      `http://127.0.0.1:8000/api/v1/projects/proj-1/drive/files?category=source&offset=50&limit=${DRIVE_PAGE_SIZE}`,
      expect.any(Object),
    );
    expect(result).toEqual({ files: [], total: 120, hasMore: true });
  });

  it("category가 없으면 category 쿼리를 생략한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: false, total: 0 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDriveFilesPage("proj-1", undefined, 0);

    expect(fetchMock).toHaveBeenCalledWith(
      `http://127.0.0.1:8000/api/v1/projects/proj-1/drive/files?offset=0&limit=${DRIVE_PAGE_SIZE}`,
      expect.any(Object),
    );
  });

  it("projectId를 encodeURIComponent로 감싼다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        data: [],
        meta: { trace_id: null, next_cursor: null, has_more: false, total: 0 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDriveFilesPage("proj with space", undefined, 0);

    const [url] = fetchMock.mock.calls[0];
    expect(url.startsWith("http://127.0.0.1:8000/api/v1/projects/proj%20with%20space/drive/files?")).toBe(
      true,
    );
  });
});
