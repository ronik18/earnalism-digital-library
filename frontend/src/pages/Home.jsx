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
  LockKeyhole,
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
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import {
  DRACULA_CHAPTER_COUNT,
  DRACULA_CTA_EVENTS,
  DRACULA_RIGHTS_NOTE,
  DRACULA_SOURCE_NOTE,
  KSHUDHITA_PASHAN_PIPELINE,
  LIVE_APPROVED_SLUG,
  PIPELINE_BOOKS,
  mergeDraculaBook,
  notifyUrl,
  readingPassUrl,
} from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1920&q=90";

const SOCIALS = [
  { key: "linkedin", label: "LinkedIn", Icon: Linkedin },
  { key: "twitter", label: "X", Icon: Twitter },
  { key: "instagram", label: "Instagram", Icon: Instagram },
  { key: "facebook", label: "Facebook", Icon: Facebook },
  { key: "youtube", label: "YouTube", Icon: Youtube },
];

function track(event, metadata = {}) {
  trackFunnelEvent(event, { book: LIVE_APPROVED_SLUG, ...metadata });
}

function trackPipelineInterest(event, ctaId) {
  trackFunnelEvent(event, {
    source: "home_pipeline_shelf",
    book_slug: KSHUDHITA_PASHAN_PIPELINE.slug,
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
  const activeSocials = useMemo(() => SOCIALS.filter((item) => social?.[item.key]), [social]);
  const liveBook = mergeDraculaBook(dracula);

  useSEO({
    title: "Begin with Dracula | The Earnalism Digital Library",
    description:
      "Earnalism is live with Dracula as its first approved Tier A core reading release. Read Chapter 1 free, then continue with reading time as more classics move through a rights-safe pipeline.",
    image: liveBook.cover_image_url || HERO_IMG,
    imageAlt: "Dracula on Earnalism",
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
      <section className="relative isolate overflow-hidden bg-[#16090d] text-[#FDFCF8]">
        <div className="absolute inset-0 -z-10">
          <img
            src={HERO_IMG}
            alt=""
            loading="eager"
            fetchPriority="high"
            decoding="async"
            className="h-full w-full object-cover"
            style={{ filter: "saturate(0.9) brightness(0.62)" }}
          />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(18,7,11,0.94)_0%,rgba(32,12,18,0.86)_50%,rgba(32,12,18,0.28)_100%)]" />
          <div className="absolute inset-x-0 bottom-0 h-1/3 bg-[linear-gradient(to_top,#F4EFEA_0%,rgba(244,239,234,0.62)_50%,transparent_100%)]" />
        </div>

        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-12 px-5 pb-24 pt-24 sm:px-8 sm:pt-32 lg:grid-cols-12 lg:px-12 lg:pb-32 lg:pt-36">
          <div className="lg:col-span-7">
            <div className="italic-eyebrow mb-6 flex items-center gap-3 text-[var(--brand-gold-soft)]" data-testid="hero-overline">
              <span className="h-px w-10 bg-[var(--brand-gold)]/70" />
              <span>The Earnalism Digital Library</span>
            </div>
            <h1
              className="font-serif-light text-[2.8rem] leading-[1.02] tracking-normal text-[#FDFCF8] text-balance sm:text-6xl lg:text-7xl"
              data-testid="hero-headline"
              aria-label="Begin with Dracula."
            >
              Begin with <span className="italic-accent text-[var(--brand-gold-soft)]">Dracula.</span>
            </h1>
            <p className="mt-6 max-w-xl font-serif-display text-xl italic leading-snug text-[#F4EFEA]/90 sm:text-2xl">
              A quiet digital reading room for timeless books.
            </p>
            <p className="mt-6 max-w-2xl text-[1rem] font-light leading-[1.8] text-[#F4EFEA]/80">
              The Earnalism controlled launch starts with one approved classic. Read Chapter 1 free. Continue with a 7-day reading pass. More books are coming through the rights-safe pipeline.
            </p>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-3 text-[0.74rem] uppercase tracking-[0.16em] text-[#FDFCF8]/90" aria-label="Dracula launch facts">
              <span className="inline-flex items-center gap-2"><ShieldCheck size={14} strokeWidth={1.6} /> {DRACULA_RIGHTS_NOTE}</span>
              <span className="inline-flex items-center gap-2"><BookOpen size={14} strokeWidth={1.6} /> Chapter 1 free</span>
              <span className="inline-flex items-center gap-2"><Headphones size={14} strokeWidth={1.6} /> Audio not available yet</span>
            </div>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap" data-testid="hero-ctas">
              <Link
                to={`/reader/${LIVE_APPROVED_SLUG}`}
                className="btn-primary justify-center gap-2"
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
              <Link
                to="/library?category=pipeline"
                className="btn-link justify-center !text-[#FDFCF8]"
                data-testid="hero-cta-pipeline"
                onClick={() => track(DRACULA_CTA_EVENTS.notifyMe, { cta: "explore_pipeline_library" })}
              >
                Explore Pipeline / Library <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5">
            <div className="rounded-lg border border-[#FDFCF8]/16 bg-[#FDFCF8]/[0.08] p-5 shadow-[0_40px_90px_-40px_rgba(0,0,0,0.7)] backdrop-blur" data-testid="hero-dracula-card">
              <div className="mx-auto aspect-[3/4] max-w-[280px] overflow-hidden rounded-md border border-[#FDFCF8]/18 bg-[#F4EFEA]">
                <BookCoverImage book={liveBook} alt="Dracula by Bram Stoker cover" loading="eager" width={420} widths={[300, 420, 640]} sizes="(min-width: 1024px) 280px, 70vw" />
              </div>
              <div className="mt-5 text-center">
                <div className="text-[0.68rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]">Live controlled release</div>
                <h2 className="mt-2 font-serif-display text-3xl text-[#FDFCF8]">Dracula</h2>
                <p className="mt-2 text-[0.82rem] uppercase tracking-[0.14em] text-[#F4EFEA]/76">by Bram Stoker</p>
                <p className="mx-auto mt-4 max-w-sm text-sm leading-relaxed text-[#F4EFEA]/72">
                  {DRACULA_CHAPTER_COUNT} chapters. Source: {DRACULA_SOURCE_NOTE}. Audio is not available yet.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="surface-warm border-y border-brand-soft" data-testid="dracula-journey-map">
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:px-12 lg:py-16">
          <div className="mb-8 grid gap-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
            <div>
              <div className="overline mb-3">How the reading room works</div>
              <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">
                Preview first. Add time only when you want to stay.
              </h2>
            </div>
            <p className="max-w-2xl text-sm leading-[1.85] text-charcoal-soft sm:text-base">
              Dracula is the only live room today. Chapter 1 opens free, later chapters ask for sign-in and reading time, and your place follows you back through the library or account page.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4" aria-label="Dracula reading journey">
            <JourneyStep number="01" title="Read Chapter 1 free" body="Open the preview before paying. No audio controls or hidden catalog claims are part of this launch." />
            <JourneyStep number="02" title="Choose quiet reading time" body="Reading time is credited to your wallet after confirmation and is used only while you read." />
            <JourneyStep number="03" title="Return from account or library" body="Sign in to resume Dracula, review your wallet, and continue from the controlled live shelf." />
            <JourneyStep number="04" title="Future rooms stay gated" body="Kshudhita Pashan and other classics remain Coming Soon until source, rights, and QA pass." />
          </div>
        </div>
      </section>

      <section className="surface-warm border-y border-brand-soft" data-testid="controlled-carousel-section">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-12">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="overline mb-3">Launch carousel</div>
              <h2 className="font-serif-light text-4xl leading-tight text-burgundy sm:text-5xl">One live room. More are in review.</h2>
            </div>
            <span className="text-sm leading-relaxed text-charcoal-soft">No autoplay. No fake book count. Only Dracula has reading CTAs.</span>
          </div>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3" role="list" aria-label="Dracula controlled launch slides">
            <CarouselSlide
              icon={BookOpen}
              eyebrow="Slide 1"
              title="Dracula by Bram Stoker"
              body="Live controlled release. Chapter 1 is free, and the core reading journey continues through reading time."
              primary={{ label: "Read Chapter 1 Free", to: `/reader/${LIVE_APPROVED_SLUG}`, event: DRACULA_CTA_EVENTS.previewStart }}
              secondary={{ label: "Start Dracula", to: `/book/${LIVE_APPROVED_SLUG}`, event: DRACULA_CTA_EVENTS.startReading }}
            />
            <CarouselSlide
              icon={ShieldCheck}
              eyebrow="Slide 2"
              title="Rights-safe source"
              body={`Source: ${DRACULA_SOURCE_NOTE}. This launch is scoped to the approved core reading candidate only.`}
              primary={{ label: "View source note", to: `/book/${LIVE_APPROVED_SLUG}#rights-note`, event: DRACULA_CTA_EVENTS.bookView }}
            />
            <CarouselSlide
              icon={Sparkles}
              eyebrow="Slide 3"
              title="7-Day Dracula Reading Path"
              body="The reading path is being prepared as a guided layer. The live product today is the Dracula core reader."
              primary={{ label: "Notify Me", to: notifyUrl("dracula-reading-path"), event: DRACULA_CTA_EVENTS.notifyMe }}
            />
          </div>
        </div>
      </section>

      <section
        className="relative overflow-hidden border-y border-brand-soft bg-[#221017] text-[#FDFCF8]"
        data-testid="bengali-gothic-pipeline-shelf"
        aria-labelledby="bengali-gothic-pipeline-title"
      >
        <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-12 lg:px-12 lg:py-24">
          <div className="lg:col-span-7">
            <div className="italic-eyebrow mb-4 text-[var(--brand-gold-soft)]">Coming Through the Rights-Safe Pipeline</div>
            <h2 id="bengali-gothic-pipeline-title" className="font-serif-light text-4xl leading-tight sm:text-5xl lg:text-[3.65rem]">
              {KSHUDHITA_PASHAN_PIPELINE.headline}
            </h2>
            <p className="mt-5 font-serif-display text-xl italic leading-snug text-[var(--brand-gold-soft)] sm:text-2xl">
              {KSHUDHITA_PASHAN_PIPELINE.subcopy}
            </p>
            <p className="mt-6 max-w-2xl text-[#F4EFEA]/76 leading-[1.85] font-light">
              This Bengali Gothic candidate remains pipeline-only. Source evidence, CC BY-SA attribution/share-alike compliance, text QA,
              pronunciation review, and provider audio QA must pass before any reader or listening access goes live.
            </p>
          </div>
          <div className="lg:col-span-5">
            <div className="rounded-lg border border-[#FDFCF8]/16 bg-[#FDFCF8]/[0.065] p-6 backdrop-blur-sm sm:p-8" data-testid="pipeline-kshudhita-pashan">
              <div className="text-[0.64rem] uppercase tracking-[0.28em] text-[var(--brand-gold-soft)]">Bengali Gothic Candidate</div>
              <h3 className="mt-4 font-serif-light text-3xl leading-tight sm:text-4xl">{KSHUDHITA_PASHAN_PIPELINE.titleBn}</h3>
              <p className="mt-2 text-[#F4EFEA]/68">{KSHUDHITA_PASHAN_PIPELINE.titleEn} by {KSHUDHITA_PASHAN_PIPELINE.author}</p>
              <p className="mt-6 text-sm leading-[1.75] text-[#F4EFEA]/72">
                Status: {KSHUDHITA_PASHAN_PIPELINE.statusLabel}
              </p>
              <div className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Link
                  to={notifyUrl(KSHUDHITA_PASHAN_PIPELINE.slug)}
                  className="btn-secondary justify-center !border-[var(--brand-gold-soft)] !text-[#FDFCF8] hover:!bg-[rgba(216,185,122,0.12)]"
                  data-testid="pipeline-kshudhita-notify"
                  onClick={() => trackPipelineInterest("kshudhita_pashan_notify_click", "pipeline-kshudhita-notify")}
                >
                  Notify Me
                </Link>
                <button
                  type="button"
                  className="btn-link justify-center !text-[#FDFCF8]"
                  data-testid="pipeline-reading-circle"
                  onClick={() => {
                    trackPipelineInterest("bengali_gothic_reading_circle_click", "pipeline-reading-circle");
                    toast.message("Reading Circle interest noted.");
                  }}
                >
                  Reading Circle
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-12" data-testid="dracula-shelves">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <div className="overline mb-4">Live Controlled Release</div>
            <h2 className="font-serif-light text-4xl leading-tight text-burgundy sm:text-5xl">Dracula is the only open reading room.</h2>
            <p className="mt-5 text-charcoal-soft leading-[1.85]">
              Earnalism is live, but intentionally narrow: one approved Tier A classic, one core reading experience, and a visible rights trail.
            </p>
          </div>
          <div className="lg:col-span-7">
            <div className="card-elegant p-7 sm:p-9" data-testid="home-live-dracula">
              <div className="flex flex-col gap-7 sm:flex-row">
                <div className="w-full max-w-[180px] shrink-0 overflow-hidden rounded-md border border-brand-soft bg-ivory-warm">
                  <BookCoverImage book={liveBook} alt="Dracula cover" loading="lazy" width={320} widths={[220, 320, 480]} sizes="180px" />
                </div>
                <div className="min-w-0 flex-1">
                  <span className="overline">Gothic fiction</span>
                  <h3 className="mt-3 font-serif-display text-3xl leading-tight text-burgundy">Dracula</h3>
                  <p className="mt-2 text-[0.85rem] uppercase tracking-[0.14em] text-charcoal-soft">by Bram Stoker</p>
                  <ul className="mt-5 grid gap-2 text-sm leading-relaxed text-charcoal-soft sm:grid-cols-2">
                    <li className="inline-flex gap-2"><CheckCircle2 size={16} className="mt-0.5 text-gold" /> 27 chapters</li>
                    <li className="inline-flex gap-2"><CheckCircle2 size={16} className="mt-0.5 text-gold" /> Chapter 1 free</li>
                    <li className="inline-flex gap-2"><CheckCircle2 size={16} className="mt-0.5 text-gold" /> Tier A approved</li>
                    <li className="inline-flex gap-2"><LockKeyhole size={16} className="mt-0.5 text-gold" /> Audio not available yet</li>
                  </ul>
                  <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                    <Link to={`/reader/${LIVE_APPROVED_SLUG}`} className="btn-secondary justify-center" data-testid="home-dracula-preview" onClick={() => track(DRACULA_CTA_EVENTS.previewStart, { cta: "live_shelf_preview" })}>
                      Read Chapter 1 Free
                    </Link>
                    <Link to={`/book/${LIVE_APPROVED_SLUG}`} className="btn-primary justify-center" data-testid="home-dracula-start" onClick={() => track(DRACULA_CTA_EVENTS.startReading, { cta: "live_shelf_start" })}>
                      Start Dracula
                    </Link>
                    <Link to={readingPassUrl("home_live_shelf")} className="btn-link justify-center" data-testid="home-dracula-pass" onClick={() => track(DRACULA_CTA_EVENTS.readingPass, { cta: "live_shelf_pass" })}>
                      Get Reading Pass <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-14 border-t border-brand-soft pt-12">
          <div className="mb-7 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="overline mb-3">Coming Through The Rights-Safe Pipeline</div>
              <h2 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-4xl">Future rooms are visible, not readable yet.</h2>
            </div>
            <p className="max-w-md text-sm leading-relaxed text-charcoal-soft">Pipeline titles have no reader links until their approval packet is complete.</p>
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4" data-testid="pipeline-books">
            {PIPELINE_BOOKS.map((book) => (
              <article key={book.slug} className="card-elegant p-6" data-testid={`pipeline-card-${book.slug}`}>
                <div className="overline">{book.category_slug.replace(/-/g, " ")}</div>
                <h3 className="mt-4 min-h-[4rem] font-serif-display text-[1.55rem] leading-tight text-burgundy">{book.title}</h3>
                <p className="mt-3 text-[0.78rem] uppercase tracking-[0.14em] text-charcoal-soft">by {book.author}</p>
                <p className="mt-5 text-sm leading-relaxed text-charcoal-soft">{book.statusLabel}. Coming Soon.</p>
                <Link
                  to={notifyUrl(book.slug)}
                  className="mt-6 inline-flex rounded-full border border-[var(--brand-gold)] px-4 py-2 text-[0.68rem] uppercase tracking-[0.2em] text-burgundy transition-colors hover:bg-[var(--brand-gold)]/10"
                  data-testid={`pipeline-notify-${book.slug}`}
                  onClick={() => track(DRACULA_CTA_EVENTS.notifyMe, { future_title: book.slug })}
                >
                  Notify Me
                </Link>
              </article>
            ))}
          </div>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card-elegant p-7 sm:p-9" data-testid="reading-path-draft">
            <div className="overline mb-3">Reading Paths</div>
            <h3 className="font-serif-display text-3xl text-burgundy">Dracula 7-Day Reading Path</h3>
            <p className="mt-5 text-charcoal-soft leading-[1.8]">The guided path is in draft. The live release today is the core Dracula reader.</p>
            <Link to={notifyUrl("dracula-reading-path")} className="btn-secondary mt-7" onClick={() => track(DRACULA_CTA_EVENTS.notifyMe, { future_title: "dracula-reading-path" })}>
              Notify Me
            </Link>
          </div>
          <div className="card-elegant p-7 sm:p-9" data-testid="audiobook-unavailable">
            <div className="overline mb-3">Audiobooks</div>
            <h3 className="font-serif-display text-3xl text-burgundy">Audio is being prepared through QA.</h3>
            <p className="mt-5 text-charcoal-soft leading-[1.8]">Dracula audiobook is not available yet. There are no play buttons, waveforms, or audiobook CTAs in this launch.</p>
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
                <div className="text-[0.64rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]/90">Follow Earnalism</div>
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
          <form onSubmit={subscribe} className="rounded-lg border border-[#FDFCF8]/16 bg-[#FDFCF8]/[0.06] p-6 backdrop-blur-sm sm:p-8 lg:col-span-6 lg:p-10" data-testid="newsletter-card">
            <div className="flex items-center gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-[var(--brand-gold-soft)]">
              <Mail size={15} strokeWidth={1.6} /> Private dispatch
            </div>
            <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2">
              <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" className="input-elegant !border-b-[#FDFCF8]/30 !text-[#FDFCF8] placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-name" />
              <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Your email" className="input-elegant !border-b-[#FDFCF8]/30 !text-[#FDFCF8] placeholder:!text-[#FDFCF8]/45" data-testid="newsletter-email" />
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

function JourneyStep({ number, title, body }) {
  return (
    <article className="rounded-lg border border-brand-soft bg-white/45 p-5 shadow-[0_18px_45px_-38px_rgba(74,28,39,0.45)]" data-testid={`dracula-journey-step-${number}`}>
      <div className="font-serif-display text-2xl text-gold-deep">{number}</div>
      <h3 className="mt-4 font-serif-display text-xl leading-tight text-burgundy">{title}</h3>
      <p className="mt-3 text-sm leading-[1.75] text-charcoal-soft">{body}</p>
    </article>
  );
}

function CarouselSlide({ icon: Icon, eyebrow, title, body, primary, secondary }) {
  return (
    <article className="card-elegant flex min-h-[20rem] flex-col p-7" role="listitem">
      <Icon size={25} strokeWidth={1.55} className="text-gold" aria-hidden="true" />
      <div className="overline mt-7">{eyebrow}</div>
      <h3 className="mt-4 font-serif-display text-3xl leading-tight text-burgundy">{title}</h3>
      <p className="mt-5 flex-1 text-charcoal-soft leading-[1.75]">{body}</p>
      <div className="mt-7 flex flex-col gap-3 sm:flex-row">
        {primary && (
          <Link to={primary.to} className="btn-secondary justify-center" data-testid={`carousel-${primary.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} onClick={() => track(primary.event, { cta: primary.label })}>
            {primary.label}
          </Link>
        )}
        {secondary && (
          <Link to={secondary.to} className="btn-link justify-center" onClick={() => track(secondary.event, { cta: secondary.label })}>
            {secondary.label} <ArrowRight size={14} />
          </Link>
        )}
      </div>
    </article>
  );
}
