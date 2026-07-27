import { graphicalCoverFallbackDataUri, resolveBookCover } from "./bookCoverResolver";

describe("deterministic graphical cover fallbacks", () => {
  test("keeps missing production cover truth as fallback rather than a fake canonical URL", () => {
    const resolved = resolveBookCover({ slug: "devdas", title: "দেবদাস / Devdas" });

    expect(resolved.isFallback).toBe(true);
    expect(resolved.source).toBe("earnalism_graphical_fallback");
    expect(resolved.src).toMatch(/^data:image\/svg\+xml,/);
  });

  test("uses content-bound vector motifs for missing Bengali editions", () => {
    const devdas = graphicalCoverFallbackDataUri({ slug: "devdas", title: "দেবদাস / Devdas" });
    const pather = graphicalCoverFallbackDataUri({ slug: "pather-panchali", title: "পথের পাঁচালী / Pather Panchali" });

    expect(devdas).not.toBe(pather);
    expect(decodeURIComponent(devdas)).toContain("stroke-opacity=\"0.62\"");
    expect(decodeURIComponent(pather)).toContain("M122 920C260 782");
  });
});
