import { useEffect, useMemo, useState } from "react";
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
  kind = "front",
  quality = 82,
  draggable,
  fallback = "E",
  allowGraphicalFallback = true,
  onImageError,
  onPermanentFailure,
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const coverCandidates = useMemo(() => Array.from(new Set([
    book?.front_cover_url,
    book?.cover_image_url,
    book?.cover_url,
    book?.thumbnail_url,
    ...(Array.isArray(book?.cover_candidates) ? book.cover_candidates.map((item) => (
      typeof item === "string" ? item : item?.url
    )) : []),
  ].filter((value) => typeof value === "string" && value.trim()))), [book]);
  const activeCover = coverCandidates[candidateIndex] || "";
  const candidateBook = activeCover
    ? { ...book, front_cover_url: activeCover, cover_image_url: activeCover, cover_url: activeCover, thumbnail_url: activeCover }
    : book;
  const intrinsicHeight = height || Math.round(Number(width || 420) * 4 / 3);
  const sources = allowGraphicalFallback
    ? bookCoverImageSources(candidateBook, { width, widths, quality, forceFallback: failed, kind })
    : failed
      ? { src: "", srcSet: "", placeholder: "", backgroundColor: "", hasCover: false }
      : bookCoverImageSources(candidateBook, { width, widths, quality, kind });
  const showImage = Boolean(sources.hasCover && (allowGraphicalFallback || !sources.isFallback));
  useEffect(() => {
    if (!allowGraphicalFallback && !failed && !sources.hasCover) {
      setFailed(true);
      onImageError?.(book);
      onPermanentFailure?.(book);
    }
  }, [allowGraphicalFallback, book, failed, onImageError, onPermanentFailure, sources.hasCover]);
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
          onError={() => {
            setLoaded(false);
            if (candidateIndex < coverCandidates.length - 1) {
              setCandidateIndex((current) => current + 1);
              return;
            }
            setFailed(true);
            onImageError?.(book);
            onPermanentFailure?.(book);
          }}
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
