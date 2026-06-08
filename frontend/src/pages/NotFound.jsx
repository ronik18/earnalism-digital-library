import { Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import useSEO from "../hooks/useSEO";

export default function NotFound() {
  useSEO({
    title: "Page not found - The Earnalism Digital Library",
    description: "This Earnalism page is no longer available.",
    robots: "noindex, nofollow",
  });

  return (
    <section className="mx-auto flex min-h-[62vh] max-w-4xl flex-col items-center justify-center px-5 py-24 text-center" data-testid="not-found-page">
      <div className="italic-eyebrow mb-4">Page unavailable</div>
      <h1 className="font-serif-light text-4xl leading-tight text-burgundy sm:text-5xl">
        This page is no longer on the shelf.
      </h1>
      <p className="mt-6 max-w-xl text-charcoal-soft leading-relaxed">
        The link may point to a removed book, an old reader route, or a page that has moved.
      </p>
      <div className="mt-9 flex flex-col gap-3 sm:flex-row">
        <Link to="/library" className="btn-primary justify-center">
          Browse Library
        </Link>
        <Link to="/" className="btn-secondary justify-center">
          <ChevronLeft size={15} strokeWidth={1.6} /> Home
        </Link>
      </div>
    </section>
  );
}
