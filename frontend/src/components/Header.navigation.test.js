import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/Header.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/Header.css"), "utf8");

describe("premium header navigation", () => {
  test("uses only valid application routes and approved library filters", () => {
    expect(source).toContain('{ to: "/library", label: "Library" }');
    expect(source).toContain('label: "Bengali Classics"');
    expect(source).toContain('label: "English Classics"');
    expect(source).toContain('{ to: "/library?availability=approved-audiobook", label: "Audiobooks" }');
    expect(source).toContain('{ to: "/pricing", label: "Membership" }');
    expect(source).toContain('{ to: "/about", label: "About" }');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).not.toMatch(/href=["']#|to=["']#|javascript:/i);
  });

  test("uses a working library CTA on desktop and mobile", () => {
    expect(source).toContain('data-testid="header-cta-library">Start Reading');
    expect(source).toContain('data-testid="mobile-cta-library">Start Reading');
  });

  test("keeps the reference header readable and geometrically stable", () => {
    expect(styles).toContain("--premium-header-menu-size: calc(0.92rem + 2px);");
    expect(styles).toContain("--premium-header-cta-size: calc(0.98rem + 2px);");
    expect(styles).toContain("font-size: var(--premium-header-menu-size) !important;");
    expect(styles).toContain("font-size: var(--premium-header-cta-size);");
    expect(styles).toContain("calc(0.95vw + 2px)");
    expect(styles).toContain(".premium-site-header #mobile-menu a");
    expect(styles).toContain("font-synthesis: none;");
    expect(styles).toContain("justify-content: flex-end;");
    expect(styles).toContain("min-height: 2.75rem;");
    expect(styles).toContain("min-width: 9rem;");
    expect(styles).toContain("flex: 0 0 2.75rem;");
  });
});
