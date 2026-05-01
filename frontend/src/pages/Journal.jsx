import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import useSEO from "../hooks/useSEO";

const JOURNAL_OG = "https://images.unsplash.com/photo-1764087957302-ef0756ed8e0a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85";

const readMinutes = (text = "") => Math.max(2, Math.round((text || "").split(/\s+/).filter(Boolean).length / 200));
const fmtDate = (iso) => {
  try { return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }); }
  catch { return ""; }
};

export default function Journal() {
  const [posts, setPosts] = useState([]);
  const [active, setActive] = useState("all");

  useSEO({
    title: "Journal — The Earnalism",
    description: "Notes from an independent online bookstore that reads slowly — essays on literature, business, and the quiet craft of reading.",
    image: JOURNAL_OG,
  });

  useEffect(() => { api.get("/blog").then((r) => setPosts(r.data)).catch(() => {}); }, []);

  const cats = useMemo(() => ["all", ...Array.from(new Set(posts.map((p) => p.category)))], [posts]);
  const filtered = active === "all" ? posts : posts.filter((p) => p.category === active);
  const [feature, ...rest] = filtered;

  return (
    <div data-testid="journal-page">
      {/* Masthead */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-20 sm:pt-28 pb-12 sm:pb-16 text-center">
        <div className="issue-marker mb-6">Issue 01 &middot; Volume I</div>
        <h1 className="font-serif-light text-4xl sm:text-6xl lg:text-[4.5rem] text-burgundy tracking-tight max-w-4xl mx-auto leading-[1.02] text-balance">
          The <span className="italic-accent">Journal</span> — notes from a bookstore that reads slowly.
        </h1>
        <p className="font-serif-display italic text-lg sm:text-xl text-charcoal-soft mt-7 max-w-2xl mx-auto leading-snug">Essays on literature, business, technology, and the quiet craft of reading well.</p>
        <div className="gold-rule mx-auto mt-10" />
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-6">
        <div className="flex flex-wrap gap-2 border-y border-brand-soft py-6 justify-center" data-testid="journal-filters">
          {cats.map((c) => (
            <button
              key={c}
              onClick={() => setActive(c)}
              data-testid={`journal-filter-${c.toLowerCase()}`}
              className={`px-4 py-2 rounded-full text-[0.68rem] tracking-[0.24em] uppercase transition-colors ${active === c ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy border border-transparent hover:border-[var(--brand-gold)]/40"}`}
            >
              {c === "all" ? "All Notes" : c}
            </button>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-28 space-y-16">
        {feature && (
          <Link to={`/journal/${feature.slug}`} className="grid grid-cols-1 lg:grid-cols-12 gap-10 group" data-testid="journal-feature">
            <div className="lg:col-span-7 aspect-[16/10] lg:aspect-auto lg:min-h-[460px] overflow-hidden rounded-xl border border-brand-soft">
              {feature.cover_image_url && <img src={feature.cover_image_url} alt={feature.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-[900ms] group-hover:scale-[1.03]" />}
            </div>
            <div className="lg:col-span-5 flex flex-col justify-center">
              <div className="overline mb-4">Featured · {feature.category}</div>
              <h2 className="font-serif-light text-3xl sm:text-4xl lg:text-5xl text-burgundy leading-[1.08] tracking-tight">{feature.title}</h2>
              <div className="gold-rule-thin mt-6" />
              <p className="font-serif-display italic text-lg text-charcoal-soft mt-6 leading-snug">{feature.excerpt}</p>
              <div className="text-[0.7rem] tracking-[0.22em] uppercase text-charcoal-soft mt-7">By {feature.author || "The Earnalism"} &middot; {fmtDate(feature.created_at)} &middot; {readMinutes(feature.content)} min read</div>
              <span className="btn-link mt-7 self-start">Read the article</span>
            </div>
          </Link>
        )}

        {rest.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 sm:gap-10 pt-10 border-t border-brand-soft">
            {rest.map((p) => (
              <Link key={p.slug} to={`/journal/${p.slug}`} className="group flex flex-col gap-5" data-testid={`journal-card-${p.slug}`}>
                <div className="aspect-[4/3] overflow-hidden rounded-xl border border-brand-soft">
                  {p.cover_image_url && <img src={p.cover_image_url} alt={p.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-[900ms] group-hover:scale-[1.04]" />}
                </div>
                <div>
                  <div className="overline mb-3">{p.category}</div>
                  <h3 className="font-serif-light text-[1.55rem] text-burgundy leading-[1.15] tracking-tight">{p.title}</h3>
                  <p className="font-serif-display italic text-charcoal-soft mt-3 line-clamp-3 text-base leading-snug">{p.excerpt}</p>
                  <div className="text-[0.68rem] tracking-[0.22em] uppercase text-charcoal-soft mt-4">{fmtDate(p.created_at)} &middot; {readMinutes(p.content)} min read</div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {filtered.length === 0 && (
          <div className="card-elegant p-16 text-center" data-testid="journal-empty">
            <h3 className="font-serif-light text-3xl text-burgundy">No notes yet on this shelf.</h3>
          </div>
        )}
      </section>
    </div>
  );
}
