import fs from "fs";
import path from "path";

const componentSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/BrandHeaderLogo.jsx"),
  "utf8"
);
const headerSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/Header.jsx"),
  "utf8"
);

describe("BrandHeaderLogo", () => {
  test("uses the approved bundled Earnalism wordmark asset", () => {
    expect(componentSource).toContain('earnalism-logo-text.png');
    expect(componentSource).not.toMatch(/earnalism-brand-lockup\.png/);
    expect(componentSource).not.toMatch(/canvas|generated|ai-garbled|data:image/i);
  });

  test("renders the approved wordmark with the complete accessible brand label", () => {
    expect(componentSource).toContain('aria-label="Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture"');
    expect(componentSource).toContain('className="brand-header-logo__wordmark-image"');
    expect(componentSource).toContain('alt="Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture"');
    expect(componentSource).toContain('data-testid="brand-header-logo-india-flag"');
  });

  test("keeps all three requested badge variants available", () => {
    expect(componentSource).toContain('exactFlag: "exact-flag"');
    expect(componentSource).toContain('tricolor: "tricolor"');
    expect(componentSource).toContain('none: "none"');
    expect(componentSource).toContain('data-compliance-status="owner-review-required"');
  });

  test("exact flag badge keeps a 3:2 vector shape and contains no inscription text", () => {
    expect(componentSource).toContain('viewBox="0 0 30 20"');
    expect(componentSource).not.toMatch(/<text\b/i);
  });

  test("default tricolor badge is a visible deterministic literary medallion", () => {
    expect(componentSource).toContain('viewBox="0 0 48 48"');
    expect(componentSource).toContain('id="tricolor-medallion"');
    expect(componentSource).toContain("brand-header-logo__badge--tricolor");
  });

  test("keeps badge variants available while allowing the public header to omit the badge", () => {
    expect(componentSource.match(/<TricolorLiteraryBadge \/>/g)).toHaveLength(1);
    expect(componentSource).toContain('data-logo-source="admin-setting"');
  });

  test("public header reuses the footer lockup without the obsolete badge component", () => {
    expect(headerSource).toContain('import BrandMark from "./BrandMark";');
    expect(headerSource).toContain('<BrandMark variant="footer" />');
    expect(headerSource).not.toContain("IndiaCraftBadge");
  });
});
