import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Clock, ShieldCheck } from "lucide-react";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const STORIES = [
  {
    title: "The Thirty-Minute Shelf",
    tag: "Workday pause",
    body: "A reader closes a noisy tab, opens a single chapter, and discovers the day still has one quiet corner left.",
  },
  {
    title: "One More Page",
    tag: "Evening reset",
    body: "The lamp is low, the phone is face down, and a short read turns the end of the day into something deliberate.",
  },
  {
    title: "The Borrowed Margin",
    tag: "Weekend note",
    body: "A sentence catches, a note is made, and ten spare minutes become the beginning of a better question.",
  },
];

export default function MicroStoryLanding() {
  useSEO({
    title: "3-Minute Stories — Earnalism",
    description: "Try a quiet 3-minute Earnalism preview, then start with the ₹49 Afternoon Pause reading pack.",
  });

  return (
    <div className="micro-story-page">
      <section className="micro-story-hero">
        <div className="micro-story-hero__copy">
          <p className="italic-eyebrow">Three minutes, no subscription</p>
          <h1>Start with a small read before you choose a longer stay.</h1>
          <p>
            Built for Instagram and YouTube visitors who want a low-risk first step:
            sample the tone, then unlock the ₹49 <em>Afternoon Pause</em>.
          </p>
          <Link
            to="/pricing?pack=30m&source=micro_story"
            className="btn-primary micro-story-hero__cta"
            onClick={() => trackFunnelEvent("micro_story_hero_cta_click", { pack_id: "30m", price_inr: 49 })}
          >
            Start with ₹49 <ArrowRight size={15} />
          </Link>
        </div>
        <div className="micro-story-hero__panel" aria-label="Why start with Afternoon Pause">
          <div><Clock size={18} /> 30 reading minutes</div>
          <div><BookOpen size={18} /> Enough for a first chapter</div>
          <div><ShieldCheck size={18} /> No autorenewal</div>
        </div>
      </section>

      <section className="micro-story-grid" aria-label="Three-minute story previews">
        {STORIES.map((story, index) => (
          <article key={story.title} className="micro-story-card">
            <span>0{index + 1} · {story.tag}</span>
            <h2>{story.title}</h2>
            <p>{story.body}</p>
            <Link
              to="/pricing?pack=30m&source=micro_story_card"
              className="micro-story-card__cta"
              onClick={() => trackFunnelEvent("micro_story_card_cta_click", { pack_id: "30m", story: story.title, price_inr: 49 })}
            >
              Continue with Afternoon Pause <ArrowRight size={14} />
            </Link>
          </article>
        ))}
      </section>
    </div>
  );
}
