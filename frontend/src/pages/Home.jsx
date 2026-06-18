import { startTransition, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Sparkles, Compass, Feather, Mail, Instagram, Facebook, Youtube, Linkedin, Twitter, CreditCard } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "../lib/api";
import { optimizedImageUrl } from "../lib/images";
import BookCoverImage from "../components/BookCoverImage";
import LiveCoverShowcase from "../components/LiveCoverShowcase";
import { useSettings } from "../context/SettingsContext";
import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1920&q=90";
const FOUNDER_IMG = "https://images.unsplash.com/photo-1773067752075-2cfd37ab02dd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHw0fHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85";
const WHY_MOTIF_IMG = "/assets/shelves/literary-fiction.jpg";
const READING_CIRCLE_IMG = "https://images.unsplash.com/photo-1764087957302-ef0756ed8e0a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85";
const HERO_BOOK_INITIAL_PAGE_SIZE = 8;
const HERO_BOOK_PAGE_SIZE = 12;
const HERO_BOOK_RENDER_LIMIT = 72;
const SHELF_IMAGES = {
  "bengali": "/assets/shelves/bengali-classics.jpg",
  "bengali-reading": "/assets/shelves/bengali-classics.jpg",
  "bengali-classics": "/assets/shelves/bengali-classics.jpg",
  "business": "/assets/shelves/business.jpg",
  "business-entrepreneurship": "/assets/shelves/business.jpg",
  "history": "/assets/shelves/history-strategy.jpg",
  "history-politics": "/assets/shelves/history-strategy.jpg",
  "history-strategy": "/assets/shelves/history-strategy.jpg",
  "literature": "/assets/shelves/literary-fiction.jpg",
  "classic-literature": "/assets/shelves/literary-fiction.jpg",
  "literary-fiction": "/assets/shelves/literary-fiction.jpg",
  "children-classics": "/assets/shelves/young-readers.jpg",
  "young-readers": "/assets/shelves/young-readers.jpg",
  "technology": "/assets/shelves/technology-ai.jpg",
  "technology-ai": "/assets/shelves/technology-ai.jpg",
  "adventure": "/assets/shelves/adventure.jpg",
  "science-fiction": "/assets/shelves/science-fiction.jpg",
  "gothic-fiction": "/assets/shelves/gothic-fiction.jpg",
};

function shelfImageFor(category) {
  const slug = (category?.slug || "").toLowerCase();
  const name = (category?.name || "").toLowerCase();

  if (SHELF_IMAGES[slug]) return SHELF_IMAGES[slug];
  if (slug.includes("bengali") || name.includes("bengali")) return SHELF_IMAGES.bengali;
  if (slug.includes("business") || name.includes("business") || name.includes("entrepreneur")) return SHELF_IMAGES.business;
  if (slug.includes("history") || slug.includes("politic") || name.includes("history") || name.includes("politic")) return SHELF_IMAGES["history-politics"];
  if (slug.includes("literary") || slug.includes("literature") || name.includes("literary") || name.includes("literature")) return SHELF_IMAGES["literary-fiction"];
  if (slug.includes("young") || slug.includes("children") || name.includes("young") || name.includes("children")) return SHELF_IMAGES["young-readers"];
  if (slug.includes("tech") || name.includes("tech") || name.includes("ai")) return SHELF_IMAGES.technology;
  if (slug.includes("adventure") || name.includes("adventure")) return SHELF_IMAGES.adventure;
  if (slug.includes("science") || name.includes("science")) return SHELF_IMAGES["science-fiction"];
  if (slug.includes("gothic") || name.includes("gothic")) return SHELF_IMAGES["gothic-fiction"];

  return category?.image_url;
}

const WHY_POINTS = [
  {
    icon: Sparkles,
    title: "Curated slowly",
    proof: "No shelf sprawl",
    body: "Each shelf is chosen like a letter to one thoughtful reader: fewer titles, stronger reasons, more room to return.",
  },
  {
    icon: BookOpen,
    title: "Preview first",
    proof: "Reader-first buying",
    body: "Earnalism lets the book introduce itself before purchase, so curiosity can become trust at its own pace.",
  },
  {
    icon: Compass,
    title: "Built for focus",
    proof: "Quiet by design",
    body: "The typography, spacing, and reading path are tuned for calm attention instead of restless browsing.",
  },
];

const DESK_NOTES = [
  { number: "01", title: "Small lists", body: "A tighter catalog makes each recommendation feel earned." },
  { number: "02", title: "Reader pace", body: "Pages, previews, and shelves are arranged for unhurried decisions." },
  { number: "03", title: "Useful depth", body: "Classic literature, Bengali writing, business, history, and AI sit beside each other with purpose." },
];

const SOCIALS = [
  { key: "linkedin", label: "LinkedIn", Icon: Linkedin },
  { key: "twitter", label: "X", Icon: Twitter },
  { key: "instagram", label: "Instagram", Icon: Instagram },
  { key: "facebook", label: "Facebook", Icon: Facebook },
  { key: "youtube", label: "YouTube", Icon: Youtube },
];

function appendUniqueBooks(existing = [], incoming = [], maxItems = HERO_BOOK_RENDER_LIMIT) {
  const seen = new Set();
  const next = [];
  [...existing, ...incoming].forEach((book) => {
    const slug = book?.slug || book?.id;
    if (!slug || seen.has(slug) || next.length >= maxItems) return;
    seen.add(slug);
    next.push(book);
  });
  return next;
}

function normalizeBooksPage(payload, fallbackOffset = 0) {
  if (Array.isArray(payload)) {
    return {
      books: payload,
      pagination: {
        offset: fallbackOffset,
        limit: payload.length,
        count: payload.length,
        total: payload.length,
        next_offset: null,
        has_more: false,
      },
    };
  }
  const books = payload?.books || [];
  const pagination = payload?.pagination || payload?.books_page || {};
  const count = Number(pagination.count ?? books.length) || books.length;
  const offset = Number(pagination.offset ?? fallbackOffset) || 0;
  const nextOffset = pagination.next_offset ?? pagination.nextOffset ?? null;
  return {
    books,
    pagination: {
      offset,
      limit: Number(pagination.limit ?? books.length) || books.length,
      count,
      total: Number(pagination.total ?? books.length) || books.length,
      next_offset: nextOffset === undefined ? null : nextOffset,
      has_more: Boolean(pagination.has_more ?? pagination.hasMore ?? nextOffset !== null),
    },
  };
}

function runWhenIdle(task) {
  if (typeof window === "undefined") return null;
  if ("requestIdleCallback" in window) {
    return window.requestIdleCallback(task, { timeout: 1600 });
  }
  return window.setTimeout(task, 350);
}

function cancelIdleTask(id) {
  if (id == null || typeof window === "undefined") return;
  if ("cancelIdleCallback" in window) window.cancelIdleCallback(id);
  else window.clearTimeout(id);
}

function MotifBackdrop({ image, variant = "library" }) {
  const isDesk = variant === "desk";
  const imageTone = isDesk
    ? "saturate(0.9) brightness(0.68) contrast(1.04)"
    : "saturate(0.82) brightness(0.62) contrast(1.08)";
  const veil = isDesk
    ? "linear-gradient(90deg, rgba(25,8,13,0.94) 0%, rgba(27,11,16,0.9) 48%, rgba(74,28,39,0.7) 100%)"
    : "linear-gradient(90deg, rgba(22,7,11,0.94) 0%, rgba(34,16,23,0.88) 52%, rgba(58,20,29,0.7) 100%)";
  const glow = isDesk
    ? "radial-gradient(ellipse 54% 62% at 78% 44%, rgba(216,185,122,0.18), transparent 70%)"
    : "radial-gradient(ellipse 58% 58% at 78% 38%, rgba(216,185,122,0.14), transparent 72%)";

  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      <img
        src={optimizedImageUrl(image, { width: 1800, quality: 88 })}
        alt=""
        loading="lazy"
        decoding="async"
        className={`h-full w-full object-cover ${isDesk ? "object-[center_52%]" : "object-[center_60%]"}`}
        style={{ filter: imageTone }}
      />
      <div className="absolute inset-0" style={{ background: veil }} />
      <div className="absolute inset-0" style={{ background: glow }} />
      <div
        className="absolute inset-0"
        style={{ background: "linear-gradient(180deg, rgba(253,252,248,0.05), transparent 28%, rgba(0,0,0,0.22) 100%)" }}
      />
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(216,185,122,0.54), transparent)" }} />
      <div className="absolute inset-x-0 bottom-0 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(216,185,122,0.38), transparent)" }} />
    </div>
  );
}

export default function Home() {
  const { social } = useSettings();
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState(null);
  const [liveBooks, setLiveBooks] = useState([]);
  const [liveBookPage, setLiveBookPage] = useState({
    offset: 0,
    limit: HERO_BOOK_INITIAL_PAGE_SIZE,
    count: 0,
    total: 0,
    next_offset: null,
    has_more: false,
  });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const activeSocials = useMemo(() => SOCIALS.filter((item) => social?.[item.key]), [social]);

  useSEO({
    title: "The Earnalism Digital Library — Buy Reading Time. Read Beautifully.",
    description: "A quiet digital reading room for Bengali classics, literary fiction, young readers, business, technology and AI, history, adventure, science fiction, and gothic fiction.",
    image: HERO_IMG,
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadHomePayload() {
      try {
        const { data } = await api.get("/home", {
          params: { books_limit: HERO_BOOK_INITIAL_PAGE_SIZE, books_offset: 0 },
          signal: controller.signal,
        });
        const booksPage = normalizeBooksPage({ books: data?.books || [], pagination: data?.books_page }, 0);
        setCategories(data?.categories || []);
        setFeatured(data?.featured?.book || null);
        setLiveBooks(appendUniqueBooks([], booksPage.books));
        setLiveBookPage(booksPage.pagination);
      } catch (err) {
        if (controller.signal.aborted) return;
        const [categoryRes, featuredRes, booksRes] = await Promise.allSettled([
          api.get("/categories", { signal: controller.signal }),
          api.get("/featured", { signal: controller.signal }),
          api.get("/home/books", {
            params: { limit: HERO_BOOK_INITIAL_PAGE_SIZE, offset: 0 },
            signal: controller.signal,
          }),
        ]);
        if (categoryRes.status === "fulfilled") {
          setCategories(categoryRes.value.data || []);
        }
        if (featuredRes.status === "fulfilled") {
          setFeatured(featuredRes.value.data?.book || null);
        }
        if (booksRes.status === "fulfilled") {
          const booksPage = normalizeBooksPage(booksRes.value.data, 0);
          setLiveBooks(appendUniqueBooks([], booksPage.books));
          setLiveBookPage(booksPage.pagination);
        }
      }
    }

    loadHomePayload().catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!liveBookPage.has_more || liveBookPage.next_offset == null || liveBooks.length >= HERO_BOOK_RENDER_LIMIT) {
      return undefined;
    }
    const controller = new AbortController();
    const idleId = runWhenIdle(() => {
      const remainingSlots = Math.max(0, HERO_BOOK_RENDER_LIMIT - liveBooks.length);
      if (!remainingSlots) return;
      api.get("/home/books", {
        params: {
          limit: Math.min(HERO_BOOK_PAGE_SIZE, remainingSlots),
          offset: liveBookPage.next_offset,
        },
        signal: controller.signal,
      }).then(({ data }) => {
        if (controller.signal.aborted) return;
        const booksPage = normalizeBooksPage(data, liveBookPage.next_offset);
        startTransition(() => {
          setLiveBooks((current) => appendUniqueBooks(current, booksPage.books));
          setLiveBookPage(booksPage.pagination);
        });
      }).catch(() => {});
    });

    return () => {
      controller.abort();
      cancelIdleTask(idleId);
    };
  }, [liveBookPage.has_more, liveBookPage.next_offset, liveBooks.length]);

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
      <section className="relative isolate overflow-visible">
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
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-32 lg:pt-36 pb-56 sm:pb-48 lg:pb-52">
          <div className="max-w-4xl">
            <div className="italic-eyebrow text-[var(--brand-gold-soft)] mb-6 sm:mb-7 flex items-center gap-3" data-testid="hero-overline">
              <span className="h-px w-8 sm:w-10 bg-[var(--brand-gold)]/70" />
              <span className="text-[0.85rem] sm:text-[0.95rem]">The Earnalism Digital Library</span>
            </div>
            <h1 className="font-serif-light text-[2.6rem] sm:text-[3.5rem] md:text-6xl lg:text-7xl leading-[1.04] text-[#FDFCF8] tracking-normal text-balance drop-shadow-[0_2px_24px_rgba(0,0,0,0.45)]" data-testid="hero-headline">
              A quieter bookstore for readers who <span className="italic-accent text-[var(--brand-gold-soft)]">linger.</span>
            </h1>
            <p className="mt-5 sm:mt-6 font-serif-display italic text-lg sm:text-2xl text-[#F4EFEA]/90 max-w-xl leading-snug drop-shadow-[0_1px_18px_rgba(0,0,0,0.5)]">
              Preview every book before you pay. Read deeply when the day finally slows down.
            </p>
            <p className="mt-6 sm:mt-7 text-[0.95rem] sm:text-[1.05rem] text-[#F4EFEA]/80 max-w-md sm:max-w-lg leading-[1.75] font-light drop-shadow-[0_1px_18px_rgba(0,0,0,0.4)]">
              Discover thoughtful books across Bengali classics, literary fiction, business, technology, history, AI, and imagination. Earnalism keeps the shelves intentional so choosing your next read feels calm.
            </p>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-3 text-[0.73rem] sm:text-[0.78rem] uppercase tracking-[0.16em] text-[#FDFCF8]/90 drop-shadow-[0_1px_12px_rgba(0,0,0,0.55)]" aria-label="Earnalism reading promises">
              <span className="inline-flex items-center gap-2"><BookOpen size={14} strokeWidth={1.6} /> Preview before purchase</span>
              <span className="inline-flex items-center gap-2"><Sparkles size={14} strokeWidth={1.6} /> Curated shelves</span>
              <span className="inline-flex items-center gap-2"><Compass size={14} strokeWidth={1.6} /> Focused reading</span>
            </div>
            <div className="mt-10 sm:mt-12 flex flex-col sm:flex-row gap-3 sm:gap-4 sm:items-center">
              <Link to="/library" className="btn-primary w-full sm:w-auto gap-2" data-testid="hero-cta-read">
                <BookOpen size={16} strokeWidth={1.7} className="shrink-0" /> Start Reading
              </Link>
              <Link to="/pricing" className="btn-secondary w-full sm:w-auto !text-[#FDFCF8] !border-[var(--brand-gold)] hover:!bg-[var(--brand-gold)]/10" data-testid="hero-cta-pricing">
                <CreditCard size={15} strokeWidth={1.7} /> Buy Reading Time
              </Link>
              <Link to="/library" className="btn-link w-full sm:w-auto !text-[#FDFCF8]" data-testid="hero-cta-library">
                Explore Library <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
            </div>
          </div>
        </div>
        <div className="absolute inset-x-0 bottom-0 translate-y-1/2 z-10">
          <div className="w-full">
            <LiveCoverShowcase books={liveBooks} featured={featured} variant="band" totalBooks={liveBookPage.total} />
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-56 sm:pt-44 lg:pt-48 pb-12 sm:pb-16 lg:pb-20" id="collection">
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
                <BookCoverImage
                  book={featured}
                  alt={featured.title}
                  loading="lazy"
                  width={560}
                  widths={[360, 560, 760]}
                  sizes="(min-width: 1024px) 380px, (min-width: 640px) 52vw, 90vw"
                />
              </div>
            </div>
            <div className="lg:col-span-7 text-center lg:text-left">
              <div className="italic-eyebrow mb-4 sm:mb-5">Currently on the table</div>
              <h2 className="font-serif-light text-[2.25rem] sm:text-5xl lg:text-[3.5rem] text-burgundy leading-[1.06] tracking-tight">{featured.title}</h2>
              <p className="font-serif-display italic text-lg sm:text-2xl text-burgundy-soft mt-3 sm:mt-4 leading-snug">{featured.subtitle}</p>
              <div className="gold-rule-thin mt-6 mx-auto lg:mx-0" />
              <p className="text-charcoal-soft mt-6 sm:mt-7 leading-[1.85] max-w-2xl font-light text-[0.95rem] sm:text-base mx-auto lg:mx-0">{featured.description}</p>
              <div className="mt-6 flex flex-wrap justify-center gap-4 text-[0.72rem] uppercase tracking-[0.16em] text-charcoal-soft/80 lg:justify-start">
                <span className="inline-flex items-center gap-2"><BookOpen size={14} strokeWidth={1.6} /> Preview before purchase</span>
                <span className="inline-flex items-center gap-2"><Sparkles size={14} strokeWidth={1.6} /> Curated selection</span>
                <span className="inline-flex items-center gap-2"><Compass size={14} strokeWidth={1.6} /> Focused reading room</span>
              </div>
              <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 justify-center lg:justify-start">
                <Link to={`/reader/${featured.slug}`} className="btn-primary justify-center" data-testid="featured-preview">
                  <BookOpen size={16} strokeWidth={1.7} /> Read Preview
                </Link>
                <Link to={`/book/${featured.slug}#preview-payment`} className="btn-secondary justify-center" data-testid="featured-payment">
                  Preview & Pay
                </Link>
                <Link to={`/book/${featured.slug}`} className="btn-link justify-center" data-testid="featured-view">
                  Details <ArrowRight size={14} strokeWidth={1.7} />
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* WHY EARNALISM */}
      <section className="relative overflow-hidden bg-[#221017] text-[#FDFCF8]">
        <MotifBackdrop image={WHY_MOTIF_IMG} />
        <div className="relative max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-16 sm:py-20 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-end">
            <div className="lg:col-span-5">
              <div className="italic-eyebrow text-[var(--brand-gold-soft)] mb-4">Why The Earnalism</div>
              <h2 className="font-serif-light text-[2.35rem] sm:text-5xl lg:text-[3.75rem] leading-[1.03] tracking-normal text-balance">
                A library that lowers the room's <span className="italic-accent text-[var(--brand-gold-soft)]">volume.</span>
              </h2>
              <p className="mt-6 text-[#F4EFEA]/78 leading-[1.8] text-[0.98rem] sm:text-[1.05rem] font-light max-w-xl">
                After the shelves, the promise stays simple: fewer distractions, richer judgment, and a reading path that lets each book earn its place.
              </p>
              <Link to="/library" className="btn-secondary mt-8 !text-[#FDFCF8] !border-[var(--brand-gold-soft)] hover:!bg-[rgba(216,185,122,0.12)]" data-testid="why-library-link">
                Explore the shelves <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
            </div>

            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-5">
              {WHY_POINTS.map((point) => (
                <div key={point.title} className="rounded-lg border border-[#FDFCF8]/15 bg-[#FDFCF8]/[0.06] p-6 sm:p-7 backdrop-blur-sm" data-testid={`why-card-${point.title.toLowerCase().replace(/\s/g, '-')}`}>
                  <point.icon className="text-[var(--brand-gold-soft)]" size={24} strokeWidth={1.45} />
                  <div className="mt-8 text-[0.65rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]">{point.proof}</div>
                  <h3 className="font-serif-display text-[1.55rem] text-[#FDFCF8] mt-3 leading-snug">{point.title}</h3>
                  <p className="mt-4 text-[#F4EFEA]/72 leading-[1.75] text-[0.9rem] font-light">{point.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* FOUNDER NOTE */}
      <section className="bg-[#FDFCF8]">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-16 sm:py-20 lg:py-24 grid grid-cols-1 lg:grid-cols-12 gap-10 sm:gap-12 lg:gap-16 items-center">
          <div className="lg:col-span-6">
            <div className="relative overflow-hidden rounded-lg border border-brand-soft bg-[#221017] aspect-[5/4] sm:aspect-[16/11] lg:aspect-[4/5]">
              <img src={optimizedImageUrl(FOUNDER_IMG, { width: 940 })} alt="" loading="lazy" decoding="async" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#2a1218]/55 via-transparent to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-7">
                <div className="inline-flex items-center gap-2 rounded-full border border-[#FDFCF8]/35 bg-[#2a1218]/50 px-4 py-2 text-[0.65rem] uppercase tracking-[0.2em] text-[#FDFCF8] backdrop-blur">
                  <Feather size={13} strokeWidth={1.6} /> From the desk
                </div>
              </div>
            </div>
          </div>
          <div className="lg:col-span-6">
            <div className="italic-eyebrow mb-4 sm:mb-5">A note from the desk</div>
            <h2 className="font-serif-light text-[2.25rem] sm:text-5xl lg:text-[3.55rem] text-burgundy leading-[1.04] tracking-normal text-balance">
              A bookstore for the reader who still believes in <span className="italic-accent">depth.</span>
            </h2>
            <p className="text-charcoal-soft mt-6 sm:mt-7 leading-[1.85] text-[0.98rem] sm:text-[1.03rem] max-w-2xl font-light">
              The Earnalism began as a quiet rebellion against noisy bookshelves. A book is a long conversation: patient, particular, and worth the careful season it takes to write. The list stays small because the standard stays generous.
            </p>
            <div className="mt-8 sm:mt-10 grid grid-cols-1 sm:grid-cols-3 border-y border-brand-soft">
              {DESK_NOTES.map((note, i) => (
                <div key={note.title} className={`py-6 sm:px-5 ${i > 0 ? "border-t sm:border-t-0 sm:border-l border-brand-soft" : ""}`}>
                  <div className="text-[0.68rem] tracking-[0.24em] uppercase text-gold-deep">{note.number}</div>
                  <h3 className="font-serif-display text-[1.35rem] text-burgundy mt-3 leading-snug">{note.title}</h3>
                  <p className="text-charcoal-soft text-[0.88rem] leading-[1.65] mt-3 font-light">{note.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="relative overflow-hidden bg-[#1b0b10] text-[#FDFCF8]">
        <MotifBackdrop image={READING_CIRCLE_IMG} variant="desk" />
        <div className="relative max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-16 sm:py-20 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            <div className="lg:col-span-6">
              <div className="italic-eyebrow text-[var(--brand-gold-soft)] mb-4">From the Editor's Desk</div>
              <h2 className="font-serif-light text-[2.25rem] sm:text-5xl lg:text-[3.6rem] tracking-normal leading-[1.04] text-balance">
                Join the Earnalism <span className="italic-accent text-[var(--brand-gold-soft)]">Reading Circle.</span>
              </h2>
              <p className="text-[#F4EFEA]/76 mt-6 leading-[1.8] max-w-xl font-light text-[0.98rem] sm:text-[1.03rem]">
                Receive thoughtful book notes, new shelf arrivals, and curated reading recommendations written with the care of a private letter.
              </p>
              {activeSocials.length > 0 && (
                <nav className="mt-9" aria-label="Earnalism social links" data-testid="home-socials">
                  <div className="text-[0.64rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]/90">Follow the marginalia</div>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    {activeSocials.map(({ key, label, Icon }) => (
                      <a
                        key={key}
                        href={social[key]}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Visit Earnalism on ${label}`}
                        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#FDFCF8]/18 bg-[#FDFCF8]/[0.045] text-[#F4EFEA]/78 transition-colors duration-300 hover:border-[var(--brand-gold-soft)]/70 hover:bg-[rgba(216,185,122,0.1)] hover:text-[var(--brand-gold-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--brand-gold-soft)]"
                        data-testid={`home-social-${key}`}
                      >
                        <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                      </a>
                    ))}
                  </div>
                </nav>
              )}
            </div>
            <form onSubmit={subscribe} className="lg:col-span-6 rounded-lg border border-[#FDFCF8]/16 bg-[#FDFCF8]/[0.06] p-6 sm:p-8 lg:p-10 backdrop-blur-sm" data-testid="newsletter-card">
              <div className="flex items-center gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]">
                <Mail size={15} strokeWidth={1.6} /> Private dispatch
              </div>
              <div className="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-5 sm:gap-6">
                <input
                  required value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Your name" className="input-elegant !text-[#FDFCF8] !border-b-[#FDFCF8]/30 placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-name"
                />
                <input
                  required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="Your email" className="input-elegant !text-[#FDFCF8] !border-b-[#FDFCF8]/30 placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-email"
                />
                <div className="sm:col-span-2 flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between mt-3">
                  <p className="text-[#F4EFEA]/58 text-[0.78rem] leading-[1.6] font-light max-w-sm">
                    Quiet notes only. No noisy campaign rhythm.
                  </p>
                  <button disabled={submitting} type="submit" className="btn-primary w-full sm:w-auto justify-center !bg-[var(--brand-gold-soft)] !border-[var(--brand-gold-soft)] !text-[#241016] hover:!bg-[var(--brand-gold)] disabled:opacity-60" data-testid="newsletter-submit">
                    {submitting ? "Joining…" : "Join the Circle"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
