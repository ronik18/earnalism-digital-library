import { useState } from "react";
import { bookCoverImageSources } from "../lib/images";

const DEFAULT_SIZES = "(min-width: 1024px) 320px, (min-width: 640px) 44vw, 92vw";
const DEFAULT_WIDTHS = [320, 420, 560, 720];

function fallbackText(book, fallback = "E") {
  const title = typeof book?.title === "string" ? book.title.trim() : "";
  return title ? title.slice(0, 1) : fallback;
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
  quality = 82,
  draggable,
  fallback = "E",
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const sources = bookCoverImageSources(book, { width, widths, quality });
  const showImage = sources.hasCover && !failed;
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
          {fallbackText(book, fallback)}
        </span>
      )}
    </span>
  );
}
