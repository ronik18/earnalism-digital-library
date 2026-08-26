import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Clock, ShieldCheck } from "lucide-react";
import useSEO from "../hooks/useSEO";
import PublicPageFrame from "../components/PublicPageFrame";
import { PUBLIC_ACCESS_COPY, PUBLIC_PREVIEW_COPY, READING_TIME_COPY } from "../lib/publicAccessCopy";

const READING_PATHS = [
  {
    title: "Find a reader-ready edition",
    tag: "Discover",
    body: "Browse Bengali and English classics that are available for the current release.",
  },
  {
    title: "Begin with the preview",
    tag: "Read",
    body: `${PUBLIC_PREVIEW_COPY}. The page boundary is defined by the edition, never by a chapter marker.`,
  },
  {
    title: "Continue when it matters",
    tag: "Return",
    body: `${READING_TIME_COPY} Choose a Reading Pass only when you want to continue.`,
  },
];

export default function MicroStoryLanding() {
  useSEO({
    title: "A Quiet Reading Invitation — Earnalism",
    description: "Find a reader-ready Earnalism edition, begin with the canonical preview, and continue with a Reading Pass when you choose.",
  });

  return (
    <PublicPageFrame tone="quiet" className="micro-story-page">
      <section className="micro-story-hero">
        <div className="micro-story-hero__copy">
          <p className="italic-eyebrow">A quiet way into the library</p>
          <h1>Begin with a story, then stay as long as it holds you.</h1>
          <p>{PUBLIC_ACCESS_COPY} Explore reader-ready editions before deciding whether to add time.</p>
          <Link
            to="/library?source=reading_invitation"
            className="btn-primary micro-story-hero__cta"
          >
            Explore the Library <ArrowRight size={15} />
          </Link>
        </div>
        <div className="micro-story-hero__panel" aria-label="Why start with a short preview">
          <div><Clock size={18} /> {READING_TIME_COPY}</div>
          <div><BookOpen size={18} /> {PUBLIC_PREVIEW_COPY}</div>
          <div><ShieldCheck size={18} /> No autorenewal</div>
        </div>
      </section>

      <section className="micro-story-grid" aria-label="Reading paths">
        {READING_PATHS.map((story, index) => (
          <article key={story.title} className="micro-story-card">
            <span>0{index + 1} · {story.tag}</span>
            <h2>{story.title}</h2>
            <p>{story.body}</p>
            <Link
              to={index === 2 ? "/pricing" : "/library"}
              className="micro-story-card__cta"
            >
              {index === 2 ? "View Reading Passes" : "Browse reader-ready editions"} <ArrowRight size={14} />
            </Link>
          </article>
        ))}
      </section>
    </PublicPageFrame>
  );
}
