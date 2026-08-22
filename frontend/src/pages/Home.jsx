import { lazy, startTransition, Suspense, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  BookText,
  CircleCheck,
  CreditCard,
  Facebook,
  Instagram,
  Languages,
  Linkedin,
  Mail,
  Headphones,
  ShieldCheck,
  Twitter,
  Youtube,
} from "lucide-react";
import { toast } from "sonner";
import DeferredMount from "../components/DeferredMount";
import PremiumHero from "../components/PremiumHero";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG } from "../lib/controlledLaunch";
import {
  fetchHomeHero,
  getHomeHeroCache,
  getHomeHeroSnapshot,
} from "../lib/homeSurfaces";
import useSEO from "../hooks/useSEO";

const HomeListeningRoom = lazy(() => import("../components/HomeListeningRoom"));
const HomeShelfArchitecture = lazy(() => import("../components/HomeShelfArchitecture"));

// HomeShelfArchitecture remains the compatibility name for the editorial Home mount.

const SOCIAL_ICONS = {
  email: Mail,
  facebook: Facebook,
  instagram: Instagram,
  linkedin: Linkedin,
  x: Twitter,
  youtube: Youtube,
};

const QUICK_PATHS = [
  {
    eyebrow: "বাংলার আপন গল্প",
    title: "Bengali classics",
    description: "Beloved voices of Bengal, beautifully brought to the page.",
    label: "Enter the Bengali collection",
    testId: "home-cta-bengali-classics",
    to: "/library?language=bn&availability=reader-ready",
    Icon: Languages,
  },
  {
    eyebrow: "TIMELESS WORLDS",
    title: "English classics",
    description: "Enduring stories of wonder, courage, mystery, and the human heart.",
    label: "Enter the English collection",
    testId: "home-cta-english-classics",
    to: "/library?language=en",
    Icon: BookText,
  },
  {
    eyebrow: "STORIES IN VOICE",
    title: "Immersive audiobooks",
    description: "Soulful performances that let every chapter unfold around you.",
    label: "Step into the listening room",
    testId: "home-cta-listening-room",
    to: "/library?availability=approved-audiobook",
    Icon: Headphones,
  },
];

function track(event, metadata = {}) {
  if (!event) return;
  trackFunnelEvent(event, { book: LIVE_APPROVED_SLUG, book_slug: LIVE_APPROVED_SLUG, ...metadata });
}

export default function Home() {
  const { social } = useSettings();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [newsletterStatus, setNewsletterStatus] = useState("");
  const [heroCuration, setHeroCuration] = useState(() => getHomeHeroSnapshot());
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);

  useSEO({
    title: "Earnalism | Bengali and English Classics in a Calm Digital Library",
    description:
      "Earnalism is a calm digital reading room for timeless Bengali and English literature, with beautiful editions, immersive audiobooks, and space to linger.",
    image: "/assets/shelves/bengali-classics.jpg",
    imageAlt: "Earnalism Bengali and English classics shelf artwork",
    canonicalPath: "/",
  });

  useEffect(() => {
    const cachedHero = getHomeHeroCache();
    if (cachedHero) setHeroCuration(cachedHero);
  }, []);

  useEffect(() => {
    trackFunnelEvent("bengali_gothic_pipeline_view", {
      source: "home",
      book_slug: LIVE_APPROVED_SLUG,
      public: false,
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let idleHandle;
    let timeoutHandle;

    const refreshCuration = () => {
      fetchHomeHero(controller.signal)
        .then((payload) => {
          startTransition(() => setHeroCuration(payload));
        })
        .catch((error) => {
          if (error?.name === "CanceledError" || error?.name === "AbortError") return;
          // Keep the bundled release snapshot visible if background revalidation fails.
        });
    };

    if (typeof window.requestIdleCallback === "function") {
      idleHandle = window.requestIdleCallback(refreshCuration, { timeout: 1200 });
    } else {
      timeoutHandle = window.setTimeout(refreshCuration, 250);
    }

    return () => {
      controller.abort();
      if (idleHandle !== undefined && typeof window.cancelIdleCallback === "function") {
        window.cancelIdleCallback(idleHandle);
      }
      if (timeoutHandle !== undefined) window.clearTimeout(timeoutHandle);
    };
  }, []);

  const subscribe = async (event) => {
    event.preventDefault();
    track("newsletter_submit_attempt", { source: "reading_circle" });
    setSubmitting(true);
    setNewsletterStatus("");
    try {
      const { data } = await api.post("/newsletter", { name, email });
      const message = "Welcome to the Reading Circle. We will write when a story is worth opening together.";
      toast.success(data.message || message);
      setName("");
      setEmail("");
      setNewsletterStatus(message);
      track("newsletter_submit_success", { source: "reading_circle" });
    } catch (err) {
      const message = formatError(err.response?.data?.detail);
      toast.error(message);
      setNewsletterStatus(message);
      track("newsletter_submit_failure", { source: "reading_circle" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="home-reference-page" data-testid="home-page">
      <PremiumHero
        curation={heroCuration}
        loading={false}
        error={false}
        headerMode="in-flow"
        analyticsNamespace="home"
        eyebrowLabel="A library made for lingering"
        onTrack={(event, metadata) => trackFunnelEvent(event, { source: "home", ...metadata })}
      />
      <section className="home-quick-paths" aria-labelledby="home-quick-paths-title" data-testid="home-quick-paths">
        <div className="home-quick-paths__inner">
          <div className="home-quick-paths__heading">
            <div className="overline">Begin with what moves you</div>
            <h2 id="home-quick-paths-title">
              Find the language, voice, and story <em>that feel like home.</em>
            </h2>
          </div>
          <div className="home-quick-paths__grid">
            {QUICK_PATHS.map(({ description, eyebrow, Icon, label, testId, title, to }) => (
              <Link
                key={to}
                data-testid={testId}
                to={to}
                className="home-quick-path"
                onClick={() => track("homepage_quick_path_click", { cta: label, destination: to })}
              >
                <span className="home-quick-path__icon"><Icon size={20} strokeWidth={1.45} aria-hidden="true" /></span>
                <span className="home-quick-path__copy">
                  <span className="home-quick-path__eyebrow">{eyebrow}</span>
                  <strong>{title}</strong>
                  <small>{description}</small>
                </span>
                <span className="home-quick-path__cta">{label}<ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" /></span>
              </Link>
            ))}
          </div>
        </div>
      </section>
      <DeferredMount className="home-deferred-listening" minHeight={374} rootMargin="1100px 0px" testId="deferred-listening-room">
        <Suspense fallback={<div className="home-deferred-listening__fallback" aria-hidden="true" />}>
          <HomeListeningRoom />
        </Suspense>
      </DeferredMount>
      <DeferredMount className="home-deferred-shelves" minHeight={0} rootMargin="1200px 0px" testId="deferred-home-shelves">
        <Suspense fallback={null}>
          <HomeShelfArchitecture />
        </Suspense>
      </DeferredMount>
      {false && (
      <section
        className="premium-landing-hero reference-library-hero relative isolate overflow-hidden text-[#FDFCF8]"
        data-testid="premium-landing-hero"
        data-approved-hero-max-height="650"
      >
        <div className="reference-hero-grid mx-auto grid max-w-7xl grid-cols-1 gap-7 px-5 py-8 sm:px-8 sm:py-11 lg:grid-cols-12 lg:items-center lg:px-12 lg:py-12">
          <div className="reference-hero-copy lg:col-span-7">
            <div className="italic-eyebrow flex items-center gap-3 text-[var(--brand-gold-soft)]" data-testid="hero-overline">
              <span className="h-px w-7 bg-[var(--brand-gold)]/70" />
              <span>The Earnalism Digital Library</span>
            </div>
            <h1
              className="home-hero-title mt-4 max-w-4xl font-serif-light tracking-normal text-[#FDFCF8] text-balance"
              data-testid="hero-headline"
              aria-label="Step into the classics. Stay with the story."
            >
              Step into the classics.
              <span className="home-hero-title__accent">Stay with the story.</span>
            </h1>
            <p className="home-hero-deck mt-3 max-w-2xl font-serif-display italic text-[#F4EFEA]/92">
              A calm home for Bengali and English classics, with room to read, reflect, and return.
            </p>
            <p className="home-hero-description mt-4 max-w-2xl font-light text-[#F4EFEA]/82">
              Illustrated editions lead the way, with quiet reading rooms and a small, carefully selected listening shelf for the late hour.
            </p>
            <div className="reference-hero-trust mt-5" aria-label="Earnalism launch trust signals">
              <span><ShieldCheck size={16} strokeWidth={1.6} /> Rights-safe releases</span>
              <span><BookOpen size={16} strokeWidth={1.6} /> Bengali + English shelves</span>
              <span><CreditCard size={16} strokeWidth={1.6} /> Curated listening</span>
            </div>
            <div className="premium-hero-ctas mt-5 sm:mt-6" data-testid="hero-ctas">
              <Link
                to="/library"
                className="btn-primary premium-hero-cta-primary justify-center gap-2"
                data-testid="hero-cta-library"
                onClick={() => track("hero_primary_cta_click", { cta: "home_hero_start_reading" })}
              >
                <BookOpen size={16} strokeWidth={1.7} /> Start Reading
              </Link>
              <Link
                to="#curated-action-cards-title"
                className="btn-secondary justify-center !border-[var(--brand-gold)] !text-[#FDFCF8] hover:!bg-[var(--brand-gold)]/10"
                data-testid="hero-cta-shelves"
                onClick={() => track("hero_secondary_cta_click", { cta: "home_hero_browse_library" })}
              >
                Browse Library <ArrowRight size={15} strokeWidth={1.7} />
              </Link>
            </div>
          </div>

          <div className="reference-editorial-stage lg:col-span-5" data-testid="hero-editorial-index">
            <div className="reference-editorial-card" aria-label="Earnalism library index">
              <div className="reference-editorial-card__eyebrow">Live shelves</div>
              <div className="reference-editorial-card__rows">
                <span>Bengali classics</span>
                <strong>Stories rooted in Bengal</strong>
              </div>
              <div className="reference-editorial-card__rows">
                <span>English classics</span>
                <strong>Dark houses and strange roads</strong>
              </div>
              <div className="reference-editorial-card__rows">
                <span>Audiobooks</span>
                <strong>Narrated classics for the late hour</strong>
              </div>
              <div className="reference-editorial-card__mark" aria-hidden="true">E</div>
            </div>
          </div>
        </div>
      </section>
      )}

      <section
        className="reference-reading-path"
        data-testid="reading-time-library-path"
        aria-labelledby="reading-time-library-path-title"
      >
        <div className="reference-reading-path__inner mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:px-12 lg:py-16">
          <div className="reference-reading-path__copy">
            <div className="overline mb-3">Reading on your terms</div>
            <h2 id="reading-time-library-path-title">
              Stay with the story for as long as it holds you.
            </h2>
            <p>
              The first 3 canonical pages are free. When you are ready for more, add reading time once—without a subscription or autorenewal.
            </p>
            <Link
              to="/pricing"
              className="btn-primary reference-reading-path__cta"
              data-testid="reading-path-pricing-cta"
              onClick={() => track("homepage_reading_path_click", { cta: "see_reading_passes", source: "homepage_reading_path" })}
            >
              View Reading Passes <ArrowRight size={15} strokeWidth={1.7} />
            </Link>
          </div>
          <div className="reference-reading-path__cards" aria-label="How Earnalism reading time works">
            <article className="reference-reading-step">
              <BookOpen size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Meet the story</h3>
              <p>The first 3 canonical pages are yours to explore before you add reading time.</p>
            </article>
            <article className="reference-reading-step">
              <CreditCard size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Choose your time</h3>
              <p>Add a reading pass only when you want to linger.</p>
            </article>
            <article className="reference-reading-step">
              <CircleCheck size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Carry it with you</h3>
              <p>Your place waits for you across account and library.</p>
            </article>
          </div>
        </div>
      </section>

      <section id="reading-circle" className="reading-circle">
        <div className="reading-circle__orbit" aria-hidden="true" />
        <div className="reading-circle__inner">
          <div className="reading-circle__story">
            <div className="reading-circle__eyebrow">THE READING CIRCLE</div>
            <h2>A private letter for readers who linger.</h2>
            <p className="reading-circle__description">
              Occasional notes on beautiful editions, newly opened listening rooms, and books worth carrying with you.
            </p>
            <ul className="reading-circle__signals" aria-label="Reading Circle notes">
              <li>Beautiful new editions</li>
              <li>Intimate listening rooms</li>
              <li>Letters from the library</li>
            </ul>
          </div>
          <form onSubmit={subscribe} className="reading-dispatch" data-testid="newsletter-card" aria-describedby="newsletter-description newsletter-trust newsletter-status">
            <div className="reading-dispatch__seal" aria-hidden="true">E</div>
            <div className="reading-dispatch__eyebrow">
              <Mail size={15} strokeWidth={1.6} aria-hidden="true" /> PRIVATE DISPATCH
            </div>
            <h3>Join the circle.</h3>
            <p id="newsletter-description" className="reading-dispatch__description">
              Share your name and email; we will write only when a story is worth opening together.
            </p>
            <div className="reading-dispatch__fields">
              <label className="reading-dispatch__field">
                <span>Your name</span>
                <input id="newsletter-name" required autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} data-testid="newsletter-name" />
              </label>
              <label className="reading-dispatch__field">
                <span>Email address</span>
                <input id="newsletter-email" required type="email" inputMode="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="newsletter-email" />
              </label>
            </div>
            <button type="submit" disabled={submitting} className="reading-dispatch__submit" data-testid="newsletter-submit">
              <span>{submitting ? "Joining the circle..." : "JOIN THE READING CIRCLE"}</span>
              <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
            </button>
            <p id="newsletter-trust" className="reading-dispatch__trust">Occasional. Thoughtful. Made for readers who still believe a book can change the room.</p>
            <div id="newsletter-status" className={`reading-dispatch__status ${newsletterStatus && !submitting ? "is-visible" : ""}`} aria-live="polite" role="status">{newsletterStatus}</div>
          </form>
          {activeSocials.length > 0 ? (
            <nav className="reading-circle__socials" aria-label="Earnalism social links" data-testid="home-socials">
              <div className="reading-circle__social-label">FOLLOW THE LIBRARY ELSEWHERE</div>
              <div className="reading-circle__social-grid">
                {activeSocials.map(({ id, ariaLabel, external, Icon, label, url }) => (
                  <a key={id} href={url} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined} aria-label={ariaLabel} className="home-social-rail__link" data-social={id} data-testid={`home-social-${id}`} onClick={() => track("social_link_click", { source: "reading_circle", social_id: id })}>
                    <Icon size={17} strokeWidth={1.55} aria-hidden="true" />
                    <span className="home-social-rail__copy">{label}</span>
                    <ArrowUpRight className="home-social-rail__external" size={14} strokeWidth={1.5} aria-hidden="true" />
                  </a>
                ))}
              </div>
            </nav>
          ) : null}
        </div>
      </section>
    </div>
  );
}
