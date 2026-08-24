import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/ReferencePublicPages.jsx"), "utf8");

describe("Reference public page surfaces", () => {
  test("keeps listening controls behind release truth", () => {
    expect(source).toContain('import { audiobookReleaseState } from "../lib/audioReleaseSafety"');
    expect(source).toContain("audio.canShowControls");
    expect(source).toContain("Only editions with approved listening access.");
    expect(source).toContain("Titles without approval show no listening action.");
  });

  test("uses the approved canonical preview and non-recurring pass language", () => {
    expect(source).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
    expect(source).toContain("First 3 pages are free on eligible titles");
    expect(source).toContain("No subscription or autorenewal");
    expect(source).not.toContain("Chapter 1 free");
    expect(source).not.toContain("Most Popular");
  });

  test("binds offer presentation to current configured offer fields", () => {
    expect(source).toContain("pack.price_inr");
    expect(source).toContain("pack.minutes");
    expect(source).toContain("pack.recommended === true || pack.is_recommended === true");
    expect(source).toContain("pack.gift_enabled === true || pack.kind === \"gift\"");
  });
});
