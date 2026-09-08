import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Clock, ShieldCheck } from "lucide-react";
import useSEO from "../hooks/useSEO";
import PublicPageFrame from "../components/PublicPageFrame";
import { PUBLIC_ACCESS_COPY, PUBLIC_PREVIEW_COPY, READING_TIME_COPY } from "../lib/publicAccessCopy";
import "../styles/editorial-support.css";

const READING_PATHS = [
  {
    title: "Find a reader-ready edition",
    tag: "Discover",
    body: "Browse Bengali and English classics that are available for the current release.",
    to: "/library",
    cta: "Browse reader-ready editions",
  },
  {
    title: "Begin with the preview",
    tag: "Read",
    body: `${PUBLIC_PREVIEW_COPY}. The page boundary is defined by the edition, never by a chapter marker.`,
    to: "/library",
    cta: "Browse reader-ready editions",
  },
  {
    title: "Continue when it matters",
    tag: "Return",
    body: `${READING_TIME_COPY} Choose a Reading Pass only when you want to continue.`,
    to: "/pricing",
    cta: "View Reading Passes",
  },
];

export default function MicroStoryLanding() {
  useSEO({
    title: "A Quiet Reading Invitation — Earnalism",
    description: "Find a reader-ready Earnalism edition, begin with the canonical preview, and continue with a Reading Pass when you choose.",
    canonicalPath: "/micro-story",
  });

  return (
    <PublicPageFrame tone="quiet" className="micro-story-page">
      <section className="micro-story-hero" aria-labelledby="micro-story-title">
        <div className="micro-story-hero__copy">
          <p className="micro-story-hero__eyebrow">A quiet way into the library</p>
          <h1 id="micro-story-title">Begin with a story, then stay as long as it holds you.</h1>
          <p>{PUBLIC_ACCESS_COPY} Explore reader-ready editions before deciding whether to add Reading Pass time.</p>
          <div className="micro-story-hero__actions">
            <Link
              to="/library?source=reading_invitation"
              className="micro-story-action micro-story-action--primary"
              data-testid="micro-story-library-cta"
            >
              Explore the Library <ArrowRight size={15} />
            </Link>
            <p>Choose a title first. Reading time is only relevant when you decide to continue.</p>
          </div>
        </div>
        <aside className="micro-story-hero__aside" aria-label="What to expect before choosing a pass">
          <div className="micro-story-hero__folio" aria-hidden="true"><span>03</span><small>pages to begin</small></div>
          <div className="micro-story-hero__promises">
            <div><Clock size={18} /> {READING_TIME_COPY}</div>
            <div><BookOpen size={18} /> {PUBLIC_PREVIEW_COPY}</div>
            <div><ShieldCheck size={18} /> No auto-renewal</div>
          </div>
        </aside>
      </section>

      <section className="micro-story-paths" aria-labelledby="micro-story-paths-title">
        <div className="micro-story-paths__intro">
          <p>Three quiet steps</p>
          <h2 id="micro-story-paths-title">A reading invitation, not a promise you need to keep.</h2>
          <span>Every path keeps the edition, preview boundary, and next choice visible.</span>
        </div>
        <ol className="micro-story-grid" aria-label="Reading paths">
          {READING_PATHS.map((story, index) => (
            <li key={story.title}>
              <article className="micro-story-card">
                <span>0{index + 1} · {story.tag}</span>
                <h3>{story.title}</h3>
                <p>{story.body}</p>
                <Link
                  to={story.to}
                  className="micro-story-card__cta"
                  data-testid={`micro-story-path-${index + 1}`}
                >
                  {story.cta} <ArrowRight size={14} />
                </Link>
              </article>
            </li>
          ))}
        </ol>
      </section>
    </PublicPageFrame>
  );
}
