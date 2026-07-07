import { ArrowRight, BookOpen, Headphones, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

const GATES = [
  {
    icon: ShieldCheck,
    title: "Rights and source clear",
    body: "Only legally safe editions move beyond curation.",
  },
  {
    icon: BookOpen,
    title: "Reader quality locked",
    body: "Clean manuscript, graceful typography, and verified navigation first.",
  },
  {
    icon: Headphones,
    title: "Audio held for proof",
    body: "Audiobooks stay private until sync, naturalness, and browser gates pass.",
  },
];

export default function ComingSoonBoard({ compact = false }) {
  return (
    <section
      className={`coming-soon-board-wrap ${compact ? "coming-soon-board-wrap--compact" : ""}`}
      data-testid="coming-soon-quality-board"
      aria-labelledby="coming-soon-quality-board-title"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-12">
        <div className="coming-soon-board">
          <div className="coming-soon-board__copy">
            <div className="coming-soon-board__eyebrow">
              <span aria-hidden="true" />
              Coming Soon - Quality Gate Active
            </div>
            <h2 id="coming-soon-quality-board-title" className="coming-soon-board__title">
              The full Earnalism atelier opens only after every title clears the benchmark.
            </h2>
            <p className="coming-soon-board__text">
              We are keeping the wider shelves in curation instead of spending on rushed production. Each book must clear rights evidence, sanitized content, premium rendering, audiobook sync, accessibility, and browser QA before it is released.
            </p>
            <div className="coming-soon-board__actions">
              <Link to="/library" className="btn-primary coming-soon-board__primary">
                View Controlled Shelf <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
              <a href="/#reading-circle" className="btn-secondary coming-soon-board__secondary">
                Follow Launch Updates
              </a>
            </div>
          </div>

          <aside className="coming-soon-board__panel" aria-label="Earnalism release safeguards">
            <div className="coming-soon-board__seal">
              <Sparkles size={18} strokeWidth={1.6} aria-hidden="true" />
              <span>Cost-safe curation</span>
            </div>
            <div className="coming-soon-board__meter" aria-hidden="true">
              <span />
            </div>
            <div className="coming-soon-board__gate-list">
              {GATES.map(({ icon: Icon, title, body }) => (
                <div className="coming-soon-board__gate" key={title}>
                  <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                  <div>
                    <h3>{title}</h3>
                    <p>{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
