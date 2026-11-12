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
  test("uses the transparent full-logo WebP with a transparent PNG fallback", () => {
    expect(componentSource).toContain('earnalism-brand-lockup-640.webp');
    expect(componentSource).toContain('earnalism-brand-lockup.png');
    expect(componentSource).not.toContain('earnalism-brand-video-light.gif');
    expect(componentSource).not.toContain('earnalism-brand-video-still.png');
    expect(fs.statSync(path.join(process.cwd(), 'public/assets/performance/earnalism-brand-lockup-640.webp')).size).toBeLessThan(100 * 1024);
    expect(componentSource).not.toMatch(/canvas|generated|ai-garbled|data:image/i);
  });

  test("renders the approved wordmark with the complete accessible brand label", () => {
    expect(componentSource).toContain('alt="Earnalism — Where Learning Becomes Earning"');
    expect(componentSource).toContain('width="520"');
    expect(componentSource).toContain('height="156"');
    expect(componentSource).toContain('BUNDLED_FALLBACK');
  });

  test("public header uses the one customer-shell lockup and exposes mobile search", () => {
    expect(headerSource).toContain('import EarnalismBrandLockup from "./EarnalismBrandLockup";');
    expect(headerSource).toContain('<EarnalismBrandLockup variant="desktop-header" />');
    expect(headerSource).toContain('data-testid="mobile-header-search"');
    expect(headerSource).toContain('data-testid="nav-search"');
  });
});
