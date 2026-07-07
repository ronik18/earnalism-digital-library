import { ArrowRight, BookOpen, Headphones, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import { DRACULA_FALLBACK_BOOK } from "../lib/controlledLaunch";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const ACTION_CARDS = [
  {
    icon: Sparkles,
    eyebrow: "Reader-only live",
    title: "Bengali Classics",
    body: "A growing Bengali shelf presented as a complete reading experience: graphical covers, careful type, and audio hidden until every listening gate passes.",
    cta: "Explore Bengali Library",
    to: "/library?language=bn&availability=reader-ready",
    event: "bengali_card_click",
    book: {
      slug: "book-2b9853ec52",
      title: "দুই বিঘা জমি",
      author: "রবীন্দ্রনাথ ঠাকুর",
      cover_image_url: "/assets/shelves/bengali-classics.jpg",
      back_cover_image_url: "/assets/shelves/bengali.jpg",
      dominant_color: "#24362E",
    },
  },
  {
    icon: BookOpen,
    eyebrow: "English classics",
    title: "English Classics",
    body: "Bram Stoker's classic remains available as one polished reading tile, not the whole identity of the homepage.",
    cta: "Read Dracula",
    to: "/reader/dracula",
    event: "english_card_click",
    book: DRACULA_FALLBACK_BOOK,
  },
  {
    icon: Headphones,
    eyebrow: "Release-gated audio",
    title: "Approved Audiobooks",
    body: "Listening rooms appear only after endpoint, manifest, sync, QA, and browser evidence are present. Otherwise, audio stays private.",
    cta: "",
    to: "",
    event: "approved_audio_card_click",
    book: {
      slug: "approved-audiobooks",
      title: "Approved Audiobooks",
      author: "Earnalism",
      dominant_color: "#4A1C27",
    },
  },
];

export default function ComingSoonBoard({ compact = false }) {
  return (
    <section
      className={`coming-soon-board-wrap ${compact ? "coming-soon-board-wrap--compact" : ""}`}
      data-testid="curated-action-cards"
      aria-labelledby="curated-action-cards-title"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-12">
        <div className="coming-soon-board">
          <div className="coming-soon-board__intro">
            <div className="coming-soon-board__eyebrow">
              <span aria-hidden="true" />
              Three ways into the library
            </div>
            <h2 id="curated-action-cards-title" className="coming-soon-board__title">
              Choose a shelf without losing the quiet.
            </h2>
            <p className="coming-soon-board__text">
              Bengali reading, English classics, and listening releases each have a clear state. Reading is complete where approved; audio remains hidden until evidence makes it public.
            </p>
          </div>

          <div className="coming-soon-board__cards" aria-label="Curated homepage actions">
            {ACTION_CARDS.map(({ icon: Icon, eyebrow, title, body, cta, to, book, event }) => (
              <article className="coming-soon-board__card" key={title}>
                <BookCoverImage
                  book={book}
                  alt={`${title} graphical cover`}
                  className="coming-soon-board__cover"
                  width={220}
                  height={300}
                  sizes="(max-width: 767px) 34vw, 190px"
                />
                <div className="coming-soon-board__card-copy">
                  <div className="coming-soon-board__card-eyebrow">
                    <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                    <span>{eyebrow}</span>
                  </div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                  {to ? (
                    <Link
                      to={to}
                      className="coming-soon-board__card-link"
                      onClick={() => trackFunnelEvent(event, { surface: "home_action_card", title })}
                    >
                      {cta} <ArrowRight size={14} strokeWidth={1.7} />
                    </Link>
                  ) : (
                    <div className="coming-soon-board__card-gated" role="note">
                      Selected listening releases appear after quality gates pass.
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>

          <aside className="coming-soon-board__panel" aria-label="Earnalism release safeguards">
            <div className="coming-soon-board__seal">
              <ShieldCheck size={18} strokeWidth={1.6} aria-hidden="true" />
              <span>Release truth preserved</span>
            </div>
            <div className="coming-soon-board__gate-list">
              <div className="coming-soon-board__gate">
                <ShieldCheck size={17} strokeWidth={1.55} aria-hidden="true" />
                <div>
                  <h3>No unapproved audio</h3>
                  <p>Audiobook controls are earned by endpoint, manifest, sync, QA, and browser evidence.</p>
                </div>
              </div>
              <div className="coming-soon-board__gate">
                <BookOpen size={17} strokeWidth={1.55} aria-hidden="true" />
                <div>
                  <h3>Reader-first shelves</h3>
                  <p>Bengali and English classics remain premium even when audio stays hidden.</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
