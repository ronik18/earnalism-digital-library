import { ArrowUpRight, BookOpen, Clock3, Headphones, LibraryBig, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ExperienceBottomNavigation from "../experiences-v2/shared/ExperienceBottomNavigation";
import ExperienceShell from "../experiences-v2/shared/ExperienceShell";
import "./MyLibrary.css";

export default function MyLibrary() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const accountName = user?.name || "My Library";

  return (
    <ExperienceShell className="my-library-v2" labelledBy="my-library-title">
      <section className="my-library-v2__content" data-testid="my-library-mobile">
        <header className="my-library-v2__hero">
          <p className="my-library-v2__eyebrow">{accountName}</p>
          <h1 id="my-library-title">My Library</h1>
          <p className="my-library-v2__introduction">A calm place for the reading life your account can support today.</p>
        </header>

        <div className="my-library-v2__availability" aria-label="Library availability">
          <div><BookOpen size={16} aria-hidden="true" /><span><b>Books</b><small>Browse reader-ready editions</small></span></div>
          <div><Headphones size={16} aria-hidden="true" /><span><b>Listening</b><small>Available only when a title is released</small></span></div>
        </div>

        <div className="my-library-v2__layout">
          <section className="my-library-v2__empty" aria-live="polite" aria-labelledby="my-library-empty-title">
            <LibraryBig size={30} aria-hidden="true" />
            <p className="my-library-v2__section-kicker">Your shelf</p>
            <h2 id="my-library-empty-title">No saved titles to show.</h2>
            <p>This page doesn’t yet show saved books or reading progress. Explore the Library to choose your next read.</p>
            <Link to="/library?availability=reader-ready" data-testid="my-library-browse-ready">Browse reader-ready editions <ArrowUpRight size={15} aria-hidden="true" /></Link>
          </section>

          <aside className="my-library-v2__next" aria-labelledby="my-library-next-title">
            <p className="my-library-v2__section-kicker"><Sparkles size={14} aria-hidden="true" /> A considered next step</p>
            <h2 id="my-library-next-title">Find the right edition, then make time for it.</h2>
            <p>Browse with release status in view. When an edition needs more time, its next action will say so plainly.</p>
            <div className="my-library-v2__next-links">
              <Link to="/library">Explore the Library <ArrowUpRight size={14} aria-hidden="true" /></Link>
              <Link to="/pricing"><Clock3 size={14} aria-hidden="true" /> View Reading Passes</Link>
            </div>
          </aside>
        </div>
      </section>
      <ExperienceBottomNavigation active="library" onNavigate={(target) => {
        if (target === "home") navigate("/");
        if (target === "library") navigate("/library");
        if (target === "passes") navigate("/pricing");
        if (target === "profile") navigate("/account");
      }} />
    </ExperienceShell>
  );
}
