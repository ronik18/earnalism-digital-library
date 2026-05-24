import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Sparkles, Compass } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "../lib/api";
import { optimizedImageUrl } from "../lib/images";
import LiveCoverShowcase from "../components/LiveCoverShowcase";
import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1920&q=90";
const FOUNDER_IMG = "https://images.unsplash.com/photo-1773067752075-2cfd37ab02dd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHw0fHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85";
const SHELF_IMAGES = {
  "bengali": "/assets/shelves/bengali.jpg",
  "bengali-reading": "/assets/shelves/bengali.jpg",
  "bengali-classics": "/assets/shelves/bengali.jpg",
  "business": "/assets/shelves/business.jpg",
  "business-entrepreneurship": "/assets/shelves/business.jpg",
  "history": "/assets/shelves/history-politics.jpg",
  "history-politics": "/assets/shelves/history-politics.jpg",
  "history-strategy": "/assets/shelves/history-politics.jpg",
  "literature": "/assets/shelves/literature.jpg",
  "self-growth": "/assets/shelves/self-growth.jpg",
  "self-improvement": "/assets/shelves/self-growth.jpg",
  "technology": "/assets/shelves/technology.jpg",
};

function shelfImageFor(category) {
  const slug = (category?.slug || "").toLowerCase();
  const name = (category?.name || "").toLowerCase();

  if (SHELF_IMAGES[slug]) return SHELF_IMAGES[slug];
  if (slug.includes("bengali") || name.includes("bengali")) return SHELF_IMAGES.bengali;
  if (slug.includes("business") || name.includes("business") || name.includes("entrepreneur")) return SHELF_IMAGES.business;
  if (slug.includes("history") || slug.includes("politic") || name.includes("history") || name.includes("politic")) return SHELF_IMAGES["history-politics"];
  if (slug.includes("literature") || name.includes("literature")) return SHELF_IMAGES.literature;
  if (slug.includes("self") || name.includes("self")) return SHELF_IMAGES["self-growth"];
  if (slug.includes("tech") || name.includes("tech") || name.includes("ai")) return SHELF_IMAGES.technology;

  return category?.image_url;
}

export default function Home() {
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState(null);
  const [liveBooks, setLiveBooks] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useSEO({
    title: "The Earnalism Digital Library — Buy Reading Time. Read Beautifully.",
    description: "A quiet digital reading room for books in business, self-growth, literature, spirituality, Bengali reading, and technology. Buy reading time. Read beautifully. Return whenever you wish.",
    image: HERO_IMG,
  });

  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled([
      api.get("/categories", { signal: controller.signal }),
      api.get("/featured", { signal: controller.signal }),
      api.get("/books", { signal: controller.signal }),
    ])
      .then(([categoryRes, featuredRes, booksRes]) => {
        if (categoryRes.status === "fulfilled") {
          setCategories(categoryRes.value.data || []);
        }
        if (featuredRes.status === "fulfilled") {
          setFeatured(featuredRes.value.data?.book || null);
        }
        if (booksRes.status === "fulfilled") {
          setLiveBooks(booksRes.value.data || []);
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  const subscribe = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const { data } = await api.post("/newsletter", { name, email });
      toast.success(data.message || "Welcome to the Reading Circle.");
      setName(""); setEmail("");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="home-page">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <img
            src={HERO_IMG}
            alt=""
            loading="eager"
            fetchPriority="high"
            decoding="async"
            className="w-full h-full object-cover"
            style={{ filter: "saturate(1.05) brightness(0.82)" }}
          />
          {/* Strong left-side dark gradient so headline + subtext sit on a deep, readable surface */}
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to right, rgba(14,6,8,0.88) 0%, rgba(14,6,8,0.66) 38%, rgba(14,6,8,0.28) 65%, rgba(14,6,8,0.05) 100%)" }}
          />
          {/* Subtle top + bottom deepening to ground the masthead and the page transition */}
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to bottom, rgba(14,6,8,0.45) 0%, transparent 22%, transparent 70%, rgba(14,6,8,0.30) 100%)" }}
          />
          {/* Warm amber glow on the upper-right — lifts the library's golden depth */}
          <div
            className="absolute inset-0"
            style={{ background: "radial-gradient(ellipse 55% 55% at 78% 40%, rgba(216,185,122,0.22), transparent 72%)" }}
          />
          {/* Soft transition into the page beige */}
          <div
            className="absolute inset-x-0 bottom-0 h-1/3"
            style={{ background: "linear-gradient(to top, #F4EFEA 0%, rgba(244,239,234,0.60) 55%, transparent 100%)" }}
          />
        </div>
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-32 lg:pt-36 pb-20 sm:pb-28 lg:pb-32">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <div className="max-w-3xl lg:col-span-7">
              <div className="italic-eyebrow text-[var(--brand-gold-soft)] mb-6 sm:mb-7 flex items-center gap-3" data-testid="hero-overline">
                <span className="h-px w-8 sm:w-10 bg-[var(--brand-gold)]/70" />
                <span className="text-[0.85rem] sm:text-[0.95rem]">Volume I &middot; The Digital Library</span>
              </div>
              <h1 className="font-serif-light text-[2.6rem] sm:text-[3.5rem] md:text-6xl lg:text-7xl leading-[1.04] text-[#FDFCF8] tracking-tight text-balance drop-shadow-[0_2px_24px_rgba(0,0,0,0.45)]" data-testid="hero-headline">
                The Earnalism <span className="italic-accent text-[var(--brand-gold-soft)]">Digital Library.</span>
              </h1>
              <p className="mt-5 sm:mt-6 font-serif-display italic text-lg sm:text-2xl text-[#F4EFEA]/90 max-w-xl leading-snug drop-shadow-[0_1px_18px_rgba(0,0,0,0.5)]">
                Buy reading time. Read beautifully. Return whenever you wish.
              </p>
              <p className="mt-6 sm:mt-7 text-[0.95rem] sm:text-[1.05rem] text-[#F4EFEA]/80 max-w-md sm:max-w-lg leading-[1.75] font-light drop-shadow-[0_1px_18px_rgba(0,0,0,0.4)]">
                A quiet digital reading room for books in business, self-growth, literature, spirituality, Bengali reading, and technology.
              </p>
              <div className="mt-10 sm:mt-12 flex flex-col sm:flex-row gap-3 sm:gap-4 sm:items-center">
                <Link to={featured ? `/reader/${featured.slug}` : "/library"} className="btn-primary w-full sm:w-auto" data-testid="hero-cta-read">Start Reading</Link>
                <Link to="/library" className="btn-secondary w-full sm:w-auto !text-[#FDFCF8] !border-[var(--brand-gold)] hover:!bg-[var(--brand-gold)]/10" data-testid="hero-cta-library">Explore the Library</Link>
              </div>
            </div>
            <div className="lg:col-span-5">
              <LiveCoverShowcase books={liveBooks} featured={featured} />
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 lg:py-32" id="collection">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 mb-12 sm:mb-16 lg:mb-20">
          <div className="max-w-xl">
            <div className="overline mb-4">The Shelves</div>
            <h2 className="font-serif-light text-[2.25rem] sm:text-5xl lg:text-[3.5rem] text-burgundy leading-[1.06] tracking-tight">A small library, <span className="italic-accent">carefully kept.</span></h2>
          </div>
          <Link to="/library" className="btn-link self-start sm:self-end" data-testid="categories-view-all">View the full library <ArrowRight size={14} /></Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-7 lg:gap-9">
          {categories.map((c, i) => {
            const shelfImage = shelfImageFor(c);

            return (
              <Link
                key={c.slug}
                to={`/library?category=${c.slug}`}
                className={`card-elegant overflow-hidden group ${i === 0 ? "lg:col-span-2 lg:row-span-2" : ""}`}
                data-testid={`category-card-${c.slug}`}
              >
                <div className={`relative ${i === 0 ? "aspect-[16/10] lg:aspect-[16/12]" : "aspect-[4/3]"} overflow-hidden`}>
                  {shelfImage && (
                    <img src={optimizedImageUrl(shelfImage, { width: i === 0 ? 1200 : 720 })} alt={c.name} loading="lazy" decoding="async" className="w-full h-full object-cover transition-transform [transition-duration:1200ms] group-hover:scale-[1.06]" />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#2a1218]/72 via-[#2a1218]/15 to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-7 sm:p-9">
                    <span className="text-[0.65rem] tracking-[0.32em] uppercase text-[var(--brand-gold-soft)]">Shelf · 0{i + 1}</span>
                    <h3 className={`font-serif-light text-[#FDFCF8] ${i === 0 ? "text-3xl sm:text-[2.5rem] mt-3" : "text-2xl mt-2"} leading-[1.1] tracking-tight`}>{c.name}</h3>
                    <p className="text-[#F4EFEA]/85 text-[0.92rem] leading-[1.65] mt-3 max-w-md font-light">{c.description}</p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* FEATURED BOOK */}
      {featured && (
        <section className="surface-warm border-y border-brand-soft">
          <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 lg:py-32 grid grid-cols-1 lg:grid-cols-12 gap-10 sm:gap-12 lg:gap-16 items-center">
            <div className="lg:col-span-5">
              <div className="aspect-[3/4] rounded-xl overflow-hidden border border-brand-soft bg-ivory-warm shadow-[0_30px_70px_-30px_rgba(74,28,39,0.4)] max-w-[320px] sm:max-w-sm mx-auto lg:max-w-none lg:mx-0">
                <img src={optimizedImageUrl(featured.cover_image_url, { width: 760 })} alt={featured.title} loading="lazy" decoding="async" className="w-full h-full object-contain" />
              </div>
            </div>
            <div className="lg:col-span-7 text-center lg:text-left">
              <div className="italic-eyebrow mb-4 sm:mb-5">Currently on the table</div>
              <h2 className="font-serif-light text-[2.25rem] sm:text-5xl lg:text-[3.5rem] text-burgundy leading-[1.06] tracking-tight">{featured.title}</h2>
              <p className="font-serif-display italic text-lg sm:text-2xl text-burgundy-soft mt-3 sm:mt-4 leading-snug">{featured.subtitle}</p>
              <div className="gold-rule-thin mt-6 mx-auto lg:mx-0" />
              <p className="text-charcoal-soft mt-6 sm:mt-7 leading-[1.85] max-w-2xl font-light text-[0.95rem] sm:text-base mx-auto lg:mx-0">{featured.description}</p>
              <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 justify-center lg:justify-start">
                <Link to={`/book/${featured.slug}`} className="btn-secondary justify-center" data-testid="featured-view">View Book</Link>
                {featured.buy_url ? (
                  <a href={featured.buy_url} target="_blank" rel="noreferrer" className="btn-primary justify-center" data-testid="featured-buy">Buy Now</a>
                ) : (
                  <Link to="/contact" className="btn-primary justify-center" data-testid="featured-request">Request Purchase Info</Link>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* WHY EARNALISM */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 lg:py-32">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16 lg:mb-20">
          <div className="overline mb-3 sm:mb-4">Why The Earnalism</div>
          <h2 className="font-serif-light text-[2.25rem] sm:text-5xl text-burgundy tracking-tight leading-[1.06]">A bookstore for readers who <span className="italic-accent">linger.</span></h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-7 lg:gap-8 max-w-5xl mx-auto lg:max-w-none">
          {[
            { icon: Sparkles, title: "Curated With Meaning", body: "Every shelf is a slow act of selection. We choose books we would lend to a close friend — and never apologise for the smaller list." },
            { icon: BookOpen, title: "Built for Thoughtful Readers", body: "Our writing, design, and packaging assume a patient reader. Margins to think in. Typography to return to. A pace that respects you." },
            { icon: Compass, title: "From Reading to Practice", body: "Every shelf is chosen to turn careful reading into careful living — steadier thinking, better work, quieter days. We curate for return, not rush." },
          ].map((c, i) => (
            <div key={c.title} className={`card-elegant p-8 sm:p-9 lg:p-11 ${i === 2 ? "md:col-span-2 lg:col-span-1" : ""}`} data-testid={`why-card-${c.title.toLowerCase().replace(/\s/g, '-')}`}>
              <c.icon className="text-gold" size={26} strokeWidth={1.4} />
              <div className="gold-rule-thin mt-5 mb-6" />
              <h3 className="font-serif-display text-[1.5rem] sm:text-2xl text-burgundy mb-3 sm:mb-4 leading-snug">{c.title}</h3>
              <p className="text-charcoal-soft leading-[1.8] text-[0.92rem] sm:text-[0.95rem] font-light">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOUNDER NOTE */}
      <section className="surface-warm border-y border-brand-soft">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 lg:py-32 grid grid-cols-1 lg:grid-cols-12 gap-10 sm:gap-12 lg:gap-16 items-center">
          <div className="lg:col-span-5 order-2 lg:order-1">
            <div className="aspect-[4/5] rounded-xl overflow-hidden border border-brand-soft max-w-[280px] sm:max-w-sm mx-auto lg:max-w-none">
              <img src={optimizedImageUrl(FOUNDER_IMG, { width: 760 })} alt="" loading="lazy" decoding="async" className="w-full h-full object-cover" />
            </div>
          </div>
          <div className="lg:col-span-7 order-1 lg:order-2 text-center lg:text-left">
            <div className="italic-eyebrow mb-4 sm:mb-5">A note from the desk</div>
            <h2 className="font-serif-light text-[2.25rem] sm:text-5xl text-burgundy leading-[1.06] tracking-tight">A bookstore for the reader who still believes in <span className="italic-accent">depth.</span></h2>
            <p className="text-charcoal-soft mt-6 sm:mt-8 leading-[1.85] text-[0.98rem] sm:text-[1.02rem] max-w-2xl font-light mx-auto lg:mx-0">
              The Earnalism began as a quiet rebellion against noisy bookshelves. We believe a book is a long conversation — patient, particular, and worth the careful season it takes to write. As an independent online bookstore, we keep the list small and the standard generous. Every title here is chosen for one reader: the one who still believes that meaning compounds, slowly, across the right pages.
            </p>
            <div className="gold-rule mt-8 sm:mt-10 mx-auto lg:mx-0" />
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 lg:py-32">
        <div className="surface-quiet border border-brand-soft rounded-xl p-8 sm:p-12 lg:p-20 text-center max-w-3xl mx-auto" data-testid="newsletter-card">
          <div className="italic-eyebrow mb-3 sm:mb-4">From the Editor's Desk</div>
          <h2 className="font-serif-light text-[2rem] sm:text-4xl lg:text-5xl text-burgundy tracking-tight leading-[1.08]">Join the Earnalism <span className="italic-accent">Reading Circle.</span></h2>
          <div className="gold-rule-thin mx-auto mt-6 sm:mt-7" />
          <p className="text-charcoal-soft mt-6 sm:mt-7 max-w-xl mx-auto leading-[1.8] font-light text-[0.95rem]">
            Receive thoughtful book notes, new shelf arrivals, and curated reading recommendations — written with the care of a private letter.
          </p>
          <form onSubmit={subscribe} className="mt-10 sm:mt-12 grid grid-cols-1 sm:grid-cols-2 gap-5 sm:gap-6 max-w-xl mx-auto text-left">
            <input
              required value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Your name" className="input-elegant" data-testid="newsletter-name"
            />
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="Your email" className="input-elegant" data-testid="newsletter-email"
            />
            <div className="sm:col-span-2 flex justify-center mt-5 sm:mt-6">
              <button disabled={submitting} type="submit" className="btn-primary w-full sm:w-auto justify-center disabled:opacity-60" data-testid="newsletter-submit">
                {submitting ? "Joining…" : "Join the Circle"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
