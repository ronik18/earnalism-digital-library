import axios from "axios";
import { USER_TOKEN_KEY } from "./api";
import { renewReadingPassLease } from "./readingPassApi";

beforeEach(() => localStorage.clear());
afterEach(() => jest.restoreAllMocks());

test("same-origin Reading Pass 401 refreshes the member token once and retries", async () => {
  localStorage.setItem(USER_TOKEN_KEY, "old-test-token");
  const previousFetch = global.fetch;
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ token: "new-test-token" }) });
  const adapter = jest.fn(async (config) => {
    if (config.headers.Authorization !== "Bearer new-test-token") {
      throw { config, response: { status: 401, data: { detail: { code: "AUTH_REQUIRED" } } } };
    }
    return { status: 200, data: { checked: true }, config, headers: {} };
  });
  try {
    const result = await axios.get("/api/reading-pass/books/test/pages/4", { adapter, headers: { Authorization: "Bearer old-test-token" } });
    expect(result.data.checked).toBe(true);
    expect(adapter).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("new-test-token");
  } finally { global.fetch = previousFetch; }
});

test("caller-supplied heartbeat identity survives retries unchanged", async () => {
  const post = jest.spyOn(axios, "post").mockResolvedValue({ data: { status: "Running" } });
  const request = { lease: { sessionId: "s", token: "opaque", version: 1 }, sequence: 1, active: true, idempotencyKey: "s:1:reader-v2" };
  await renewReadingPassLease(request); await renewReadingPassLease(request);
  expect(post.mock.calls[0][1]).toEqual(post.mock.calls[1][1]);
  expect(post.mock.calls[0][1].idempotency_key).toBe(request.idempotencyKey);
});
