import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  CreditCard,
  Facebook,
  Instagram,
  Linkedin,
  Mail,
  ShieldCheck,
  Sparkles,
  Twitter,
  Youtube,
} from "lucide-react";
import { toast } from "sonner";
import BookCoverImage from "../components/BookCoverImage";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { normalizeSocialUrl } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import {
  DRACULA_COVER_IMAGE,
  DRACULA_CTA_EVENTS,
  KSHUDHITA_PASHAN_PIPELINE,
  LIVE_APPROVED_SLUG,
  PIPELINE_BOOKS,
  mergeDraculaBook,
  notifyUrl,
  readingPassUrl,
} from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";

const SOCIALS = [
  { key: "linkedin", label: "LinkedIn", Icon: Linkedin },
  { key: "twitter", label: "X", Icon: Twitter },
  { key: "instagram", label: "Instagram", Icon: Instagram },
  { key: "facebook", label: "Facebook", Icon: Facebook },
  { key: "youtube", label: "YouTube", Icon: Youtube },
];

function track(event, metadata = {}) {
  if (!event) return;
  trackFunnelEvent(event, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, ...metadata });
}

function trackPipelineInterest(event, ctaId, bookSlug = KSHUDHITA_PASHAN_PIPELINE.slug) {
  trackFunnelEvent(event, {
    source: "home_pipeline_shelf",
    book_slug: bookSlug,
    cta_id: ctaId,
    public: false,
  });
}

export default function Home() {
  const { social } = useSettings();
  const [dracula, setDracula] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const activeSocials = useMemo(() => (
    SOCIALS
      .map((item) => ({ ...item, url: normalizeSocialUrl(social?.[item.key]) }))
      .filter((item) => item.url)
  ), [social]);
  const liveBook = mergeDraculaBook(dracula);

  useSEO({
    title: "Step Into Dracula | The Earnalism Digital Library",
    description:
      "Earnalism is live with Dracula as its first approved classic reading release. Read Chapter 1 free, then continue with reading time as more classics move through a rights-safe pipeline.",
    image: liveBook.cover_image_url || DRACULA_COVER_IMAGE,
    imageAlt: "Custom Earnalism Dracula cover artwork",
    canonicalPath: "/",
  });

  useEffect(() => {
    trackFunnelEvent("bengali_gothic_pipeline_view", {
      source: "home",
      book_slug: KSHUDHITA_PASHAN_PIPELINE.slug,
      public: false,
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api.get(`/books/${LIVE_APPROVED_SLUG}`, { signal: controller.signal })
      .then((response) => setDracula(response.data))
      .catch(() => setDracula(null));
    return () => controller.abort();
  }, []);

  const subscribe = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const { data } = await api.post("/newsletter", { name, email });
      toast.success(data.message || "Welcome to the Reading Circle.");
      setName("");
      setEmail("");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="home-page">
      <section
        className="premium-landing-hero reference-library-hero relative isolate overflow-hidden text-[#FDFCF8]"
        data-testid="premium-landing-hero"
        data-approved-hero-max-height="650"
        style={{ "--reference-hero-image": "url('/assets/hero/golden-hour-library-hero.webp')" }}
      >
        <div className="reference-hero-grid mx-auto grid max-w-7xl grid-cols-1 gap-7 px-5 py-8 sm:px-8 sm:py-11 lg:grid-cols-12 lg:items-center lg:px-12 lg:py-12">
          <div className="reference-hero-copy lg:col-span-7">
            <div className="italic-eyebrow flex items-center gap-3 text-[var(--brand-gold-soft)]" data-testid="hero-overline">
              <span className="h-px w-7 bg-[var(--brand-gold)]/70" />
              <span>The Earnalism Digital Library</span>
            </div>
            <h1
              className="mt-4 font-serif-light text-[2.34rem] leading-[0.98] tracking-normal text-[#FDFCF8] text-balance min-[390px]:text-[2.62rem] sm:text-[3.75rem] lg:text-[4.45rem]"
              data-testid="hero-headline"
              aria-label="Step into the classics. Stay with the story."
            >
              Step into the classics.
              <span className="block text-[var(--brand-gold-soft)]">Stay with the story.</span>
            </h1>
            <p className="mt-3 max-w-xl font-serif-display text-base italic leading-snug text-[#F4EFEA]/92 sm:text-2xl">
              Timeless stories. Beautifully presented. Yours to read, reflect, and remember.
            </p>
            <p className="mt-4 max-w-2xl text-[0.88rem] font-light leading-[1.65] text-[#F4EFEA]/82 sm:text-[0.98rem] sm:leading-[1.75]">
              The Earnalism launch begins with one approved classic. Read Chapter 1 free, continue with reading time, and return to your place whenever you wish.
            </p>
            <div className="reference-hero-trust mt-5" aria-label="Earnalism launch trust signals">
              <span><ShieldCheck size={16} strokeWidth={1.6} /> Rights-safe & ethical</span>
              <span><BookOpen size={16} strokeWidth={1.6} /> Ad-free reading</span>
              <span><CreditCard size={16} strokeWidth={1.6} /> Reading time stays with you</span>
            </div>
            <div className="premium-hero-ctas mt-5 sm:mt-6" data-testid="hero-ctas">
              <Link
                to={`/reader/${LIVE_APPROVED_SLUG}`}
                className="btn-primary premium-hero-cta-primary justify-center gap-2"
                data-testid="hero-cta-read"
                onClick={() => track(DRACULA_CTA_EVENTS.homepagePrimary, { cta: "read_chapter_1_free" })}
              >
                <BookOpen size={16} strokeWidth={1.7} /> Read Chapter 1 Free
              </Link>
              <Link
                to={`/book/${LIVE_APPROVED_SLUG}`}
                className="btn-secondary justify-center !border-[var(--brand-gold)] !text-[#FDFCF8] hover:!bg-[var(--brand-gold)]/10"
                data-testid="hero-cta-start-dracula"
                onClick={() => track(DRACULA_CTA_EVENTS.startReading, { cta: "start_dracula" })}
              >
                Start Dracula
              </Link>
              <Link
                to={readingPassUrl("homepage_hero")}
                className="btn-link justify-center !text-[#FDFCF8]"
                data-testid="hero-cta-pricing"
                onClick={() => track(DRACULA_CTA_EVENTS.readingPass, { cta: "get_7_day_reading_pass" })}
              >
                Get 7-Day Reading Pass <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
            </div>
            <p className="mt-3 max-w-xl text-[0.66rem] uppercase tracking-[0.16em] text-[var(--brand-gold-soft)]/92 sm:text-[0.72rem]">
              Chapter 1 is free. Reading time is used only while you read.
            </p>
          </div>

          <div className="reference-dracula-stage lg:col-span-5" data-testid="hero-dracula-card">
            <div className="reference-dracula-book-object reference-dracula-book-object--hardcopy">
              <div
                className="reference-dracula-hardcopy-shell"
                data-testid="hero-dracula-cover-frame"
                data-no-white-edge="true"
              >
                <img
                  src="/assets/books/dracula/dracula-hero-hardcopy.webp"
                  alt="Hard-copy Dracula book object with approved classic reading release plaque"
                  loading="eager"
                  fetchPriority="high"
                  width="572"
                  height="665"
                  className="reference-dracula-hardcopy-img"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        className="reference-pipeline-shelf"
        data-testid="bengali-gothic-pipeline-shelf"
        aria-labelledby="bengali-gothic-pipeline-title"
      >
        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12 lg:py-12">
          <div className="mb-7">
            <div className="overline mb-2">Shelf 2</div>
            <h2 id="bengali-gothic-pipeline-title" className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
              Coming Through the Rights-Safe Pipeline
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-charcoal-soft">
              These books are not live products yet. They have Notify Me CTAs only, and no reader, checkout, or audiobook access.
            </p>
          </div>
          <div className="reference-pipeline-row" data-testid="pipeline-books">
            {PIPELINE_BOOKS.slice(0, 4).map((book, index) => {
              const title = book.displayTitle || book.title;
              const hasCover = Boolean(book.cover_image_url || book.cover_url || book.thumbnail_url);
              const isKshudhita = book.slug === KSHUDHITA_PASHAN_PIPELINE.slug;
              return (
                <article key={book.slug} className="reference-pipeline-card" data-testid={`pipeline-card-${book.slug}`}>
                  <div className="reference-pipeline-cover" data-testid={`pipeline-cover-${book.slug}`}>
                    {hasCover ? (
                      <BookCoverImage
                        book={book}
                        alt={`${title} cover artwork`}
                        loading={index < 4 ? "eager" : "lazy"}
                        width={260}
                        widths={[180, 260, 360]}
                        sizes="(min-width: 1024px) 112px, 32vw"
                        fallback={title.slice(0, 1)}
                      />
                    ) : (
                      <div className="reference-pipeline-placeholder" aria-label={`${title} cover placeholder`}>
                        <Sparkles size={22} strokeWidth={1.35} aria-hidden="true" />
                        <span>{title}</span>
                      </div>
                    )}
                  </div>
                  <div className="reference-pipeline-copy">
                    <div className="reference-pipeline-status">Coming Soon</div>
                    <h3>{title}</h3>
                    {book.titleNative && <p className="reference-pipeline-native">{book.titleNative}</p>}
                    <p className="reference-pipeline-author">by {book.author}</p>
                    <Link
                      to={notifyUrl(book.slug)}
                      className="reference-pipeline-notify"
                      data-testid={`pipeline-notify-${book.slug}`}
                      onClick={() => {
                        if (isKshudhita) {
                          trackPipelineInterest("kshudhita_pashan_notify_click", "pipeline-kshudhita-notify", book.slug);
                        } else {
                          track(DRACULA_CTA_EVENTS.notifyMe, { future_title: book.slug });
                        }
                      }}
                    >
                      Notify Me
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-[#1b0b10] text-[#FDFCF8]">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-12 lg:px-12 lg:py-24">
          <div className="lg:col-span-6">
            <div className="italic-eyebrow mb-4 text-[var(--brand-gold-soft)]">Reading Circle</div>
            <h2 className="font-serif-light text-4xl leading-tight sm:text-5xl">Follow the controlled launch.</h2>
            <p className="mt-6 max-w-xl text-[#F4EFEA]/76 leading-[1.8]">
              Receive Dracula reading notes and updates as future classics move from rights review to controlled release.
            </p>
            {activeSocials.length > 0 && (
              <nav className="mt-9" aria-label="Earnalism social links" data-testid="home-socials">
                <div className="text-[0.64rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]/90">Follow the reading room</div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {activeSocials.map(({ key, label, Icon, url }) => (
                    <a
                      key={key}
                      href={url}
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
          <form onSubmit={subscribe} className="rounded-lg border border-[#FDFCF8]/16 bg-[#FDFCF8]/[0.06] p-6 backdrop-blur-sm sm:p-8 lg:col-span-6 lg:p-10" data-testid="newsletter-card" aria-describedby="newsletter-description">
            <div className="flex items-center gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]">
              <Mail size={15} strokeWidth={1.6} /> Private dispatch
            </div>
            <p id="newsletter-description" className="mt-4 text-sm leading-relaxed text-[#F4EFEA]/70">
              Join for Dracula reading notes and pipeline updates. No audiobook or paid campaign is live from this form.
            </p>
            <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2">
              <label>
                <span className="sr-only">Your name</span>
                <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" className="input-elegant !border-b-[#FDFCF8]/30 !text-[#FDFCF8] placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-name" aria-label="Your name" />
              </label>
              <label>
                <span className="sr-only">Your email</span>
                <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Your email" className="input-elegant !border-b-[#FDFCF8]/30 !text-[#FDFCF8] placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-email" aria-label="Your email" />
              </label>
            </div>
            <button type="submit" disabled={submitting} className="btn-primary mt-8 w-full justify-center" data-testid="newsletter-submit">
              {submitting ? "Joining..." : "Join the Reading Circle"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
