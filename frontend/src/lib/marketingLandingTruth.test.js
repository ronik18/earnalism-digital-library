import fs from "fs";
import path from "path";

function readSource(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

const useSeoSource = readSource("src/hooks/useSEO.js");
const aboutSource = readSource("src/pages/About.jsx");
const homeSource = readSource("src/pages/Home.jsx");
const pricingSource = readSource("src/pages/Pricing.jsx");
const contactSource = readSource("src/pages/Contact.jsx");
const shelfTwoSource = readSource("src/components/ShelfTwoSlideshow.jsx");
const controlledLaunchSource = readSource("src/lib/controlledLaunch.js");
const spotlightSource = readSource("src/components/ApprovedAudiobookSpotlight.jsx");
const marketingSources = [
  useSeoSource,
  aboutSource,
  homeSource,
  pricingSource,
  contactSource,
  shelfTwoSource,
  controlledLaunchSource,
].join("\n");

describe("MARKETING_LANDING release truth", () => {
  test("positions Earnalism as a Bengali and English library instead of Dracula-first", () => {
    expect(useSeoSource).toContain("Bengali and English digital library");
    expect(aboutSource).toContain("Bengali and English Digital Library");
    expect(aboutSource).toContain("Bengali and English classics");
    expect(aboutSource).not.toMatch(/Dracula-First|beginning with Dracula|Dracula is live first/i);
    expect(useSeoSource).not.toMatch(/beginning with Dracula/i);
  });

  test("keeps controlled-launch audio copy evidence-gated and not privately playable", () => {
    expect(controlledLaunchSource).toContain("Audio availability remains evidence-gated");
    expect(controlledLaunchSource).toContain("audiobook_enabled: false");
    expect(controlledLaunchSource).not.toMatch(/audiobook experience in private review/i);
  });

  test("uses one production-facing contact domain across marketing pages", () => {
    expect(contactSource).toContain("sales@reoenterprise.org");
    expect(pricingSource).toContain("sales@reoenterprise.org");
    expect(marketingSources).not.toMatch(/sales@reoenterprise\.in|support@theearnalism\.org|theearnalism\.org/i);
  });

  test("does not present a fake Notify Me action", () => {
    expect(shelfTwoSource).toContain("Request Update");
    expect(shelfTwoSource).toContain("/contact?interest=");
    expect(shelfTwoSource).not.toContain("Notify Me");
    expect(shelfTwoSource).not.toMatch(/preventDefault\(\)/);
  });

  test("does not leak unapproved audiobook marketing claims or audio metadata", () => {
    expect(marketingSources).not.toMatch(/AudioObject|word-level|word level|word sync|speechSynthesis|SpeechSynthesisUtterance|\/audio\//i);
    expect(marketingSources).not.toMatch(/paid Listen|listen to every book|all classics in audio/i);
    expect(marketingSources).not.toMatch(/a-ghost-story.*Listen|pather-panchali.*audiobook|bn-066.*audiobook/i);
  });

  test("keeps the approved audiobook spotlight fail-closed behind release evidence", () => {
    expect(spotlightSource).toContain("audiobookReleaseState");
    expect(spotlightSource).toContain("if (!book) return null");
    expect(spotlightSource).toContain("if (!audioState.canShowControls) return null");
    expect(spotlightSource).toContain("Listen where the release gate is already proven.");
  });
});
