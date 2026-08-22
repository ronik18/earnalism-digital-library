import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Pricing.jsx"), "utf8");

describe("Commerce design contract", () => {
  test("binds current offers without fabricated popularity or term claims", () => {
    expect(source).toContain('api.get("/payments/offers")');
    expect(source).not.toContain('Promise.all([api.get("/payments/packs"), api.get("/payments/config")])');
    expect(source).toContain("p.label");
    expect(source).toContain("p.price_inr");
    expect(source).not.toContain("Most Popular");
    expect(source).not.toContain("7-Day");
  });
  test("keeps canonical preview and non-recurring product truth", () => {
    expect(source).toContain("Read the first 3 pages free");
    expect(source).toContain("No subscription or autorenewal");
  });
});
