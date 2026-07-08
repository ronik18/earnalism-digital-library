import { Link } from "react-router-dom";
import { Clock } from "lucide-react";
import { memo } from "react";
import BookCoverImage from "./BookCoverImage";
import {
  DRACULA_CTA_EVENTS,
  LIVE_APPROVED_SLUG,
  bookLaunchStatus,
  canShowPreview,
  canShowReadingPass,
  canShowStartReading,
  notifyUrl,
  readingPassUrl,
} from "../lib/controlledLaunch";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";
import { libraryPresentationForBook } from "../lib/libraryCatalog";

function BookCard({ book, priority = false }) {
  const status = bookLaunchStatus(book);
  const isLiveApproved = status === "LIVE_APPROVED";
  const showPreview = canShowPreview(book);
  const showStartReading = canShowStartReading(book);
  const showReadingPass = canShowReadingPass(book);
  const isDracula = book.slug === LIVE_APPROVED_SLUG;
  const displayTitle = book.title_en || book.title;
  const secondaryTitle = book.title_en && book.title_en !== book.title ? book.title : "";
  const audioState = audiobookReleaseState(book);
  const presentation = libraryPresentationForBook(book);

  const track = (event, metadata = {}) => {
    trackFunnelEvent(event, { book: book.slug, book_slug: book.slug, ...metadata });
  };

  return (
    <div
      className={`card-elegant overflow-hidden flex flex-col group ${isLiveApproved ? "book-card--live" : "book-card--pipeline"}`}
      data-testid={`book-card-${book.slug}`}
      data-launch-status={status}
      data-cover-status={book.cover_status || ""}
    >
      <Link to={isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)} className="block aspect-[3/4] bg-ivory-warm overflow-hidden relative">
        <BookCoverImage
          book={book}
          alt={displayTitle}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          width={320}
          widths={[240, 320, 420]}
          quality={80}
          sizes="(min-width: 1024px) 300px, (min-width: 640px) 44vw, 92vw"
        />
      </Link>
      <div className="p-6 sm:p-7 flex flex-col gap-3 flex-1">
        <div className="book-card__badges" aria-label={`${displayTitle} availability`}>
          <span>{presentation.availabilityLabel}</span>
          <span>{presentation.languageLabel}</span>
          <span className={audioState.canShowControls ? "book-card__badge--audio-live" : "book-card__badge--audio-hidden"}>
            {presentation.audioBadgeLabel}
          </span>
        </div>
        <Link to={isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)} className="group/title">
          <h3 className="font-serif-display text-[1.12rem] sm:text-[1.22rem] text-burgundy leading-[1.24] group-hover/title:text-burgundy-soft transition-colors">{displayTitle}</h3>
        </Link>
        {secondaryTitle && (
          <p className="book-card__secondary-title">{secondaryTitle}</p>
        )}
        {book.author && (
          <p className="text-[0.78rem] tracking-[0.12em] uppercase text-charcoal-soft">by {book.author}</p>
        )}
        {book.short_description && (
          <p className="text-sm text-charcoal-soft leading-relaxed line-clamp-3 font-light">{book.short_description}</p>
        )}
        {book.estimated_reading_time && (
          <div className="inline-flex items-center gap-1.5 text-[0.72rem] tracking-[0.18em] uppercase text-gold-deep">
            <Clock size={12} strokeWidth={1.5} /> {book.estimated_reading_time}
          </div>
        )}
        <p className="book-card__availability-note">{presentation.availabilityNote}</p>
        {showPreview || showStartReading || audioState.canShowControls ? (
          <div className="mt-auto flex flex-col sm:flex-row gap-2 sm:gap-3 pt-5 border-t border-brand-soft">
            {showPreview && (
              <Link
                to={`/reader/${book.slug}`}
                className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase text-burgundy border border-[var(--brand-gold)] hover:bg-[var(--brand-gold)]/10 transition-colors"
                data-testid={`card-preview-${book.slug}`}
                onClick={() => {
                  track("book_card_read_click", { cta: "book_card_preview", release_state: status });
                  track(DRACULA_CTA_EVENTS.previewStart, { cta: "book_card_preview" });
                }}
              >
                {isDracula ? "Read Chapter 1" : "Read"}
              </Link>
            )}
            {audioState.canShowControls && (
              <Link
                to={`/reader/${book.slug}?listen=1`}
                className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase bg-[var(--brand-charcoal)] text-[var(--brand-ivory)] hover:bg-burgundy-deep transition-colors"
                data-testid={`card-listen-${book.slug}`}
                onClick={() => track("book_card_listen_click", { cta: "book_card_listen", release_state: audioState.status })}
              >
                Listen
              </Link>
            )}
            {showStartReading && showReadingPass && (
              <Link
                to={readingPassUrl("book_card")}
                className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase bg-burgundy text-[var(--brand-ivory)] hover:bg-burgundy-deep transition-colors"
                data-testid={`card-start-${book.slug}`}
                onClick={() => track(DRACULA_CTA_EVENTS.readingPass, { cta: "book_card_pass" })}
              >
                Reading Pass
              </Link>
            )}
            {showStartReading && !showReadingPass && (
              <Link
                to={`/book/${book.slug}`}
                className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase bg-burgundy text-[var(--brand-ivory)] hover:bg-burgundy-deep transition-colors"
                data-testid={`card-details-${book.slug}`}
                onClick={() => {
                  track("book_card_read_click", { cta: "book_card_details", release_state: status });
                  track(DRACULA_CTA_EVENTS.startReading, { cta: "book_card_details" });
                }}
              >
                Details
              </Link>
            )}
          </div>
        ) : (
          <div className="mt-auto pt-5 border-t border-brand-soft">
            <p className="text-xs leading-relaxed text-charcoal-soft">
              This title is in the rights-safe pipeline and is not readable or listenable yet.
            </p>
            <Link
              to={notifyUrl(book.slug)}
              className="mt-4 inline-flex w-full items-center justify-center px-3 py-2 rounded-full text-[0.68rem] tracking-[0.22em] uppercase text-burgundy border border-[var(--brand-gold)] hover:bg-[var(--brand-gold)]/10 transition-colors"
              data-testid={`card-notify-${book.slug}`}
              onClick={() => track(DRACULA_CTA_EVENTS.notifyMe, { future_title: book.slug })}
            >
              Request Update
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(BookCard);
