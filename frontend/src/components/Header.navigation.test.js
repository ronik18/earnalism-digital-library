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
    expect(styles).toContain(".premium-site-header .mobile-menu-overlay");
    expect(styles).toContain("inset: var(--site-header-height) 0 0;");
    expect(styles).not.toContain("height: 28rem;");
  });

  test("keeps the reference header readable and geometrically stable", () => {
    expect(styles).toContain("--premium-header-menu-size: calc((0.92rem + 2px) * 1.02);");
    expect(styles).toContain("--premium-header-cta-size: calc((0.98rem + 2px) * 1.02);");
    expect(styles).toContain("font-size: var(--premium-header-menu-size) !important;");
    expect(styles).toContain("font-size: var(--premium-header-cta-size);");
    expect(styles).toContain("calc((0.95vw + 2px) * 1.02)");
    expect(globalStyles).toContain("The wordmark may scale inside this rail; it must never resize the rail.");
    expect(globalStyles).toContain("--site-header-height: clamp(4.05rem, 5.85vw, 5.4rem);");
    expect(globalStyles).toContain("--site-header-height: 3.6rem;");
    expect(styles).toContain("max-width: min(34rem, 34vw);");
    expect(styles).toContain("transform: scale(1.3);");
    expect(styles).toContain("left: 35.5%;");
    expect(styles).toContain(".premium-site-header #mobile-menu a");
    expect(styles).toContain("font-synthesis: none;");
    expect(styles).toContain("justify-content: flex-end;");
    expect(styles).toContain("min-height: 2.75rem;");
    expect(styles).toContain("min-width: 7.25rem;");
    expect(styles).toContain("flex: 0 0 2.75rem;");
    expect(styles).toContain("@media (min-width: 1280px)");
    expect(styles).not.toContain("@media (min-width: 1024px) and (max-width: 1279px)");
  });
});
