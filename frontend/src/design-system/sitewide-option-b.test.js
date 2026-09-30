const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const shell = fs.readFileSync(path.join(root, "components/Layout.jsx"), "utf8");
const styles = fs.readFileSync(path.join(__dirname, "sitewide-option-b.css"), "utf8");
const tokens = fs.readFileSync(path.join(__dirname, "tokens.css"), "utf8");

describe("sitewide Option B control and card primitives", () => {
  test("standard customer routes opt into the shared public shell", () => {
    expect(shell).toContain("layout--sitewide-option-b");
  });

  test("primary and secondary actions share the 44px control geometry and Option B radius", () => {
    expect(styles).toMatch(/\.layout--sitewide-option-b :is\([\s\S]*?\.btn-primary,[\s\S]*?\.rp-button,[\s\S]*?\.journal-v2__primary-link[\s\S]*?\)\s*\{[^}]*min-height:\s*44px;[^}]*border-radius:\s*var\(--optionb-radius-control\)/s);
    expect(styles).toMatch(/\.layout--sitewide-option-b :is\([^)]*\.reference-button[^)]*\.rp-button[^)]*\):focus-visible\s*\{[^}]*outline:\s*3px solid var\(--optionb-gold\)/s);
  });

  test("book, editorial, offer, account, and information cards share surface edges", () => {
    expect(styles).toMatch(/\.reference-home__discovery-card,[\s\S]*?\.reference-book-tile__cover,[\s\S]*?\.editorial-article-card,[\s\S]*?\.reference-offer,[\s\S]*?\.rp-offer,[\s\S]*?\.account-panel,[\s\S]*?\.auth-account-auth-card,[\s\S]*?\.error-route-panel/);
    expect(styles).toMatch(/border-radius:\s*var\(--optionb-radius-surface\);\s*box-shadow:\s*none;/);
  });

  test("shared surfaces use approved control and card radius tokens", () => {
    expect(tokens).toContain("--optionb-radius-control: 0.3rem;");
    expect(tokens).toContain("--optionb-radius-surface: 0.55rem;");
  });

  test("BookDetail availability badges retain readable ink on cream", () => {
    expect(styles).toMatch(/\.book-detail-page--reference \.book-detail-status-row span\s*\{[^}]*background:\s*#fffdf9;[^}]*color:\s*var\(--optionb-ink-muted\)/s);
  });
});
