import fs from "fs";
import path from "path";

const read = (file) => fs.readFileSync(path.join(process.cwd(), file), "utf8");

describe("public legal direct-route contract", () => {
  const app = read("src/App.js");
  const legalPages = read("src/pages/LegalPages.jsx");
  const contact = read("src/pages/Contact.jsx");
  const vercel = JSON.parse(read("vercel.json"));
  const snapshots = read("scripts/generate-static-seo-snapshots.mjs");
  const html = read("public/index.html");

  test.each([
    ["/privacy", "Privacy"],
    ["/terms", "Terms"],
    ["/copyright", "CopyrightNotice"],
    ["/contact", "Contact"],
  ])("direct navigation to %s reaches its public React route", (route, component) => {
    expect(app).toContain(`<Route path="${route}" element={<${component} />} />`);
    expect(vercel.rewrites).toContainEqual({ source: route, destination: "/index.html" });
    expect(snapshots).toContain(`"${route}"`);
  });

  test("legal pages have real content and a working contact path", () => {
    expect(legalPages).toContain('canonicalPath="/privacy"');
    expect(legalPages).toContain('canonicalPath="/terms"');
    expect(legalPages).toContain('canonicalPath="/copyright"');
    expect(legalPages).toContain('to="/contact?intent=rights"');
    expect(contact).toContain('api.post("/contact", form)');
    expect(legalPages).not.toContain("[OWNER INPUT REQUIRED");
  });

  test("initial launch does not inject optional PostHog tracking", () => {
    expect(html).not.toMatch(/posthog/i);
    expect(legalPages).toContain("Optional launch analytics and advertising trackers are not enabled");
  });
});
