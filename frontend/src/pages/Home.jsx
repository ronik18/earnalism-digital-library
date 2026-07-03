import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  CircleCheck,
  CreditCard,
  Facebook,
  Instagram,
  Linkedin,
  Mail,
  ShieldCheck,
  Twitter,
  Youtube,
} from "lucide-react";
import { toast } from "sonner";
import HeroBookObject from "../components/HeroBookObject";
import ShelfTwoSlideshow from "../components/ShelfTwoSlideshow";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import {
  BATCH_1_READER_ONLY_SLUGS,
  DRACULA_COVER_IMAGE,
  DRACULA_CTA_EVENTS,
  LIVE_APPROVED_SLUG,
  PIPELINE_BOOKS,
  mergeDraculaBook,
  readingPassUrl,
} from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";

const SOCIAL_ICONS = {
  email: Mail,
  facebook: Facebook,
  instagram: Instagram,
  linkedin: Linkedin,
  x: Twitter,
  youtube: Youtube,
};

function track(event, metadata = {}) {
  if (!event) return;
  trackFunnelEvent(event, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, ...metadata });
}

export default function Home() {
  const { social } = useSettings();
  const [dracula, setDracula] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);
  const liveBook = mergeDraculaBook(dracula);
  const homepagePipelineBooks = useMemo(
    () => PIPELINE_BOOKS.filter((book) => !BATCH_1_READER_ONLY_SLUGS.includes(book.slug)),
    [],
  );
  const shelfTwoBooks = useMemo(
    () =>
      homepagePipelineBooks.map((book, index) => ({
        id: book.slug,
        slug: book.slug,
        title: book.displayTitle || book.title,
        author: book.author,
        coverUrl: book.cover_image_url || book.thumbnail_url || book.back_cover_image_url || book.back_cover_thumbnail_url || "",
        description: book.short_description || "",
        statusLabel: book.statusLabel || "Rights-safe preparation",
        dominantColor: book.dominant_color || "",
        sequence: index + 1,
        status: "queued",
      })),
    [homepagePipelineBooks],
  );

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
      book_slug: LIVE_APPROVED_SLUG,
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
              <HeroBookObject
                href="https://theearnalism.com/book/dracula"
                coverSrc="/assets/books/dracula/dracula-front-cover-hero-polished.webp"
                alt="Dracula front cover"
                testId="hero-dracula-cover-frame"
                aria-label="Open Dracula book page"
                onClick={() => track(DRACULA_CTA_EVENTS.startReading, { cta: "hero_book_object" })}
              />
            </div>
          </div>
        </div>
      </section>

      <section
        className="reference-pipeline-shelf"
        data-testid="bengali-gothic-pipeline-shelf"
        aria-labelledby="bengali-gothic-pipeline-title"
      >
        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12 lg:py-12" data-testid="pipeline-books">
          <div className="mb-7">
            <div className="overline mb-2">Shelf II</div>
            <h2 id="bengali-gothic-pipeline-title" className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
              Coming Through the Rights-Safe Pipeline
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-charcoal-soft">
              A quieter second shelf for editions in preparation. These titles are visible as editorial promises only, with Notify Me CTAs and no reader, checkout, or audiobook access.
            </p>
            <p className="mt-3 max-w-2xl text-[0.68rem] uppercase tracking-[0.22em] text-[var(--brand-gold-deep)]/78">
              Real cover-led presentation where available. No placeholder launch claims.
            </p>
          </div>
          <ShelfTwoSlideshow books={shelfTwoBooks} />
        </div>
      </section>

      <section
        className="reference-reading-path"
        data-testid="reading-time-library-path"
        aria-labelledby="reading-time-library-path-title"
      >
        <div className="reference-reading-path__inner mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:px-12 lg:py-16">
          <div className="reference-reading-path__copy">
            <div className="overline mb-3">Reading time, clearly priced</div>
            <h2 id="reading-time-library-path-title">
              A revenue path that still feels like a library.
            </h2>
            <p>
              No fake urgency, no broad catalog claim, and no ownership promise. The reader opens with a free first chapter; paid continuation uses the wallet only when someone chooses more quiet time with Dracula.
            </p>
            <Link
              to={readingPassUrl("homepage_reading_path")}
              className="btn-primary reference-reading-path__cta"
              data-testid="reading-path-pricing-cta"
              onClick={() => track(DRACULA_CTA_EVENTS.readingPass, { cta: "see_reading_passes", source: "homepage_reading_path" })}
            >
              See Reading Passes <ArrowRight size={15} strokeWidth={1.7} />
            </Link>
          </div>
          <div className="reference-reading-path__cards" aria-label="How Earnalism reading time works">
            <article className="reference-reading-step">
              <BookOpen size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Open the room</h3>
              <p>Chapter 1 is free, so the first conversion is trust.</p>
            </article>
            <article className="reference-reading-step">
              <CreditCard size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Add reading time</h3>
              <p>Passes credit a wallet; time is spent only while reading.</p>
            </article>
            <article className="reference-reading-step">
              <CircleCheck size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Return calmly</h3>
              <p>Sign in to resume Dracula through account or library.</p>
            </article>
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
            {activeSocials.length > 0 ? (
              <nav className="mt-9" aria-label="Earnalism social links" data-testid="home-socials">
                <div className="text-[0.64rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]/90">Follow the reading room</div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {activeSocials.map(({ id, ariaLabel, external, Icon, url }) => (
                    <a
                      key={id}
                      href={url}
                      target={external ? "_blank" : undefined}
                      rel={external ? "noopener noreferrer" : undefined}
                      aria-label={ariaLabel}
                      className="home-social-rail__link"
                      data-testid={`home-social-${id}`}
                    >
                      <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                    </a>
                  ))}
                </div>
              </nav>
            ) : (
              <div className="home-social-review mt-9" data-testid="home-socials-owner-review">
                No placeholder or fake social links are shown.
              </div>
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
