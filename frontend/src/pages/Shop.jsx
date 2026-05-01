import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import BookCard from "../components/BookCard";
import useSEO from "../hooks/useSEO";

const SHOP_OG = "https://images.unsplash.com/photo-1739918075668-fc7844c6d921?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwyfHxsdXh1cnklMjBsaWJyYXJ5JTIwaW50ZXJpb3IlMjB3YXJtJTIwbGlnaHRpbmd8ZW58MHx8fHwxNzc3NjE3MTkwfDA&ixlib=rb-4.1.0&q=85";

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get("q") || "");
  const cat = params.get("category") || "all";

  useSEO({
    title: "Shop the Collection — The Earnalism",
    description: "Browse The Earnalism's curated bookstore — a small, deliberate shelf of titles in business, self-growth, literature, spirituality, technology, and Bengali reading. Independent online bookstore & self-publishing house.",
    image: SHOP_OG,
  });

  useEffect(() => { api.get("/categories").then((r) => setCategories(r.data)).catch(() => {}); }, []);

  useEffect(() => {
    setLoading(true);
    const p = {};
    if (cat && cat !== "all") p.category = cat;
    if (q) p.q = q;
    api.get("/books", { params: p }).then((r) => setBooks(r.data)).catch(() => setBooks([])).finally(() => setLoading(false));
  }, [cat, q]);

  const setCat = (slug) => {
    const next = new URLSearchParams(params);
    if (slug === "all") next.delete("category"); else next.set("category", slug);
    setParams(next);
  };

  const filters = useMemo(() => [{ slug: "all", name: "All" }, ...categories], [categories]);

  return (
    <div data-testid="shop-page">
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-20 sm:pt-28 pb-12 sm:pb-16">
        <div className="italic-eyebrow mb-4">The Collection &middot; Volume I</div>
        <h1 className="font-serif-light text-4xl sm:text-6xl lg:text-[4.25rem] text-burgundy tracking-tight max-w-3xl text-balance leading-[1.02]">A small, deliberate shelf — <span className="italic-accent">chosen for depth.</span></h1>
        <p className="text-charcoal-soft mt-7 max-w-xl leading-[1.85] font-light">Begin with our featured book, or browse by shelf. New titles arrive only when they are ready to be read for years.</p>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-6">
        <div className="flex flex-col lg:flex-row gap-6 lg:items-center lg:justify-between border-y border-brand-soft py-6">
          <div className="flex flex-wrap gap-2" data-testid="category-filters">
            {filters.map((f) => (
              <button
                key={f.slug}
                onClick={() => setCat(f.slug)}
                data-testid={`filter-${f.slug}`}
                className={`px-4 py-2 rounded-full text-[0.68rem] tracking-[0.24em] uppercase transition-colors ${cat === f.slug ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy border border-transparent hover:border-[var(--brand-gold)]/40"}`}
              >
                {f.name}
              </button>
            ))}
          </div>
          <div className="relative max-w-sm w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft" size={15} strokeWidth={1.5} />
            <input
              value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Search titles, themes…"
              className="input-elegant pl-9 !border-b !border-[var(--brand-border)]"
              data-testid="shop-search"
            />
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-28">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-7 sm:gap-9">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="card-elegant overflow-hidden">
                <div className="aspect-[3/4] bg-beige-deep animate-pulse" />
                <div className="p-7 space-y-3">
                  <div className="h-3 w-20 bg-beige-deep animate-pulse rounded" />
                  <div className="h-5 w-3/4 bg-beige-deep animate-pulse rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : books.length === 0 ? (
          cat === "technology" ? (
            <div className="card-elegant p-12 sm:p-24 text-center" data-testid="shop-empty-technology">
              <div className="italic-eyebrow mb-4">Technology Shelf</div>
              <h3 className="font-serif-light text-3xl sm:text-4xl text-burgundy leading-tight">Technology titles are <span className="italic-accent">being curated.</span></h3>
              <div className="gold-rule-thin mx-auto mt-6 mb-6" />
              <p className="text-charcoal-soft max-w-xl mx-auto leading-[1.8] font-light">Return soon for books on software, AI, data, and digital enterprise.</p>
            </div>
          ) : (
            <div className="card-elegant p-12 sm:p-24 text-center" data-testid="shop-empty">
              <div className="italic-eyebrow mb-4">An open shelf</div>
              <h3 className="font-serif-light text-3xl sm:text-4xl text-burgundy">No titles match — <span className="italic-accent">yet.</span></h3>
              <p className="text-charcoal-soft mt-5 max-w-md mx-auto leading-[1.8] font-light">Try another shelf, or join the Reading Circle to know when our next book arrives.</p>
            </div>
          )
        ) : books.length === 1 ? (
          <SingleBookSpotlight book={books[0]} />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-7 sm:gap-9" data-testid="books-grid">
            {books.map((b) => <BookCard key={b.slug} book={b} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function SingleBookSpotlight({ book }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-center max-w-5xl mx-auto py-6 sm:py-10" data-testid="single-book-spotlight">
      <Link to={`/shop/${book.slug}`} className="lg:col-span-5 group" data-testid={`book-card-${book.slug}`}>
        <div className="aspect-[3/4] rounded-xl overflow-hidden border border-brand-soft shadow-[0_40px_80px_-40px_rgba(74,28,39,0.4)]">
          {book.cover_image_url ? (
            <img src={book.cover_image_url} alt={book.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-[900ms] group-hover:scale-[1.03]" />
          ) : (
            <div className="w-full h-full bg-beige-deep flex items-center justify-center font-serif-light text-7xl text-burgundy">E</div>
          )}
        </div>
      </Link>
      <div className="lg:col-span-7">
        <span className="overline">{book.category_slug?.replace(/-/g, ' ')}</span>
        <h2 className="font-serif-light text-4xl sm:text-5xl text-burgundy leading-[1.05] mt-4 tracking-tight">{book.title}</h2>
        {book.subtitle && (
          <p className="font-serif-display italic text-xl sm:text-2xl text-burgundy-soft mt-4 leading-snug">{book.subtitle}</p>
        )}
        <div className="gold-rule-thin mt-6" />
        {book.short_description && (
          <p className="text-charcoal-soft mt-7 leading-[1.85] font-light max-w-xl">{book.short_description}</p>
        )}
        <div className="mt-9 flex flex-wrap gap-3 sm:gap-4">
          <Link to={`/shop/${book.slug}`} className="btn-secondary">View Book</Link>
          {book.buy_url ? (
            <a href={book.buy_url} target="_blank" rel="noreferrer" className="btn-primary">Buy Now</a>
          ) : (
            <Link to="/contact" className="btn-primary">Request Purchase Info</Link>
          )}
        </div>
      </div>
    </div>
  );
}
