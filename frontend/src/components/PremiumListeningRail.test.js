import fs from "fs";
import path from "path";

const rail = fs.readFileSync(
  path.join(process.cwd(), "src/components/PremiumListeningRail.jsx"),
  "utf8",
);
const styles = fs.readFileSync(
  path.join(process.cwd(), "src/components/PremiumListeningRail.css"),
  "utf8",
);
const home = fs.readFileSync(
  path.join(process.cwd(), "src/pages/Home.jsx"),
  "utf8",
);
const covers = fs.readFileSync(
  path.join(process.cwd(), "src/components/BookCoverImage.jsx"),
  "utf8",
);

describe("PremiumListeningRail Home contract", () => {
  test("mounts in Hero to Listening Room to Collage order", () => {
    expect(home.indexOf("<PremiumHero")).toBeGreaterThan(-1);
    expect(home.indexOf("<PremiumListeningRail")).toBeGreaterThan(
      home.indexOf("<PremiumHero"),
    );
    expect(home.indexOf("<CuratedShelfCollage")).toBeGreaterThan(
      home.indexOf("<PremiumListeningRail"),
    );
    expect(home).toContain("loading={homeCurationLoading}");
    expect(home).toContain("error={homeCurationError}");
  });

  test("uses the compact customer-facing listening copy and canonical routes", () => {
    expect(rail).toContain("THE LISTENING ROOM");
    expect(rail).toContain("Literature, in a more intimate form.");
    expect(rail).toContain(
      "Curated performances with seamless read-along listening.",
    );
    expect(rail).toContain("Explore audiobooks");
    expect(rail).toContain("/library?audio=approved");
    expect(rail).not.toMatch(/autoplay|<audio|preload=/i);
  });

  test("art-directs the approved covers inside a restrained listening salon", () => {
    expect(rail).toContain("premium-listening-rail__salon");
    expect(rail).toContain("premium-listening-rail__resonance");
    expect(rail).toContain("CURATED LISTENING EDITIONS");
    expect(rail).toContain("Featured listening edition");
    expect(styles).toContain("radial-gradient");
    expect(styles).toContain("mix-blend-mode: soft-light");
    expect(styles).toContain("object-fit: cover");
  });

  test("renders only real progress and real metadata", () => {
    expect(rail).toContain("listening_progress_percent");
    expect(rail).toContain("progress_percent");
    expect(rail).toContain("book?.narrator");
    expect(rail).toContain("book?.audio_duration_ms");
    expect(rail).toContain("book?.highlight_sync_enabled === true");
    expect(rail).not.toMatch(/fake|sample progress|default narrator/i);
  });

  test("supports unavailable audio without exposing a play action", () => {
    expect(rail).toContain("audio_available === false");
    expect(rail).toContain("rights_restricted === true");
    expect(rail).toContain("Audio unavailable");
    expect(rail).toContain("View reader edition");
    expect(rail).toContain("available ? (");
  });

  test("keeps navigation keyboard accessible and boundary-aware", () => {
    expect(rail).toContain('aria-label="Previous audiobooks"');
    expect(rail).toContain('aria-label="Next audiobooks"');
    expect(rail).toContain("disabled={!scrollState.previous}");
    expect(rail).toContain("disabled={!scrollState.next}");
    expect(rail).toContain('event.key !== "ArrowLeft"');
    expect(rail).toContain('event.key !== "ArrowRight"');
    expect(rail).toContain("{ passive: true }");
  });

  test("uses a single responsive snap rail with reduced-motion support", () => {
    expect(styles).toContain("grid-auto-flow: column");
    expect(styles).toContain("scroll-snap-type: x mandatory");
    expect(styles).toContain("grid-auto-columns: min(86vw, 22rem)");
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).not.toMatch(/min-height:\s*100vh|height:\s*100vh/);
  });

  test("preserves cover recovery plus loading, empty, and error states", () => {
    expect(rail).toContain("reserveBooks");
    expect(rail).toContain("setFailedSlugs");
    expect(rail).toContain("onPermanentFailure");
    expect(rail).toContain('status === "loading"');
    expect(rail).toContain('status === "error"');
    expect(rail).toContain('? "empty"');
    expect(rail).toContain("More listening editions are being prepared.");
    expect(covers).toContain("cover_candidates");
    expect(covers).toContain("onPermanentFailure");
  });
});
