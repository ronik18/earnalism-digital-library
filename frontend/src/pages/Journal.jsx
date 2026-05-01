import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export default function Journal() {
  const [posts, setPosts] = useState([]);
  const [active, setActive] = useState("all");

  useEffect(() => { api.get("/blog").then((r) => setPosts(r.data)).catch(() => {}); }, []);

  const cats = useMemo(() => ["all", ...Array.from(new Set(posts.map((p) => p.category)))], [posts]);
  const filtered = active === "all" ? posts : posts.filter((p) => p.category === active);
  const [feature, ...rest] = filtered;

  return (
    <div data-testid="journal-page">
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-16 sm:pt-24 pb-10">
        <div className="overline mb-3">The Journal</div>
        <h1 className="font-serif-display text-4xl sm:text-6xl text-burgundy tracking-tight max-w-3xl text-balance">Notes from a publishing house that reads slowly.</h1>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-6">
        <div className="flex flex-wrap gap-2 border-y border-brand py-5" data-testid="journal-filters">
          {cats.map((c) => (
            <button
              key={c}
              onClick={() => setActive(c)}
              data-testid={`journal-filter-${c.toLowerCase()}`}
              className={`px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase transition-colors ${active === c ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy border border-transparent hover:border-[var(--brand-gold)]/40"}`}
            >
              {c === "all" ? "All Notes" : c}
            </button>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-24 space-y-12">
        {feature && (
          <Link to={`/journal/${feature.slug}`} className="grid grid-cols-1 lg:grid-cols-12 gap-8 group card-elegant overflow-hidden" data-testid="journal-feature">
            <div className="lg:col-span-7 aspect-[16/10] lg:aspect-auto lg:min-h-[420px] overflow-hidden">
              {feature.cover_image_url && <img src={feature.cover_image_url} alt={feature.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]" />}
            </div>
            <div className="lg:col-span-5 p-8 sm:p-12 flex flex-col justify-center">
              <div className="overline mb-3">{feature.category}</div>
              <h2 className="font-serif-display text-3xl sm:text-4xl text-burgundy leading-tight">{feature.title}</h2>
              <p className="text-charcoal-soft mt-4 leading-relaxed">{feature.excerpt}</p>
              <span className="btn-link mt-6 self-start">Read the article</span>
            </div>
          </Link>
        )}

        {rest.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            {rest.map((p) => (
              <Link key={p.slug} to={`/journal/${p.slug}`} className="card-elegant overflow-hidden group" data-testid={`journal-card-${p.slug}`}>
                <div className="aspect-[4/3] overflow-hidden">
                  {p.cover_image_url && <img src={p.cover_image_url} alt={p.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />}
                </div>
                <div className="p-6 sm:p-7">
                  <div className="overline mb-3">{p.category}</div>
                  <h3 className="font-serif-display text-2xl text-burgundy leading-snug">{p.title}</h3>
                  <p className="text-charcoal-soft mt-3 line-clamp-3 text-sm leading-relaxed">{p.excerpt}</p>
                </div>
              </Link>
            ))}
          </div>
        )}

        {filtered.length === 0 && (
          <div className="card-elegant p-16 text-center" data-testid="journal-empty">
            <h3 className="font-serif-display text-3xl text-burgundy">No notes yet on this shelf.</h3>
          </div>
        )}
      </section>
    </div>
  );
}
