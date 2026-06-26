import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CreditCard,
  Facebook,
  Headphones,
  Instagram,
  Linkedin,
  Mail,
  ShieldCheck,
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
  DRACULA_CHAPTER_COUNT,
  DRACULA_COVER_IMAGE,
  DRACULA_CTA_EVENTS,
  DRACULA_RIGHTS_NOTE,
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

const FUTURE_STACK = PIPELINE_BOOKS.filter((book) => book.slug !== KSHUDHITA_PASHAN_PIPELINE.slug).slice(0, 3);
const HERO_LIBRARY_BACKGROUND_IMAGE = "/assets/hero/golden-hour-library-hero.webp";

function track(event, metadata = {}) {
  if (!event) return;
  trackFunnelEvent(event, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, ...metadata });
}

function trackPipelineInterest(event, ctaId) {
  void event;
  void ctaId;
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
    title: "Begin with Dracula | The Earnalism Digital Library",
    description:
      "Begin with Dracula in The Earnalism's quiet digital reading room. Chapter 1 is free, reading-time passes support continuation, and future classics remain in rights-safe preparation.",
    image: liveBook.cover_image_url || DRACULA_COVER_IMAGE,
    imageAlt: "Custom Earnalism Dracula cover artwork",
    canonicalPath: "/",
  });

  useEffect(() => {
    trackFunnelEvent("homepage_view", {
      path: "/",
      launch_status: "LIVE_VERIFIED",
      public_audio_status: "PUBLIC_AUDIO_RELEASE_BLOCKED",
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
    <div className="luxury-home-page" data-testid="home-page">
      <section
        className="premium-landing-hero relative isolate overflow-hidden text-[#FDFCF8]"
        data-testid="premium-landing-hero"
        data-approved-hero-max-height="620"
        style={{ "--premium-hero-library-bg": `url("${HERO_LIBRARY_BACKGROUND_IMAGE}")` }}
      >
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-5 pb-9 pt-8 sm:px-8 sm:pb-12 sm:pt-11 lg:grid-cols-12 lg:items-center lg:gap-10 lg:px-12 lg:py-14">
          <div className="premium-hero-copy-zone lg:col-span-7">
            <div className="mb-3 flex items-center justify-between gap-4 sm:mb-4">
              <div className="italic-eyebrow flex items-center gap-3 text-[var(--brand-gold-soft)]" data-testid="hero-overline">
                <span className="h-px w-7 bg-[var(--brand-gold)]/70" />
                <span>The Earnalism Digital Library</span>
              </div>
              <div className="premium-dracula-mobile-object lg:hidden" aria-hidden="true">
                <BookCoverImage
                  book={liveBook}
                  alt=""
                  loading="eager"
                  width={220}
                  widths={[160, 220, 320]}
                  sizes="88px"
                  imgClassName="premium-dracula-cover-img"
                />
              </div>
            </div>
            <h1
              className="font-serif-light text-[2.36rem] leading-[0.99] tracking-normal text-[#FDFCF8] text-balance min-[390px]:text-[2.66rem] sm:text-[3.9rem] lg:text-[4.55rem] xl:text-[4.95rem]"
              data-testid="hero-headline"
              aria-label="Begin with Dracula."
            >
              Begin with <span className="italic-accent text-[var(--brand-gold-soft)]">Dracula.</span>
            </h1>
            <p className="mt-3 max-w-xl font-serif-display text-base italic leading-snug text-[#F4EFEA]/92 min-[390px]:text-lg sm:text-2xl lg:mt-4">
              A quiet digital reading room for timeless books.
            </p>
            <p className="mt-3 max-w-2xl text-[0.86rem] font-light leading-[1.6] text-[#F4EFEA]/82 min-[390px]:text-[0.92rem] sm:text-[1rem] sm:leading-[1.72] lg:mt-4">
              The Earnalism launch begins with one approved classic. Read Chapter 1 free, continue with reading time, and return to your place whenever you wish.
            </p>
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
            <div className="premium-launch-facts mt-4" aria-label="Dracula launch facts">
              <span className="inline-flex items-center gap-2"><ShieldCheck size={14} strokeWidth={1.6} /> {DRACULA_RIGHTS_NOTE}</span>
              <span className="inline-flex items-center gap-2"><BookOpen size={14} strokeWidth={1.6} /> Chapter 1 free</span>
              <span className="inline-flex items-center gap-2"><CheckCircle2 size={14} strokeWidth={1.6} /> Public-domain source verified</span>
              <span className="inline-flex items-center gap-2"><Headphones size={14} strokeWidth={1.6} /> Audiobook experience in private review</span>
            </div>
            <p className="premium-hero-revenue-note mt-3">Reading time is used only while you read.</p>
          </div>

          <div className="hidden lg:col-span-5 lg:block">
            <div className="premium-dracula-hero-card mx-auto max-w-[420px]" data-testid="hero-dracula-card">
              <div className="premium-dracula-cover-frame mx-auto aspect-[500/696] max-w-[255px] overflow-hidden" data-testid="hero-dracula-cover-frame">
                <BookCoverImage
                  book={liveBook}
                  alt="Custom Earnalism Dracula cover artwork"
                  loading="eager"
                  width={520}
                  widths={[360, 520, 720]}
                  sizes="(min-width: 1024px) 255px, 74vw"
                  imgClassName="premium-dracula-cover-img"
                />
              </div>
              <div className="mt-5 text-center">
                <div className="text-[0.62rem] uppercase tracking-[0.22em] text-[var(--brand-gold-soft)]">Approved classic reading release</div>
                <h2 className="mt-2 font-serif-display text-[2rem] text-[#FDFCF8]">Dracula</h2>
                <p className="mt-1 text-[0.72rem] uppercase tracking-[0.14em] text-[#F4EFEA]/76">by Bram Stoker</p>
                <p className="mx-auto mt-4 max-w-sm text-[0.82rem] leading-relaxed text-[#F4EFEA]/74">
                  {DRACULA_CHAPTER_COUNT} chapters. Public-domain source verified. Audiobook experience is in private review.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="luxury-reading-model" data-testid="dracula-reading-model">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:px-12 lg:py-16">
          <div>
            <div className="overline mb-3">Reading time, clearly priced</div>
            <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
              A revenue path that still feels like a library.
            </h2>
            <p className="mt-5 max-w-xl text-sm leading-[1.85] text-charcoal-soft sm:text-base">
              No fake urgency, no broad catalog claim, and no ownership promise. The reader opens with a free first chapter; paid continuation uses the wallet only when someone chooses more quiet time with Dracula.
            </p>
            <Link
              to={readingPassUrl("homepage_reading_model")}
              className="btn-primary mt-7"
              data-testid="reading-model-pass-cta"
              onClick={() => track(DRACULA_CTA_EVENTS.readingPass, { cta: "reading_model_pass" })}
            >
              See Reading Passes <ArrowRight size={15} />
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <ReadingModelCard
              icon={BookOpen}
              title="Open the room"
              body="Chapter 1 is free, so the first conversion is trust."
            />
            <ReadingModelCard
              icon={CreditCard}
              title="Add reading time"
              body="Passes credit a wallet; time is spent only while reading."
            />
            <ReadingModelCard
              icon={CheckCircle2}
              title="Return calmly"
              body="Sign in to resume Dracula through account or library."
            />
          </div>
        </div>
      </section>

      <section
        className="luxury-pipeline-shelf"
        data-testid="bengali-gothic-pipeline-shelf"
        aria-labelledby="bengali-gothic-pipeline-title"
      >
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-14 sm:px-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center lg:px-12 lg:py-16">
          <div className="pipeline-object" data-testid="pipeline-kshudhita-pashan">
            <div
              className="kshudhita-cover-stack"
              data-testid="pipeline-kshudhita-cover-stack"
              data-cover-status={KSHUDHITA_PASHAN_PIPELINE.coverStatus}
            >
              <img
                src={KSHUDHITA_PASHAN_PIPELINE.backCoverImage}
                alt=""
                loading="lazy"
                width="1024"
                height="1536"
                className="kshudhita-cover-stack__back"
                aria-hidden="true"
              />
              <img
                src={KSHUDHITA_PASHAN_PIPELINE.frontCoverImage}
                alt="Owner-provided Kshudhita Pashan front cover artwork"
                loading="lazy"
                width="1024"
                height="1536"
                className="kshudhita-cover-stack__front"
              />
            </div>
          </div>
          <div>
            <div className="italic-eyebrow mb-4 text-[var(--brand-gold-deep)]">A quiet pipeline glimpse</div>
            <h2 id="bengali-gothic-pipeline-title" className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
              {KSHUDHITA_PASHAN_PIPELINE.titleEn} is visible, not open.
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-[1.85] text-charcoal-soft sm:text-base">
              {KSHUDHITA_PASHAN_PIPELINE.titleBn} stays in rights-safe preparation while attribution, share-alike compliance, text QA, pronunciation review, and audiobook provider QA remain gated.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link
                to={notifyUrl(KSHUDHITA_PASHAN_PIPELINE.slug)}
                className="btn-secondary justify-center"
                data-testid="pipeline-kshudhita-notify"
                onClick={() => trackPipelineInterest("kshudhita_pashan_notify_click", "pipeline-kshudhita-notify")}
              >
                Notify Me
              </Link>
              <button
                type="button"
                className="btn-link justify-center"
                data-testid="pipeline-reading-circle"
                onClick={() => {
                  trackPipelineInterest("bengali_gothic_reading_circle_click", "pipeline-reading-circle");
                  toast.message("Reading Circle interest noted.");
                }}
              >
                Reading Circle
              </button>
            </div>
            <div className="pipeline-mini-stack mt-8" data-testid="pipeline-books">
              {FUTURE_STACK.map((book) => (
                <article key={book.slug} className="pipeline-mini-stack__item" data-testid={`pipeline-card-${book.slug}`}>
                  <span>{book.category_slug.replace(/-/g, " ")}</span>
                  <strong>{book.title}</strong>
                  <em>{book.statusLabel}</em>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="luxury-reading-circle" data-testid="reading-circle-section">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-5 py-14 sm:px-8 lg:grid-cols-12 lg:px-12 lg:py-16">
          <div className="lg:col-span-5">
            <div className="italic-eyebrow mb-4 text-[var(--brand-gold-deep)]">Reading Circle</div>
            <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
              Follow the launch without leaving the room.
            </h2>
            <p className="mt-5 max-w-xl text-sm leading-[1.85] text-charcoal-soft sm:text-base">
              Receive Dracula reading notes and quiet pipeline updates. This form does not make audiobooks public, does not start a paid campaign, and does not publish future titles.
            </p>
            {activeSocials.length > 0 ? (
              <nav className="home-social-rail mt-8" aria-label="Earnalism social links" data-testid="home-socials">
                <div className="home-social-rail__label">Follow Earnalism</div>
                <div className="home-social-rail__links">
                  {activeSocials.map(({ key, label, Icon, url }) => (
                    <a
                      key={key}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Visit Earnalism on ${label}`}
                      className="home-social-rail__link"
                      data-testid={`home-social-${key}`}
                    >
                      <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                    </a>
                  ))}
                </div>
              </nav>
            ) : (
              <div className="home-social-review mt-8" data-testid="home-socials-owner-review">
                Social icons appear here after owner-reviewed profile URLs are configured. No placeholder or fake social links are shown.
              </div>
            )}
          </div>
          <form onSubmit={subscribe} className="reading-circle-card lg:col-span-7" data-testid="newsletter-card" aria-describedby="newsletter-description">
            <div className="flex items-center gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-[var(--brand-gold-deep)]">
              <Mail size={15} strokeWidth={1.6} /> Private dispatch
            </div>
            <p id="newsletter-description" className="mt-4 text-sm leading-relaxed text-charcoal-soft">
              Join for Dracula notes and pipeline updates. Audiobook access stays private until release gates pass, and this form never publishes future titles.
            </p>
            <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2">
              <label>
                <span className="sr-only">Your name</span>
                <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" className="input-elegant" data-testid="newsletter-name" aria-label="Your name" />
              </label>
              <label>
                <span className="sr-only">Your email</span>
                <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Your email" className="input-elegant" data-testid="newsletter-email" aria-label="Your email" />
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

function ReadingModelCard({ icon: Icon, title, body }) {
  return (
    <article className="luxury-model-card">
      <Icon size={20} strokeWidth={1.55} className="text-gold-deep" aria-hidden="true" />
      <h3>{title}</h3>
      <p>{body}</p>
    </article>
  );
}
