import fs from "fs";
import path from "path";

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

describe("dark premium public-system contract", () => {
  const tokens = read("src/design-system/tokens.css");
  const styles = read("src/components/ReferencePublicPages.css");
  const header = read("src/components/Header.css");
  const footer = read("src/components/Footer.jsx");
  const legacyPages = read("src/design-system/pages.css");
  const commerce = read("src/components/ReferencePublicPages.jsx");
  const ctaContract = JSON.parse(read("../docs/product/public-cta-contract.json"));

  test("defines one shared dark token system", () => {
    expect(tokens).toContain("--burgundy-950: #17090E;");
    expect(tokens).toContain("--beige-100: #F6EAD7;");
    expect(tokens).toContain("--gold-400: #DFB85A;");
    expect(tokens).toContain("--public-page: var(--burgundy-950);");
    expect(tokens).toContain("--book-card-width-desktop: 10rem;");
    expect(tokens).toContain("--book-card-width-tablet: 9.25rem;");
    expect(tokens).toContain("--book-card-width-mobile: 8.25rem;");
    expect(footer).toContain('bg-[#240c14]');
  });

  test("keeps public interaction geometry accessible", () => {
    expect(styles).toContain("min-height:44px");
    expect(styles).toContain("outline:3px solid var(--reference-gold-soft)");
    expect(styles).toContain("reference-library-drawer");
    expect(styles).toContain("background:rgba(23,9,14,.72)");
    expect(styles).toContain("@media (prefers-reduced-motion:reduce)");
  });

  test("removes superseded green values from active public-surface sources", () => {
    const activePublicSources = [tokens, styles, header, footer, legacyPages].join("\n").toLowerCase();
    ["#07110f", "#0d1f19", "#13271f", "#172e25", "#091310", "#10221e", "#10251f", "#122019"].forEach((color) => {
      expect(activePublicSources).not.toContain(color);
    });
    expect(styles).not.toMatch(/background:\s*(?:#fff|white)(?:;|\})/i);
  });

  test("only emphasizes offers using configured recommendation fields", () => {
    expect(commerce).toContain("pack.recommended === true || pack.is_recommended === true");
    expect(commerce).not.toContain("Most Popular");
  });

  test("makes every declared CTA unique and specifies a functional destination", () => {
    const ids = ctaContract.ctas.map((cta) => cta.id);
    expect(ids).toHaveLength(27);
    expect(new Set(ids).size).toBe(ids.length);
    ctaContract.ctas.forEach((cta) => {
      expect(cta.destination).toBeTruthy();
      expect(cta.kind).not.toBe("no-op");
    });
    expect(ctaContract.rules.join(" ")).toContain("keyboard activation");
  });
});
