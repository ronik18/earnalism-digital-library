import { Fragment, useEffect, useId, useRef, useState } from "react";

const PAGE_SIZE = 10;

export default function LibraryBrowseShelf({ title, copy, books, renderBook }) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const gridRef = useRef(null);
  const pendingFocusIndex = useRef(null);
  const shelfId = useId().replace(/:/g, "");
  const headingId = `library-shelf-${shelfId}-heading`;
  const gridId = `library-shelf-${shelfId}-grid`;
  const shownCount = Math.min(visibleCount, books.length);
  const remainingCount = books.length - shownCount;
  const nextCount = Math.min(PAGE_SIZE, remainingCount);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
    pendingFocusIndex.current = null;
  }, [books]);

  useEffect(() => {
    if (pendingFocusIndex.current === null) return;
    const firstNewCard = gridRef.current?.children[pendingFocusIndex.current];
    pendingFocusIndex.current = null;
    firstNewCard?.querySelector("a[href]")?.focus();
  }, [visibleCount]);

  if (!books.length) return null;
  const showMore = () => {
    pendingFocusIndex.current = shownCount;
    setVisibleCount((current) => Math.min(current + PAGE_SIZE, books.length));
  };

  return <section className="reference-library-shelf" aria-labelledby={headingId}>
    <div className="reference-section-heading"><div><h2 id={headingId}>{title}</h2><p>{copy}</p></div><span className="reference-shelf-count">{remainingCount ? `Showing ${shownCount} of ${books.length}` : `${books.length} ${books.length === 1 ? "edition" : "editions"}`}</span></div>
    <div ref={gridRef} id={gridId} className="reference-library-grid">{books.slice(0, shownCount).map((book, index) => <Fragment key={book.slug || book.id || index}>{renderBook(book, index)}</Fragment>)}</div>
    {remainingCount ? <button type="button" className="reference-library-show-more" aria-label={`Show ${nextCount} more ${nextCount === 1 ? "edition" : "editions"} in ${title}`} aria-controls={gridId} onClick={showMore}>Show {nextCount} more</button> : null}
  </section>;
}
