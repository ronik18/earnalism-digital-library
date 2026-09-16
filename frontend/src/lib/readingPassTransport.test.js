/** @jest-environment node */
import http from "http";
import { runInThisContext } from "vm";
import axios from "axios";
import { USER_TOKEN_KEY } from "./api";
import {
  endReadingPassSession, getReadingPassConfig, getReadingPassDevices,
  getReadingPassManifest, getReadingPassPage, getReadingPassPosition,
  renewReadingPassLease, revokeReadingPassDevice, saveReadingPassAudioPosition,
  saveReadingPassPosition, startReadingPassAudioSession, startReadingPassSession,
} from "./readingPassApi";

// Exercise Axios's real HTTP transport against an intentionally stalled local
// server. Mocking axios.get/post would not prove requests can actually finish.
let server, origin, previousBase, previousFetch, nativeFetch, previousWindow, previousNavigator, previousStorage;
let route;
const sockets = new Set();
const requests = [];
const lease = { sessionId: "test-session", token: "test-lease", version: 1 };

beforeAll(async () => {
  previousBase = axios.defaults.baseURL;
  previousFetch = global.fetch;
  // Jest 27's Node sandbox omits the runtime's built-in fetch global.
  nativeFetch = previousFetch || runInThisContext("fetch");
  previousWindow = global.window;
  previousNavigator = global.navigator;
  previousStorage = global.localStorage;
  const values = new Map();
  global.localStorage = { getItem: (key) => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key), clear: () => values.clear() };
  global.navigator = { platform: "Test", userAgent: "Test browser" };
  server = http.createServer((req, res) => {
    requests.push(req.url);
    req.on("error", () => undefined);
    route?.(req, res);
  });
  server.on("connection", (socket) => { sockets.add(socket); socket.on("close", () => sockets.delete(socket)); });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  axios.defaults.baseURL = origin;
  global.window = { location: { origin, pathname: "/login", search: "", assign: jest.fn() } };
}, 10000);

beforeEach(() => { route = null; requests.length = 0; localStorage.clear(); });
afterEach(() => { for (const socket of sockets) socket.destroy(); global.fetch = previousFetch; });
afterAll(async () => {
  axios.defaults.baseURL = previousBase;
  global.fetch = previousFetch;
  global.window = previousWindow;
  global.navigator = previousNavigator;
  global.localStorage = previousStorage;
  for (const socket of sockets) socket.destroy();
  await new Promise((resolve) => server.close(resolve));
});

test("stalled session, settlement, position, and metadata requests all reject within a bounded deadline", async () => {
  const startedAt = Date.now();
  const operations = [
    getReadingPassManifest("test-book"), getReadingPassConfig(), getReadingPassDevices(),
    getReadingPassPosition({ contentType: "text", contentId: "test-book" }),
    revokeReadingPassDevice("test-device"),
    startReadingPassSession({ bookSlug: "test-book", pageIndex: 4 }),
    startReadingPassAudioSession({ bookSlug: "test-book" }),
    renewReadingPassLease({ lease, sequence: 1, active: true, idempotencyKey: "stable-heartbeat" }),
    endReadingPassSession(lease),
    saveReadingPassPosition({ bookSlug: "test-book", pageIndex: 4 }),
    saveReadingPassAudioPosition({ bookSlug: "test-book", positionSeconds: 12 }),
  ];
  const results = await Promise.allSettled(operations);
  expect(requests).toHaveLength(operations.length);
  expect(results.every((result) => result.status === "rejected" && result.reason.code === "ECONNABORTED")).toBe(true);
  expect(Date.now() - startedAt).toBeLessThan(19000);
  // No retry of an uncertain start/end/write is introduced by the transport.
  expect(requests.filter((url) => url.endsWith("/sessions/end"))).toHaveLength(1);
}, 22000);

test("a cancelled page request releases the real stalled transport", async () => {
  const controller = new AbortController();
  route = () => controller.abort();
  await expect(getReadingPassPage("test-book", 1, null, { signal: controller.signal })).rejects.toMatchObject({ code: "ERR_CANCELED" });
  expect(requests).toEqual(["/api/reading-pass/books/test-book/pages/1"]);
});

test("a 401 refresh whose response body stalls cannot hold settlement indefinitely", async () => {
  localStorage.setItem(USER_TOKEN_KEY, "old-test-token");
  // Keep the browser's root-relative URL contract while using real Node fetch.
  global.fetch = (url, options) => nativeFetch(new URL(url, origin), options);
  route = (req, res) => {
    if (req.url.endsWith("/users/refresh")) {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.write('{"token":'); // Headers arrive; the body deliberately never ends.
    } else {
      res.writeHead(401, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "Session expired" }));
    }
  };
  const startedAt = Date.now();
  await expect(endReadingPassSession(lease)).rejects.toMatchObject({ name: "AbortError" });
  expect(Date.now() - startedAt).toBeLessThan(11000);
  expect(requests).toEqual(["/api/reading-pass/sessions/end", "/api/users/refresh"]);
  // An expired access token plus a stalled refresh is not proof that the
  // refresh cookie is invalid. Keep the credential for an explicit retry.
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("old-test-token");
}, 13000);

test("a confirmed invalid refresh still clears the user credential and rejects the protected operation", async () => {
  localStorage.setItem(USER_TOKEN_KEY, "expired-test-token");
  global.fetch = (url, options) => nativeFetch(new URL(url, origin), options);
  route = (req, res) => {
    res.writeHead(401, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Session expired" }));
  };
  await expect(endReadingPassSession(lease)).rejects.toMatchObject({ response: { status: 401 } });
  expect(requests).toEqual(["/api/reading-pass/sessions/end", "/api/users/refresh"]);
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
});
