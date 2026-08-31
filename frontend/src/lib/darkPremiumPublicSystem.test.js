import fs from "fs";
import path from "path";

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

describe("dark premium public-system contract", () => {
  const tokens = read("src/design-system/tokens.css");
  const styles = read("src/components/ReferencePublicPages.css");
  const footer = read("src/components/Footer.jsx");
  const commerce = read("src/components/ReferencePublicPages.jsx");
  const ctaContract = JSON.parse(read("../docs/product/public-cta-contract.json"));

  test("defines one shared dark token system", () => {
    expect(tokens).toContain("--public-page: #07110f;");
    expect(tokens).toContain("--public-surface: #0d1f19;");
    expect(tokens).toContain("--public-surface-elevated: #13271f;");
    expect(tokens).toContain("--public-text: #fff8e9;");
    expect(tokens).toContain("--public-gold: #d6ad55;");
    expect(tokens).toContain("--book-card-width-desktop: 10rem;");
    expect(tokens).toContain("--book-card-width-tablet: 9.25rem;");
    expect(tokens).toContain("--book-card-width-mobile: 8.25rem;");
    expect(footer).toContain('bg-[#0d1f19]');
  });

  test("keeps public interaction geometry accessible", () => {
    expect(styles).toContain("min-height:44px");
    expect(styles).toContain("outline:3px solid var(--reference-gold-soft)");
    expect(styles).toContain("reference-library-drawer");
    expect(styles).toContain("background:rgba(1,7,5,.72)");
    expect(styles).toContain("@media (prefers-reduced-motion:reduce)");
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
