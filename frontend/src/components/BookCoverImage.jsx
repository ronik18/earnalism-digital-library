import { useState } from "react";
import { bookCoverImageSources } from "../lib/images";

const DEFAULT_SIZES = "(min-width: 1024px) 320px, (min-width: 640px) 44vw, 92vw";
const DEFAULT_WIDTHS = [320, 420, 560, 720];

function fallbackText(book, fallback = "E") {
  const title = typeof book?.title === "string" ? book.title.trim() : "";
  return title ? title.slice(0, 1) : fallback;
}

function coverStatusLabel(book) {
  const status = String(book?.cover_status || book?.coverStatus || "").trim();
  if (status.includes("NO_SAFE_LOCAL_COVER")) return "Cover in preparation";
  if (status.includes("PIPELINE")) return "Pipeline edition";
  return "Earnalism shelf copy";
}

export default function BookCoverImage({
  book,
  alt,
  className = "",
  imgClassName = "",
  fallbackClassName = "",
  loading = "lazy",
  fetchPriority,
  sizes = DEFAULT_SIZES,
  widths = DEFAULT_WIDTHS,
  width = 420,
  height,
  quality = 82,
  draggable,
  fallback = "E",
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const intrinsicHeight = height || Math.round(Number(width || 420) * 4 / 3);
  const sources = bookCoverImageSources(book, { width, widths, quality, forceFallback: failed });
  const showImage = Boolean(sources.hasCover);
  const coverAlt = typeof alt === "string" ? alt : (book?.title || "Book cover");
  const style = sources.backgroundColor ? { backgroundColor: sources.backgroundColor } : undefined;
  const wrapperClass = [
    "book-cover-image",
    loaded ? "book-cover-image--loaded" : "",
    showImage ? "" : "book-cover-image--fallback",
    className,
  ].filter(Boolean).join(" ");

  return (
    <span className={wrapperClass} style={style}>
      {showImage && sources.placeholder && (
        <img
          src={sources.placeholder}
          alt=""
          aria-hidden="true"
          className="book-cover-image__placeholder"
          decoding="async"
          draggable={false}
        />
      )}
      {showImage ? (
        <img
          src={sources.src}
          srcSet={sources.srcSet || undefined}
          sizes={sources.srcSet ? sizes : undefined}
          alt={coverAlt}
          width={width}
          height={intrinsicHeight}
          loading={loading}
          fetchPriority={fetchPriority}
          decoding="async"
          className={`book-cover-image__img ${imgClassName}`.trim()}
          draggable={draggable}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : (
        <span className={`book-cover-image__fallback ${fallbackClassName}`.trim()}>
          <span className="book-cover-image__fallback-orb" aria-hidden="true" />
          <span className="book-cover-image__fallback-river" aria-hidden="true" />
          <span className="sr-only">{book?.title || fallbackText(book, fallback)} graphical cover fallback. {coverStatusLabel(book)}</span>
        </span>
      )}
    </span>
  );
}
