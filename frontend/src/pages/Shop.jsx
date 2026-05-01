import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
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
    title: "Shop — The Earnalism",
    description: "A small, deliberate shelf — chosen for depth. Browse curated titles in business, self-growth, literature, spirituality, and Bengali reading.",
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
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-16 sm:pt-24 pb-10">
        <div className="overline mb-3">The Collection</div>
        <h1 className="font-serif-display text-4xl sm:text-6xl text-burgundy tracking-tight max-w-3xl text-balance">A small, deliberate shelf — chosen for depth.</h1>
        <p className="text-charcoal-soft mt-5 max-w-2xl leading-relaxed">Begin with our featured book, or browse by shelf. New titles arrive only when they are ready to be read for years.</p>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-6">
        <div className="flex flex-col lg:flex-row gap-5 lg:items-center lg:justify-between border-y border-brand py-5">
          <div className="flex flex-wrap gap-2" data-testid="category-filters">
            {filters.map((f) => (
              <button
                key={f.slug}
                onClick={() => setCat(f.slug)}
                data-testid={`filter-${f.slug}`}
                className={`px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase transition-colors ${cat === f.slug ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy border border-transparent hover:border-[var(--brand-gold)]/40"}`}
              >
                {f.name}
              </button>
            ))}
          </div>
          <div className="relative max-w-sm w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft" size={16} />
            <input
              value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Search titles, themes…"
              className="input-elegant pl-9 !border-b !border-[var(--brand-border)]"
              data-testid="shop-search"
            />
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pb-24">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="card-elegant overflow-hidden">
                <div className="aspect-[3/4] bg-beige animate-pulse" />
                <div className="p-6 space-y-3">
                  <div className="h-3 w-20 bg-beige animate-pulse rounded" />
                  <div className="h-5 w-3/4 bg-beige animate-pulse rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : books.length === 0 ? (
          cat === "technology" ? (
            <div className="card-elegant p-12 sm:p-20 text-center" data-testid="shop-empty-technology">
              <div className="overline mb-3">Technology Shelf</div>
              <h3 className="font-serif-display text-3xl text-burgundy">Technology titles are being curated.</h3>
              <p className="text-charcoal-soft mt-3 max-w-xl mx-auto">Return soon for books on software, AI, data, and digital enterprise.</p>
            </div>
          ) : (
            <div className="card-elegant p-12 sm:p-20 text-center" data-testid="shop-empty">
              <div className="overline mb-3">An Open Shelf</div>
              <h3 className="font-serif-display text-3xl text-burgundy">No titles match — yet.</h3>
              <p className="text-charcoal-soft mt-3 max-w-md mx-auto">Try another shelf, or join the Reading Circle to know when our next book arrives.</p>
            </div>
          )
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8" data-testid="books-grid">
            {books.map((b) => <BookCard key={b.slug} book={b} />)}
          </div>
        )}
      </section>
    </div>
  );
}
