import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Heart, MessageCircle } from "lucide-react";
import { api } from "../lib/api";
import { optimizedImageUrl } from "../lib/images";
import useSEO from "../hooks/useSEO";
import JournalNewsletter from "../components/JournalNewsletter";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";
import "../styles/journal-option-b.css";

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
        <div className="mt-5 text-[0.66rem] uppercase tracking-[0.2em] text-charcoal-soft">By {post.author || "The Earnalism"} · {fmtDate(post.created_at)} · {readMinutes(post.content)} min read</div>
        <span className="journal-option-b__card-actions"><span aria-hidden="true"><Heart size={20} /><MessageCircle size={20} /></span><span className="journal-v2__article-link inline-flex min-h-11 items-center gap-1">Read article <ArrowUpRight size={15} aria-hidden="true" /></span></span>
      </div>
    </Link>
  );
}

export default function Journal() {
  const [posts, setPosts] = useState([]);
  const [active, setActive] = useState("all");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("newest");
  const [error, setError] = useState(false);
  const [requestRevision, setRequestRevision] = useState(0);

  useSEO({
    title: "The Journal — The Earnalism",
    description: "Notes from The Earnalism on literature, work, and the quiet craft of reading well.",
    image: JOURNAL_OG,
    canonicalPath: "/journal",
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(false);
    api.get("/blog", { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) { setPosts(Array.isArray(response.data) ? response.data : []); setError(false); } })
      .catch(() => { if (!controller.signal.aborted) { setPosts([]); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [requestRevision]);

  const visiblePosts = useMemo(() => posts.filter((post) => !BLOCKED_JOURNAL_SLUGS.has(String(post.slug || "").toLowerCase())), [posts]);
  const categories = useMemo(() => ["all", ...Array.from(new Set(visiblePosts.map((post) => post.category).filter(Boolean)))], [visiblePosts]);
  const filtered = visiblePosts.filter((post) => (active === "all" || post.category === active) && `${post.title} ${post.excerpt || ""} ${post.author || ""}`.toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === "oldest" ? new Date(a.created_at) - new Date(b.created_at) : new Date(b.created_at) - new Date(a.created_at));
  const [featured, ...remaining] = filtered;
  const pageCount = Math.max(1, Math.ceil(remaining.length / 6));
  useEffect(() => { setPage(1); }, [active, query, sort]);

  return (
    <PublicPageFrame tone="editorial" testId="journal-page">
      <section className="journal-v2__masthead">
        <div className="journal-v2__masthead-inner">
          <div>
            <p className="editorial-kicker">The Earnalism Journal</p>
            <h1><span>Ideas worth reading.</span><br />Stories worth sharing.</h1>
            <p className="journal-v2__lede">Essays, reading notes, and conversations for a more thoughtful life.</p>
          </div>
          <aside className="journal-v2__library-note" aria-label="Library discovery">
            <span>From the reading desk</span>
            <p>Every good note eventually leads back to a book.</p>
            <Link to="/library" data-testid="journal-library-link">Explore the Library <ArrowUpRight size={15} aria-hidden="true" /></Link>
          </aside>
        </div>
      </section>

      <section className="journal-v2__content">
        {!loading && error && <div className="journal-v2__empty" role="alert" data-testid="journal-api-error"><h2>The Journal could not be loaded.</h2><p>Please try again to retrieve the latest published articles.</p><button type="button" className="btn-secondary" onClick={() => setRequestRevision((revision) => revision + 1)}>Retry</button></div>}

        {loading ? <div className="editorial-surface px-6 py-16 text-center text-charcoal-soft" role="status" data-testid="journal-loading">Opening the journal…</div> : null}
        {!loading && featured ? (
          <div className="journal-v2__feature" data-testid="journal-feature">
            <Link to={"/journal/" + featured.slug} className="journal-v2__feature-image" data-testid="journal-feature-link" aria-label={`Read ${featured.title}`}>
              {featured.cover_image_url ? <img src={optimizedImageUrl(featured.cover_image_url, { width: 1200 })} width="1200" height="750" alt="" loading="eager" decoding="async" /> : <span aria-hidden="true" style={{ backgroundImage: "linear-gradient(120deg, rgba(70, 19, 34, .96), rgba(101, 29, 50, .76)), url('/assets/hero/quiet-heritage-still-life.png')" }} />}
            </Link>
            <div className="journal-v2__feature-copy">
              <p className="editorial-kicker">Featured {featured.category ? "· " + featured.category : ""}</p>
              <h2>{featured.title}</h2>
              {featured.excerpt ? <p className="journal-v2__feature-excerpt">{featured.excerpt}</p> : null}
              <p className="journal-v2__metadata">By {featured.author || "The Earnalism"} · {fmtDate(featured.created_at)} · {readMinutes(featured.content)} min read</p>
              <Link to={"/journal/" + featured.slug} className="journal-v2__primary-link" data-testid="journal-feature-read">Read article <ArrowUpRight size={16} aria-hidden="true" /></Link>
            </div>
          </div>
        ) : null}
        <div className="journal-v2__filter-row" aria-label="Journal categories" data-testid="journal-filters">
          <p>Browse by subject</p>
          <div>
          {categories.map((category) => (
            <button key={category} type="button" onClick={() => setActive(category)} aria-pressed={active === category} data-testid={"journal-filter-" + category.toLowerCase()}
              className={active === category ? "is-active" : ""}>
              {category === "all" ? "All notes" : category}
            </button>
          ))}
          </div>
          <label className="journal-option-b__search"><span className="sr-only">Search articles</span><input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search articles…" /></label>
          <label><span className="sr-only">Sort articles</span><select value={sort} onChange={(e) => setSort(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
        </div>
        {!loading && remaining.length > 0 ? <><div className="journal-v2__section-heading"><p className="editorial-kicker">More from the desk</p><h2>More stories for thoughtful readers.</h2></div><div className="journal-v2__grid">{remaining.slice((page - 1) * 6, page * 6).map((post) => <ArticleCard key={post.slug} post={post} />)}</div></> : null}
        {!loading && pageCount > 1 && <nav className="journal-option-b__pagination" aria-label="Article pages"><button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button type="button" disabled={page === pageCount} onClick={() => setPage(page + 1)}>Next</button></nav>}
        {!loading && !error && filtered.length === 0 ? <div className="journal-v2__empty" data-testid="journal-empty"><h2>No notes on this shelf yet.</h2><p>Choose another subject, or step into the Library to find a story.</p><Link to="/library">Explore the Library <ArrowUpRight size={15} aria-hidden="true" /></Link></div> : null}
      </section>
      <JournalNewsletter />
    </PublicPageFrame>
  );
}
