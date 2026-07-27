import fs from "fs";
import path from "path";

const rail = fs.readFileSync(path.join(process.cwd(), "src/components/PremiumListeningRail.jsx"), "utf8");
const home = fs.readFileSync(path.join(process.cwd(), "src/pages/Home.jsx"), "utf8");
const covers = fs.readFileSync(path.join(process.cwd(), "src/components/BookCoverImage.jsx"), "utf8");

describe("PremiumListeningRail Home contract", () => {
  test("mounts in Hero to Listening Rail to Collage order", () => {
    expect(home.indexOf("<PremiumHero")).toBeGreaterThan(-1);
    expect(home.indexOf("<PremiumListeningRail")).toBeGreaterThan(home.indexOf("<PremiumHero"));
    expect(home.indexOf("<CuratedShelfCollage")).toBeGreaterThan(home.indexOf("<PremiumListeningRail"));
  });

  test("uses the customer-facing listening copy and canonical route", () => {
    expect(rail).toContain("Stories ready to be heard.");
    expect(rail).toContain("Step into beautifully narrated classics, then continue reading at your own pace.");
    expect(rail).toContain("Explore all audiobooks");
    expect(rail).toContain("Listen in Reader");
    expect(rail).toContain("/library?audio=approved");
    expect(rail).not.toMatch(/autoplay|release gate|QA_PASSED|manifest|evidence/i);
  });

  test("promotes reserve cards after all canonical cover candidates fail", () => {
    expect(rail).toContain("reserveBooks");
    expect(rail).toContain("setFailedSlugs");
    expect(rail).toContain("onImageError");
    expect(covers).toContain("cover_candidates");
    expect(covers).toContain("onPermanentFailure");
  });
});
