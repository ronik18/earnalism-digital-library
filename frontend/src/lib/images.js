export function optimizedImageUrl(src, { width = 900, quality = 82 } = {}) {
  if (!src || typeof src !== "string") return src;

  try {
    const url = new URL(src);
    if (url.hostname.includes("images.unsplash.com")) {
      url.searchParams.set("auto", "format");
      url.searchParams.set("fit", "crop");
      url.searchParams.set("w", String(width));
      url.searchParams.set("q", String(quality));
      return url.toString();
    }

    if (url.hostname.includes("res.cloudinary.com") && url.pathname.includes("/upload/")) {
      const transform = `f_auto,q_auto,c_limit,w_${width},dpr_auto`;
      url.pathname = url.pathname.replace("/upload/", `/upload/${transform}/`);
      return url.toString();
    }
  } catch {
    return src;
  }

  return src;
}
