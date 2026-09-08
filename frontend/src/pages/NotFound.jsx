import { Link } from "react-router-dom";
import { ArrowRight, ChevronLeft } from "lucide-react";
import useSEO from "../hooks/useSEO";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

export default function NotFound() {
  useSEO({
    title: "Page not found - The Earnalism Digital Library",
    description: "This Earnalism page is no longer available.",
    robots: "noindex, nofollow",
  });

  return (
    <PublicPageFrame tone="quiet" className="error-route-page" testId="not-found-page">
      <section className="error-route-panel" aria-labelledby="not-found-title">
        <div className="error-route-panel__copy">
          <p className="error-route-panel__eyebrow">404 · Page unavailable</p>
          <h1 id="not-found-title">This page is not on the shelf.</h1>
          <p>The link may point to a removed book, an old reader route, or a page that has moved. The library remains available.</p>
          <nav className="error-route-panel__actions" aria-label="Page recovery options">
            <Link to="/library" data-testid="not-found-library-link">Browse Library <ArrowRight size={15} /></Link>
            <Link to="/" data-testid="not-found-home-link"><ChevronLeft size={15} strokeWidth={1.6} /> Home</Link>
          </nav>
        </div>
        <aside className="error-route-panel__note" aria-label="Recovery guidance">
          <span>THE READING DESK</span>
          <p>Return to a reader-ready title, or begin again from the library.</p>
        </aside>
      </section>
    </PublicPageFrame>
  );
}
