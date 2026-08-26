import fs from "fs";
import path from "path";

const componentSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/EarnalismBrandLockup.jsx"),
  "utf8"
);
const headerSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/Header.jsx"),
  "utf8"
);

describe("EarnalismBrandLockup", () => {
  test("uses the approved bundled Earnalism lockup and no generated asset", () => {
    expect(componentSource).toContain('earnalism-brand-lockup.png');
    expect(componentSource).not.toMatch(/canvas|generated|ai-garbled|data:image/i);
  });

  test("renders the approved wordmark with the complete accessible brand label", () => {
    expect(componentSource).toContain('alt="The Earnalism — Read. Reflect. Remember."');
    expect(componentSource).toContain('width="2400"');
    expect(componentSource).toContain('height="720"');
    expect(componentSource).toContain('BUNDLED_FALLBACK');
  });

  test("public header uses the one customer-shell lockup and exposes mobile search", () => {
    expect(headerSource).toContain('import EarnalismBrandLockup from "./EarnalismBrandLockup";');
    expect(headerSource).toContain('<EarnalismBrandLockup variant="desktop-header" />');
    expect(headerSource).toContain('data-testid="mobile-header-search"');
    expect(headerSource).toContain('data-testid="nav-search"');
  });
});
