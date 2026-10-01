import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/Header.jsx"), "utf8");
const navigation = fs.readFileSync(path.join(process.cwd(), "src/config/publicNavigation.js"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/Header.css"), "utf8");
const globalStyles = fs.readFileSync(path.join(process.cwd(), "src/index.css"), "utf8");

describe("premium header navigation", () => {
  test("uses only valid application routes and approved library filters", () => {
    expect(navigation).not.toContain("HOME_OPTION_B_NAV_ITEMS");
    expect(navigation).toContain('{ key: "home", to: "/", label: "Home" }');
    expect(navigation).toContain('{ key: "library", to: "/library", label: "Library" }');
    expect(navigation).toContain('{ key: "bengali", to: "/library?language=bn&availability=reader-ready", label: "Bengali Classics" }');
    expect(navigation).toContain('{ key: "english", to: "/library?language=en", label: "English Classics" }');
    expect(navigation).toContain('{ key: "audiobooks", to: "/library?availability=approved-audiobook", label: "Audiobooks" }');
    expect(navigation).toContain('{ key: "reading-pass", to: "/pricing", label: "Reading Pass" }');
    expect(navigation).toContain('{ key: "journal", to: "/journal", label: "Blog" }');
    expect(navigation).toContain('{ key: "about", to: "/about", label: "About" }');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).not.toMatch(/href=["']#|to=["']#|javascript:/i);
  });

  test("uses the canonical nav, one search interaction, and Sign In or Account", () => {
    expect(source).toContain('role="search" data-testid="nav-search"');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).toContain('data-testid={isAuthed ? "nav-account" : "nav-sign-in"}');
    expect(source).not.toContain('data-testid="header-cta-library"');
    expect(source.match(/data-testid="header-cta-library"/g) || []).toHaveLength(0);
    expect(source).toContain('data-testid="mobile-header-search"');
    expect(source).toContain("const navigationItems = PUBLIC_NAV_ITEMS;");
    expect(source).toContain("import { PUBLIC_NAV_ITEMS, isPublicNavItemActive }");
    expect(source).toContain('data-testid="mobile-menu-toggle"');
    expect(source).toContain("data-nav-key={n.key}");
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
    expect(styles).toContain("font-size: clamp(0.94rem, 1.08vw, 1.03rem) !important;");
    expect(styles).toContain("line-height: 1.35;");
    expect(styles).toContain("min-height: 2.75rem;");
    expect(styles).toContain("min-width: 2.75rem;");
    expect(styles).toContain("height: 3px;");
    expect(styles).toContain("@media (min-width: 1280px)");
    expect(styles).toContain("--site-header-height: 6.5rem;");
    expect(styles).toContain("width: var(--header-lockup-width);");
    expect(styles).toContain("--header-lockup-width: 18.75rem;");
    expect(styles).toContain("--header-lockup-width: min(15rem, calc(100vw - 8.5rem));");
    expect(styles).toContain("background: var(--brand-lockup-paper, #fff9ee);");
    expect(styles).toContain("font: 600 1rem/1.35 var(--font-ui, Outfit, sans-serif);");
    expect(styles).toContain("min-height: 52px;");
    expect(styles).not.toContain("font-size: clamp(.56rem, .58vw, .66rem) !important;");
    expect(styles).not.toContain("font-size:.78rem !important;");
    expect(styles).not.toContain("--site-header-height: 2.8rem;");
    expect(globalStyles).toContain("--site-header-height: 5rem;");
    expect(globalStyles).toContain("--site-header-height: 6rem;");
    expect(globalStyles).toContain("--site-header-height: 6.5rem;");
  });

  test("Home cannot override the shared header sizing and immersive routes reuse Header", () => {
    const homeStyles = fs.readFileSync(path.join(process.cwd(), "src/pages/HomeOptionB.css"), "utf8");
    const immersive = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/shared/ExperienceHeader.jsx"), "utf8");
    expect(homeStyles).not.toContain("premium-site-header--reference-home");
    expect(immersive).toContain("<Header onNavigatePath={onNavigatePath}");
  });

  test("owner header evidence covers Blog and applies the canonical shell assertions to immersive pages", () => {
    const evidence = fs.readFileSync(path.join(process.cwd(), "../scripts/capture_pr471_canonical_header_matrix.mjs"), "utf8");
    const labels = [...navigation.matchAll(/label: "([^"]+)"/g)].map((match) => match[1]);
    const expected = JSON.parse(evidence.match(/const navLabels = (\[[^;]+\]);/)[1]);
    expect(expected).toEqual(labels);
    expect(evidence).toContain('{ id: "journal", path: "/journal" }');
    expect(evidence).toContain('{ id: "journal-article", path: "/journal/how-reading-shapes-better-founders" }');
    expect(evidence).not.toContain('&& !["reader", "listener"].includes(routeInfo.id)');
    expect(evidence).not.toContain('viewport.width < 1280 || hasImmersiveHeader');
    expect(evidence).toContain('header[data-testid="site-header"]');
    expect(evidence).toContain('body = { likes: 0, comments: [] }');
  });

  test("keeps mobile social controls focusable, non-shrinking, and able to wrap", () => {
    expect(source).toContain('className="mobile-menu-overlay__social-link');
    expect(styles).toContain(".mobile-menu-overlay__socials");
    expect(styles).toContain("flex-wrap: wrap;");
    expect(styles).toContain("flex: 0 0 44px;");
    expect(styles).toContain("min-width: 44px;");
    expect(styles).toContain("min-height: 44px;");
  });
});
