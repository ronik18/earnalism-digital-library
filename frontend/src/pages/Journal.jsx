import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { api } from "../lib/api";
import { optimizedImageUrl } from "../lib/images";
import useSEO from "../hooks/useSEO";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

const JOURNAL_OG = "https://images.unsplash.com/photo-1764087957302-ef0756ed8e0a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMGRlc2t8ZW58MHx8fHwxNzc3NjE3MTc3fDA&ixlib=rb-4.1.0&q=85";
const BLOCKED_JOURNAL_SLUGS = new Set(["the-quiet-power-of-a-premium-bookstore-brand"]);
const readMinutes = (text = "") => Math.max(2, Math.round(String(text).split(/\s+/).filter(Boolean).length / 200));
const fmtDate = (iso) => {
  try { return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }); }
  catch { return ""; }
};

function ArticleCard({ post }) {
  return (
    <Link to={"/journal/" + post.slug} className="editorial-article-card group" data-testid={"journal-card-" + post.slug}>
      <div className="editorial-article-card__image">
        {post.cover_image_url ? <img src={optimizedImageUrl(post.cover_image_url, { width: 720 })} width="720" height="540" alt="" loading="lazy" decoding="async" /> : null}
      </div>
      <div className="editorial-article-card__content">
        <div className="editorial-kicker">{post.category || "Journal"}</div>
        <h2 className="mt-4 font-serif-light text-[1.65rem] leading-[1.12] tracking-tight text-burgundy">{post.title}</h2>
        {post.excerpt ? <p className="mt-4 font-serif-display text-base italic leading-snug text-charcoal-soft line-clamp-3">{post.excerpt}</p> : null}
        <div className="mt-5 text-[0.66rem] uppercase tracking-[0.2em] text-charcoal-soft">{fmtDate(post.created_at)} · {readMinutes(post.content)} min read</div>
        <span className="btn-link inline-flex min-h-11 items-center gap-1">Read article <ArrowUpRight size={15} aria-hidden="true" /></span>
      </div>
    </Link>
  );
}

export default function Journal() {
  const [posts, setPosts] = useState([]);
  const [active, setActive] = useState("all");
  const [loading, setLoading] = useState(true);

  useSEO({
    title: "The Journal — The Earnalism",
    description: "Notes from The Earnalism on literature, work, and the quiet craft of reading well.",
    image: JOURNAL_OG,
    canonicalPath: "/journal",
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api.get("/blog", { signal: controller.signal })
      .then((response) => setPosts(Array.isArray(response.data) ? response.data : []))
      .catch(() => setPosts([]))
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const visiblePosts = useMemo(() => posts.filter((post) => !BLOCKED_JOURNAL_SLUGS.has(String(post.slug || "").toLowerCase())), [posts]);
  const categories = useMemo(() => ["all", ...Array.from(new Set(visiblePosts.map((post) => post.category).filter(Boolean)))], [visiblePosts]);
  const filtered = active === "all" ? visiblePosts : visiblePosts.filter((post) => post.category === active);
  const [featured, ...remaining] = filtered;

  return (
    <PublicPageFrame tone="editorial" testId="journal-page">
      <section className="editorial-support-hero">
        <div className="relative mx-auto max-w-7xl px-5 pb-14 pt-20 sm:px-8 sm:pb-20 sm:pt-28 lg:px-12">
          <p className="editorial-kicker">The Earnalism Journal</p>
          <h1 className="mt-5 max-w-4xl font-serif-light text-4xl leading-[1.02] tracking-tight text-burgundy sm:text-6xl lg:text-[4.5rem]">The Journal — notes for a more attentive reading life.</h1>
          <p className="mt-7 max-w-2xl font-serif-display text-lg italic leading-snug text-charcoal-soft sm:text-xl">Essays on literature, work, and the quiet craft of returning to a page with care.</p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12">
        <div className="flex flex-wrap gap-2" aria-label="Journal categories" data-testid="journal-filters">
          {categories.map((category) => (
            <button key={category} type="button" onClick={() => setActive(category)} data-testid={"journal-filter-" + category.toLowerCase()}
              className={active === category ? "min-h-11 rounded-full border border-burgundy bg-burgundy px-4 py-2 text-[0.68rem] uppercase tracking-[0.18em] text-[var(--brand-ivory)]" : "min-h-11 rounded-full border border-brand-soft px-4 py-2 text-[0.68rem] uppercase tracking-[0.18em] text-charcoal-soft transition-colors hover:border-gold hover:text-burgundy"}>
              {category === "all" ? "All notes" : category}
            </button>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-24 sm:px-8 lg:px-12">
        {loading ? <div className="editorial-surface px-6 py-16 text-center text-charcoal-soft" role="status" data-testid="journal-loading">Opening the journal…</div> : null}
        {!loading && featured ? (
          <div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr]" data-testid="journal-feature">
            <Link to={"/journal/" + featured.slug} className="group overflow-hidden rounded-[1.35rem] border border-brand-soft bg-[#f1e4cf]">
              {featured.cover_image_url ? <img src={optimizedImageUrl(featured.cover_image_url, { width: 1200 })} width="1200" height="750" alt="" loading="eager" decoding="async" className="aspect-[16/10] h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]" /> : null}
            </Link>
            <div className="editorial-surface flex flex-col justify-center p-7 sm:p-10">
              <p className="editorial-kicker">Featured {featured.category ? "· " + featured.category : ""}</p>
              <h2 className="mt-5 font-serif-light text-3xl leading-[1.08] tracking-tight text-burgundy sm:text-5xl">{featured.title}</h2>
              {featured.excerpt ? <p className="mt-6 font-serif-display text-lg italic leading-snug text-charcoal-soft">{featured.excerpt}</p> : null}
              <p className="mt-7 text-[0.67rem] uppercase tracking-[0.18em] text-charcoal-soft">By {featured.author || "The Earnalism"} · {fmtDate(featured.created_at)} · {readMinutes(featured.content)} min read</p>
              <Link to={"/journal/" + featured.slug} className="btn-primary mt-8 inline-flex min-h-11 w-fit items-center gap-2">Read article <ArrowUpRight size={16} aria-hidden="true" /></Link>
            </div>
          </div>
        ) : null}
        {!loading && remaining.length > 0 ? <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">{remaining.map((post) => <ArticleCard key={post.slug} post={post} />)}</div> : null}
        {!loading && filtered.length === 0 ? <div className="editorial-surface px-6 py-16 text-center" data-testid="journal-empty"><h2 className="font-serif-light text-3xl text-burgundy">No notes on this shelf yet.</h2><p className="mt-3 text-charcoal-soft">Choose another subject or return to the full journal.</p></div> : null}
      </section>
    </PublicPageFrame>
  );
}
