import { bookCoverImageSources, imageUrlCandidates, normalizeImageUrl, optimizedImageUrl } from "./images";

describe("image URL helpers", () => {
  test("normalizes extensionless local assets without changing external URLs", () => {
    expect(normalizeImageUrl("assets/shelves/business")).toBe("/assets/shelves/business.jpg");
    expect(normalizeImageUrl("/assets/shelves/business?x=1")).toBe("/assets/shelves/business.jpg?x=1");
    expect(normalizeImageUrl("https://example.com/cover")).toBe("https://example.com/cover");
  });

  test("builds fallback candidates for local assets", () => {
    expect(imageUrlCandidates("assets/shelves/business")).toEqual([
      "/assets/shelves/business.jpg",
      "/assets/shelves/business.png",
      "/assets/shelves/business.webp",
      "/assets/shelves/business.jpeg",
      "/assets/shelves/business.gif",
    ]);
  });

  test("adds provider-native image transforms", () => {
    expect(optimizedImageUrl("https://images.unsplash.com/photo-123?foo=bar", { width: 720, quality: 80 }))
      .toContain("w=720");
    expect(optimizedImageUrl("https://res.cloudinary.com/demo/image/upload/v1/cover.png", { width: 420 }))
      .toContain("/upload/f_auto,q_auto,c_limit,w_420,dpr_auto/");
  });

  test("builds progressive book cover sources from cover metadata", () => {
    const sources = bookCoverImageSources({
      title: "Dracula",
      cover_image_url: "https://res.cloudinary.com/demo/image/upload/v1/cover.png",
      thumbnail_url: "https://res.cloudinary.com/demo/image/upload/c_fill,f_auto,h_450,q_auto,w_300/v1/cover",
      blur_placeholder: "https://res.cloudinary.com/demo/image/upload/c_fill,e_blur:2000,h_30,w_20/v1/cover",
      dominant_color: "#111A21",
    }, { widths: [320, 420] });

    expect(sources.src).toContain("w_300");
    expect(sources.srcSet).toContain("320w");
    expect(sources.srcSet).toContain("420w");
    expect(sources.placeholder).toContain("e_blur");
    expect(sources.backgroundColor).toBe("#111A21");
    expect(sources.hasCover).toBe(true);
  });

  test("uses local responsive derivatives when they are available", () => {
    const sources = bookCoverImageSources({
      title: "Dracula",
      cover_image_url: "/assets/books/dracula/dracula-front-cover.webp",
      thumbnail_url: "/assets/books/dracula/dracula-front-cover.webp",
    }, { widths: [220, 420], width: 220 });

    expect(sources.src).toBe("/assets/performance/dracula-front-cover-220.webp");
    expect(sources.srcSet).toContain("/assets/performance/dracula-front-cover-220.webp 220w");
    expect(sources.srcSet).toContain("/assets/performance/dracula-front-cover-420.webp 420w");
  });
});
