import fs from "fs";
import path from "path";

const footerSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/Footer.jsx"),
  "utf8"
);

describe("Footer compact colophon", () => {
  test("removes the detached outer spacing and oversized legacy padding", () => {
    expect(footerSource).not.toContain("mt-24 sm:mt-32");
    expect(footerSource).not.toContain("py-14 sm:py-20");
    expect(footerSource).toContain("py-4 sm:py-8");
  });

  test("preserves core public routes and the canonical contact address", () => {
    ["/library", "/journal", "/about", "/contact"].forEach((route) => {
      expect(footerSource).toContain(`to="${route}"`);
    });
    expect(footerSource).toContain('const accountHref = user && typeof user === "object" ? "/account" : "/login"');
    expect(footerSource).toContain('sales@reoenterprise.org');
  });

  test("keeps premium public copy, copyright protection, and accessible navigation", () => {
    expect(footerSource).toContain("Timeless Bengali and English literature, made beautiful for every way you read and listen.");
    expect(footerSource).toContain("Return to beloved classics, discover a voice you have never forgotten");
    expect(footerSource).toContain('aria-labelledby="footer-explore-heading"');
    expect(footerSource).toContain("min-h-11");
    expect(footerSource).toContain('data-testid="footer-content-protection"');
  });
});
