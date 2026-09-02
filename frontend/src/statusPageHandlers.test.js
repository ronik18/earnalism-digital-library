import fs from "fs";
import path from "path";

const root = process.cwd();
const notFound = require("../api/not-found.js");
const removedContent = require("../api/removed-content.js");

function invoke(handler, request = {}) {
  const response = { headers: {}, body: "" };
  Object.defineProperty(response, "statusCode", { value: 200, writable: true, enumerable: true });
  handler(request, {
    set statusCode(value) { response.statusCode = value; },
    get statusCode() { return response.statusCode; },
    setHeader(key, value) { response.headers[key] = value; },
    end(value) { response.body = value; },
  });
  return response;
}

function expectSeamlessStatusDocument(response) {
  expect(response.headers["Content-Type"]).toBe("text/html; charset=utf-8");
  expect(response.headers["X-Robots-Tag"]).toBe("noindex, nofollow, noarchive");
  expect(response.body).toContain('data-testid="status-brand-masthead"');
  expect(response.body).toContain('src="/assets/brand/earnalism-brand-lockup.png"');
  expect(response.body).toContain('width="2400" height="720"');
  expect(response.body).toContain("status-page__masthead");
  expect(response.body).not.toContain("border-radius:20px");
  expect(response.body).not.toContain("0 18px 50px");
  expect(response.body).toContain('href="/library"');
  expect(response.body).toContain('href="/"');
}

describe("direct seamless-branded status pages", () => {
  test("the direct 404 keeps its HTTP, robot, and cache contract without a logo card", () => {
    const response = invoke(notFound, { query: {}, headers: {}, url: "/missing" });
    expect(response.statusCode).toBe(404);
    expect(response.headers["Cache-Control"]).toBe("public, max-age=300, s-maxage=3600");
    expectSeamlessStatusDocument(response);
    expect(response.body).toContain("404 · Page unavailable");
  });

  test("the authoritative tombstone stays a 410 with its existing cache contract", () => {
    const response = invoke(removedContent, { query: { path: "/product/patterned-wrap-dress" }, headers: {}, url: "/product/patterned-wrap-dress" });
    expect(response.statusCode).toBe(410);
    expect(response.headers["Cache-Control"]).toBe("public, max-age=3600, s-maxage=86400");
    expectSeamlessStatusDocument(response);
    expect(response.body).toContain("410 · Retired route");
  });

  test("a non-tombstoned removed-content request stays a 404 with 404 wording", () => {
    const response = invoke(removedContent, { query: { path: "/ordinary-stale-path" }, headers: {}, url: "/ordinary-stale-path" });
    expect(response.statusCode).toBe(404);
    expectSeamlessStatusDocument(response);
    expect(response.body).toContain("404 · Page unavailable");
    expect(response.body).not.toContain("404 · Retired route");
  });

  test("the hydrated React 404 retains one shared header and no inner lockup", () => {
    const page = fs.readFileSync(path.join(root, "src/pages/NotFound.jsx"), "utf8");
    const style = fs.readFileSync(path.join(root, "src/styles/editorial-support.css"), "utf8");
    expect(page).toContain("PublicPageFrame");
    expect(page).not.toContain("EarnalismBrandLockup");
    expect(page).toContain('robots: "noindex, nofollow"');
    expect(style).toContain(".error-route-page");
    expect(style).toMatch(/\.error-route-panel\s*\{[\s\S]*border:\s*0;/);
  });
});
