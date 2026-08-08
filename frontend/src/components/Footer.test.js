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
    ["/library", "/journal", "/about", "/contact", "/login"].forEach((route) => {
      expect(footerSource).toContain(`to="${route}"`);
    });
    expect(footerSource).toContain('sales@reoenterprise.org');
  });

  test("keeps release truth, copyright protection, and accessible navigation", () => {
    expect(footerSource).toContain("Bengali and English classics, presented with quiet release truth.");
    expect(footerSource).toContain("Reader-ready classics stay visible; audiobooks appear only after evidence proves they are ready.");
    expect(footerSource).toContain('aria-labelledby="footer-explore-heading"');
    expect(footerSource).toContain("min-h-11");
    expect(footerSource).toContain('data-testid="footer-content-protection"');
  });
});
