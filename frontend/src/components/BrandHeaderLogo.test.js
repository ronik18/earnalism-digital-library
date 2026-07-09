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
  test("uses the existing bundled Earnalism icon asset unchanged", () => {
    expect(componentSource).toMatch(/earnalism-logo-transparent-96\.webp/);
    expect(componentSource).toMatch(/earnalism-logo-transparent-128\.webp/);
    expect(componentSource).not.toMatch(/canvas|generated|ai-garbled|data:image/i);
  });

  test("renders deterministic proofreader wordmark text with accessible LEarnalism label", () => {
    expect(componentSource).toContain('aria-label="LEarnalism — Where Learning Becomes Earning"');
    expect(componentSource).toContain("Earnalism");
    expect(componentSource).toContain("brand-header-logo__inserted-l");
    expect(componentSource).toContain("brand-header-logo__caret");
    expect(componentSource).toContain("Where Learning Becomes Earning");
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

  test("public header uses the safer tricolor variant by default", () => {
    expect(headerSource).toContain("BrandHeaderLogo");
    expect(headerSource).toContain('badgeVariant="tricolor"');
    expect(headerSource).not.toContain("IndiaCraftBadge");
  });
});
