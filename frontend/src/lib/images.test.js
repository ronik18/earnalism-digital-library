import { imageUrlCandidates, normalizeImageUrl, optimizedImageUrl } from "./images";

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
});
