import { ArrowRight, BookOpen, Headphones, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import BookCoverImage from "./BookCoverImage";
import { DRACULA_FALLBACK_BOOK } from "../lib/controlledLaunch";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const ACTION_CARDS = [
  {
    icon: Sparkles,
      eyebrow: "Bengali classics",
      title: "Bengali Classics",
      body: "Village life, memory, reform, love, and the emotional landscape of Bengal.",
    cta: "Explore Bengali Library",
    to: "/library?language=bn&availability=reader-ready",
    event: "bengali_card_click",
    book: {
      slug: "bengali-classics-shelf",
      title: "Bengali Classics",
      author: "Earnalism",
      cover_image_url: "/assets/shelves/bengali-classics.jpg",
      back_cover_image_url: "/assets/shelves/bengali.jpg",
      dominant_color: "#24362E",
    },
  },
  {
    icon: BookOpen,
      eyebrow: "English classics",
      title: "English Classics",
      body: "Dark houses, divided minds, and mysteries that linger beyond the final page.",
    cta: "Read Dracula",
    to: "/reader/dracula",
    event: "english_card_click",
    book: DRACULA_FALLBACK_BOOK,
  },
  {
    icon: Headphones,
      eyebrow: "Selected listening",
      title: "Approved Audiobooks",
      body: "Beautifully narrated classics ready to read and hear in the Earnalism reading room.",
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
              Bengali classics, English classics, and selected listening rooms offer three calm ways into the collection.
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
                      Explore the collection at your own pace.
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>

          <aside className="coming-soon-board__panel" aria-label="Earnalism reading room principles">
            <div className="coming-soon-board__seal">
              <Sparkles size={18} strokeWidth={1.6} aria-hidden="true" />
              <span>Make room for wonder</span>
            </div>
            <div className="coming-soon-board__gate-list">
              <div className="coming-soon-board__gate">
                <BookOpen size={17} strokeWidth={1.55} aria-hidden="true" />
                <div>
                  <h3>Read at your pace</h3>
                  <p>Settle into carefully designed editions with room for a slower kind of attention.</p>
                </div>
              </div>
              <div className="coming-soon-board__gate">
                <Sparkles size={17} strokeWidth={1.55} aria-hidden="true" />
                <div>
                  <h3>Curated for discovery</h3>
                  <p>Follow a mood, a literary world, or a story that has stayed with readers for generations.</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
