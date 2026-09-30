import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import useSEO from "../hooks/useSEO";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

/** Safe customer-facing response for a historical title whose current release is held. */
export default function UnavailableTitle({ title = "Dracula", slug = "dracula" }) {
  useSEO({
    title: `${title} unavailable - The Earnalism Digital Library`,
    description: `${title} is not currently available as a public Earnalism release.`,
    robots: "noindex, nofollow",
  });

  return (
    <PublicPageFrame tone="quiet" className="error-route-page" testId="unavailable-title-page">
      <section className="error-route-panel" aria-labelledby="unavailable-title-heading">
        <div className="error-route-panel__copy">
          <p className="error-route-panel__eyebrow">Public title unavailable</p>
          <h1 id="unavailable-title-heading">{title} is not currently available.</h1>
          <p>This title is not part of the current public release. Its reading and listening experiences are unavailable. We’ll update the Library if its release status changes.</p>
          <nav className="error-route-panel__actions" aria-label="Title recovery options">
            <Link to="/library" data-testid="unavailable-title-library-link">Browse Library <ArrowRight size={15} /></Link>
            <Link to={`/contact?interest=${encodeURIComponent(slug)}`} data-testid="unavailable-title-contact-link">Ask about title</Link>
          </nav>
        </div>
        <aside className="error-route-panel__note" aria-label="Release status">
          <span>RELEASE STATUS</span>
          <p>No book text, reader session, or audio is available from this page.</p>
        </aside>
      </section>
    </PublicPageFrame>
  );
}
