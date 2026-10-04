import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import "./reader-opening.css";

export default function ReaderOpening({ book, failed = false, onRetry, onLibrary, onEscapeFocus, busy = false, embedded = false }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (failed) return undefined;
    const timer = setTimeout(() => setSlow(true), 2500);
    return () => clearTimeout(timer);
  }, [failed]);
  const Container = embedded ? "section" : "main";
  const title = book?.public_title || book?.display_title || book?.title;
  const author = book?.author || book?.author_name;
  return <Container className={`experience-v2 reader-opening${failed ? " reader-opening--failed" : ""}`} data-testid="reader-opening">
    <section className="reader-opening__composition" aria-label="Reader opening">
      <div className="reader-opening__book" aria-hidden="true">
        <div className="reader-opening__shadow" />
        <div className="reader-opening__cover reader-opening__cover--left" />
        <div className="reader-opening__cover reader-opening__cover--right" />
        <div className="reader-opening__leaf reader-opening__leaf--left"><span /><span /><span /><span /></div>
        <div className="reader-opening__leaf reader-opening__leaf--right"><span /><span /><span /><span /></div>
        <div className="reader-opening__gutter" />
      </div>
      <p className="reader-opening__eyebrow">THE EARNALISM READING ROOM</p>
      <h1 className="reader-opening__title">{failed ? "We couldn’t open this page." : title || "A world between the pages"}</h1>
      {!failed && author && <p className="reader-opening__author">by {author}</p>}
      {!failed && <p className="reader-opening__line">A quiet page, opening into another world.</p>}
      {!failed && <div className="reader-opening__progress" aria-hidden="true"><span /></div>}
      <p className="reader-opening__status" role={failed ? "alert" : "status"} aria-live="polite" aria-atomic="true">
        {failed ? "Please try again, or return to the Library." : <><span className="reader-opening__sr-only">{title ? `Opening ${title}. ` : "Opening reader. "}</span>{slow ? "Still preparing your page…" : "Opening your page…"}</>}
      </p>
      <div className="reader-opening__actions">
        {failed && <button className="reader-opening__retry" onClick={onRetry} type="button" disabled={busy}>Try again</button>}
        <button className="reader-opening__back" onClick={onLibrary} onFocus={() => onEscapeFocus?.(true)} onBlur={() => onEscapeFocus?.(false)} type="button" disabled={busy}><ArrowLeft size={15} aria-hidden="true" />{busy ? "Closing reader…" : "Back to Library"}</button>
      </div>
    </section>
  </Container>;
}
