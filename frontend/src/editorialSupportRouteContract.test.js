import fs from "fs";
import path from "path";

const source = (file) => fs.readFileSync(path.join(process.cwd(), file), "utf8");

describe("editorial and support route contract", () => {
  const journal = source("src/pages/Journal.jsx");
  const article = source("src/pages/JournalArticle.jsx");
  const contact = source("src/pages/Contact.jsx");
  const microStory = source("src/pages/MicroStoryLanding.jsx");
  const notFound = source("src/pages/NotFound.jsx");
  const vercel = source("vercel.json");
  const goneHandler = source("api/removed-content.js");
  const notFoundHandler = source("api/not-found.js");

  test("keeps the journal and article routes based on their real API data", () => {
    expect(journal).toContain('api.get("/blog"');
    expect(journal).toContain('canonicalPath: "/journal"');
    expect(journal).not.toContain("Issue 01");
    expect(article).toContain('api.get(`/blog/${slug}`');
    expect(article).toContain('api.get("/blog"');
    expect(article).toContain('canonicalPath: post ? "/journal/" + post.slug : undefined');
    expect(article).toContain('robots: postNotFound ? "noindex, nofollow" : "index, follow"');
  });

  test("preserves the existing contact endpoint and adds no pre-submit request", () => {
    expect(contact).toContain('api.post("/contact", form)');
    expect(contact).not.toContain("api.get(");
    expect(contact).toContain("CONTACT_EMAIL");
    expect(contact).toContain('canonicalPath: "/contact"');
  });

  test("keeps the locked public access contract in the active invitation", () => {
    expect(microStory).toContain("PUBLIC_ACCESS_COPY");
    expect(microStory).toContain("PUBLIC_PREVIEW_COPY");
    expect(microStory).toContain("READING_TIME_COPY");
    expect(microStory).not.toMatch(/chapter 1 free|first chapter free|free audiobook|free listening sample/i);
  });

  test("uses branded noindex handlers for unknown and tombstoned routes", () => {
    expect(notFound).toContain('robots: "noindex, nofollow"');
    expect(notFoundHandler).toContain("res.statusCode = 404");
    expect(notFoundHandler).toContain("X-Robots-Tag");
    expect(goneHandler).toContain("res.statusCode = statusCode");
    expect(goneHandler).toContain("renderBrandedStatusPage");
    expect(notFound).not.toContain("EarnalismBrandLockup");
    expect(vercel).toContain('"source": "/secure-reader-test"');
    expect(vercel).toContain('"destination": "/api/not-found"');
  });
});
