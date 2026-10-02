const { publicMetadataKeys } = require("../lib/public-metadata-policy");
const { apiUrl, frontendUrl } = require("../utils/envGuard");
const { request, apiRequest, apiGet } = require("../utils/http");
const fixture = require("../fixtures/books.manifest.json");

const forbiddenPublicKeys = new Set([
  "password",
  "password_hash",
  "token",
  "secret",
  "reviewer",
  "source_url",
  "rights_metadata",
  "user_id",
  "email",
  "private_notes",
  "reviewer_comments",
]);


describe("Security, Privacy & Access Control", () => {
  test("public responses include baseline security headers", async () => {
    const response = await request(frontendUrl(), { skipBody: true });
    const headers = response.headers;
    expect(headers.get("x-content-type-options") || "").toMatch(/nosniff/i);
    expect(headers.get("referrer-policy") || "").toBeTruthy();
    expect(headers.get("permissions-policy") || "").toBeTruthy();
    const framePolicy = `${headers.get("content-security-policy") || ""} ${headers.get("x-frame-options") || ""}`;
    expect(framePolicy).toMatch(/frame-ancestors|deny|sameorigin/i);
    if (frontendUrl().startsWith("https://")) expect(headers.get("strict-transport-security") || "").toBeTruthy();
  });

  test("admin APIs require authentication", async () => {
    const response = await apiRequest("/admin/books", { skipBody: true });
    expect([401, 403]).toContain(response.status);
  });

  test("draft fixture slugs and internal fields are not public", async () => {
    for (const slug of fixture.draftOrPrivateSlugs) {
      expect([401, 403, 404]).toContain((await apiGet(`/books/${slug}`)).status);
    }
    const books = (await apiGet("/books")).data;
    const leakedKeys = publicMetadataKeys(books).filter((key) => forbiddenPublicKeys.has(key.toLowerCase()));
    expect(leakedKeys).toEqual([]);
  });

  test("authenticated API CORS is not wildcarded", async () => {
    const response = await request(`${apiUrl()}/admin/books`, {
      method: "OPTIONS",
      skipBody: true,
      headers: {
        Origin: "https://evil.example",
        "Access-Control-Request-Method": "GET",
      },
    });
    expect(response.headers.get("access-control-allow-origin") || "").not.toBe("*");
  });
});
