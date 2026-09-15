import crypto from "crypto";
import fs from "fs";
import path from "path";

const root = process.cwd();
const repositoryRoot = path.resolve(root, "..");
const wordmarkSource = fs.readFileSync(path.join(root, "src/components/FooterWordmark.jsx"), "utf8");
const provenance = JSON.parse(fs.readFileSync(path.join(root, "public/assets/brand/earnalism-footer-wordmark-ivory.provenance.json"), "utf8"));
const digest = (file) => crypto.createHash("sha256").update(fs.readFileSync(path.join(repositoryRoot, file))).digest("hex");

describe("FooterWordmark", () => {
  test("uses the footer-only derivative as one accessible home link", () => {
    expect(wordmarkSource).toContain('to="/"');
    expect(wordmarkSource).toContain('aria-label="Earnalism home"');
    expect(wordmarkSource).toContain('alt=""');
    expect(wordmarkSource).toContain("earnalism-footer-wordmark-ivory.png");
    expect(wordmarkSource).not.toContain("earnalism-brand-lockup.png");
  });

  test("binds the derivative to the unchanged canonical source and exact pixels", () => {
    expect(provenance.source.path).toBe("frontend/public/assets/brand/earnalism-brand-lockup.png");
    expect(provenance.derivative.path).toBe("frontend/public/assets/brand/earnalism-footer-wordmark-ivory.png");
    expect(provenance.derivation.excluded).toEqual(["illustrated emblem", "embedded slogan", "embedded venture attribution"]);
    expect(digest(provenance.source.path)).toBe(provenance.source.sha256);
    expect(digest(provenance.derivative.path)).toBe(provenance.derivative.sha256);
  });
});
