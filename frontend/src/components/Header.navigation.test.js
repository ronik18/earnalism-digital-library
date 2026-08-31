import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/Header.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/Header.css"), "utf8");
const globalStyles = fs.readFileSync(path.join(process.cwd(), "src/index.css"), "utf8");

describe("premium header navigation", () => {
  test("uses only valid application routes and approved library filters", () => {
    expect(source).toContain('{ to: "/library", label: "Library" }');
    expect(source).toContain('label: "Bengali Classics"');
    expect(source).toContain('label: "English Classics"');
    expect(source).toContain('{ to: "/library?availability=approved-audiobook", label: "Audiobooks" }');
    expect(source).toContain('{ to: "/pricing", label: "Reading Passes" }');
    expect(source).toContain('{ to: "/about", label: "About" }');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).not.toMatch(/href=["']#|to=["']#|javascript:/i);
  });

  test("uses Search plus Sign In or Account on desktop and retains the Library CTA in the mobile menu", () => {
    expect(source).toContain('data-testid="nav-search"');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).toContain('data-testid={isAuthed ? "nav-account" : "nav-sign-in"}');
    expect(source).not.toContain('data-testid="header-cta-library"');
    expect(source.match(/data-testid="header-cta-library"/g) || []).toHaveLength(0);
    expect(source).toContain('data-testid="mobile-header-search"');
    expect(source).toContain('data-testid="mobile-menu-toggle"');
    expect(source).toContain('data-testid="mobile-cta-library">Enter the Library');
    expect(source).toContain('className="mobile-menu-overlay__cta" data-testid="mobile-cta-library"');
    expect(source).toContain('data-testid={isAuthed ? "mobile-nav-account" : "mobile-nav-sign-in"}');
  });

  test("opens a full-height mobile dialog that contains focus and suppresses background interaction", () => {
    expect(source).toContain('role="dialog" aria-modal="true" aria-label="Primary navigation"');
    expect(source).toContain('element.setAttribute("inert", "")');
    expect(source).toContain('document.body.style.overflow = "hidden"');
    expect(source).toContain('event.key === "Escape"');
    expect(source).toContain('requestAnimationFrame(() => menuToggle?.focus());');
    expect(styles).toContain(".premium-site-header .mobile-menu-overlay");
    expect(styles).toContain("inset: var(--site-header-height) 0 0;");
    expect(styles).not.toContain("height: 28rem;");
  });

  test("uses one readable public-header contract instead of the obsolete tiny route cascade", () => {
    expect(styles).toContain("One route-neutral public-header contract");
    expect(styles).toContain("font-size: 0.9375rem !important;");
    expect(styles).toContain("line-height: 1.35;");
    expect(styles).toContain("min-height: 2.75rem;");
    expect(styles).toContain("min-width: 2.75rem;");
    expect(styles).toContain("height: 3px;");
    expect(styles).toContain("@media (min-width: 1280px)");
    expect(styles).toContain("--site-header-height: 5.5rem;");
    expect(styles).toContain("width: clamp(18rem, 20vw, 20rem);");
    expect(styles).toContain("background: var(--brand-lockup-paper, #fff9ee);");
    expect(styles).toContain("font: 600 1rem/1.35 var(--font-ui, Outfit, sans-serif);");
    expect(styles).toContain("min-height: 52px;");
    expect(styles).not.toContain("font-size: clamp(.56rem, .58vw, .66rem) !important;");
    expect(styles).not.toContain("font-size:.78rem !important;");
    expect(styles).not.toContain("--site-header-height: 2.8rem;");
    expect(globalStyles).toContain("--site-header-height: 3.6rem;");
  });
});
