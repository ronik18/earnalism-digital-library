import fs from "fs";
import path from "path";

const read = (file) => fs.readFileSync(path.join(process.cwd(), file), "utf8");

describe("public legal direct-route contract", () => {
  const app = read("src/App.js");
  const legalRenderer = read("src/pages/LegalPages.jsx");
  const legalPages = read("src/content/legalPolicies.json");
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
    expect(legalRenderer).toContain('canonicalPath="/privacy"');
    expect(legalRenderer).toContain('canonicalPath="/terms"');
    expect(legalRenderer).toContain('canonicalPath="/copyright"');
    expect(legalPages).toContain("free preview of pages 1–3");
    expect(legalPages).toContain("page 4 onward requires a valid Reading Pass entitlement");
    expect(legalPages).toContain("₹49 for 30 minutes");
    expect(legalRenderer).toContain('to="/contact?intent=rights"');
    expect(contact).toContain('api.post("/contact", form)');
    expect(legalPages).not.toContain("[OWNER INPUT REQUIRED");
  });

  test("analytics disclosure matches disabled optional measurement", () => {
    expect(html).not.toMatch(/posthog/i);
    expect(legalPages).toContain("Optional first-party journey analytics and Vercel Web Analytics are disabled for this launch.");
    expect(legalPages).toContain("We do not create optional analytics identifiers");
    expect(legalPages).toContain("We do not use advertising pixels.");
  });
});
