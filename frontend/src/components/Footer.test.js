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
    expect(footerSource).toContain("py-5 sm:py-8");
  });

  test("uses one compact footer wordmark without a cream panel", () => {
    expect(footerSource).not.toContain('data-testid="footer-brand-paper-row"');
    expect(footerSource).not.toContain('data-testid="footer-brand-lockup"');
    expect(footerSource).not.toContain('EarnalismBrandLockup variant="footer"');
    expect(footerSource).not.toContain('bg-[#fff9ee]');
    expect(footerSource).toContain('import FooterWordmark from "./FooterWordmark"');
    expect(footerSource.match(/<FooterWordmark \/>/g)).toHaveLength(1);
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
    expect(footerSource).toContain('data-testid="footer-venture-attribution"');
    expect(footerSource).toContain("A Reo Enterprise Venture");
    expect(footerSource).toContain('aria-labelledby="footer-explore-heading"');
    expect(footerSource).toContain("min-h-11");
    expect(footerSource).toContain('data-testid="footer-content-protection"');
    expect(footerSource).toContain("Public-domain literary works and licensed source layers retain their own terms.");
    expect(footerSource).toContain('to="/copyright"');
    expect(footerSource).not.toContain("All rights reserved.");
  });

  test("mounts configured shared social controls without replacing the contact mailto", () => {
    expect(footerSource).toContain('import FooterSocialLinks from "./FooterSocialLinks"');
    expect(footerSource).toContain("const { social } = useSettings();");
    expect(footerSource).toContain("<FooterSocialLinks links={social} />");
    expect(footerSource).toContain('href={`mailto:${CONTACT_EMAIL}`}');
  });
});
