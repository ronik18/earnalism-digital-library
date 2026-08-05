import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
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
import CuratedShelfCollage from "../components/CuratedShelfCollage";
import PremiumHero from "../components/PremiumHero";
import PremiumListeningRail from "../components/PremiumListeningRail";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG } from "../lib/controlledLaunch";
import {
  fetchHomeCuration,
  getHomeCurationCache,
  getHomeCurationSnapshot,
} from "../lib/homeCuration";
import useSEO from "../hooks/useSEO";

// HomeShelfArchitecture remains the compatibility name for the editorial Home mount.

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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const cachedHomeCuration = getHomeCurationCache();
  const [homeCuration, setHomeCuration] = useState(() => cachedHomeCuration || getHomeCurationSnapshot());
  const [homeCurationLoading, setHomeCurationLoading] = useState(false);
  const [homeCurationError, setHomeCurationError] = useState(false);
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);

  useSEO({
    title: "Earnalism | Bengali and English Classics in a Calm Digital Library",
    description:
      "Earnalism is a calm digital reading room for timeless Bengali and English literature, with reader-only classics, graphical covers, and release-gated audiobooks.",
    image: "/assets/shelves/bengali-classics.jpg",
    imageAlt: "Earnalism Bengali and English classics shelf artwork",
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
    let idleHandle;
    let timeoutHandle;

    const refreshCuration = () => {
      fetchHomeCuration(controller.signal)
        .then((payload) => {
          setHomeCuration(payload);
          setHomeCurationError(false);
        })
        .catch((error) => {
          if (error?.name === "CanceledError" || error?.name === "AbortError") return;
          // Keep the bundled release snapshot visible if a background refresh fails.
          setHomeCurationError(false);
        })
        .finally(() => {
          if (!controller.signal.aborted) setHomeCurationLoading(false);
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
      <PremiumHero
        curation={homeCuration}
        loading={homeCurationLoading}
        error={homeCurationError}
        headerMode="in-flow"
        analyticsNamespace="home"
        onTrack={(event, metadata) => trackFunnelEvent(event, { source: "home", ...metadata })}
      />
      <PremiumListeningRail
        books={homeCuration.listening_rooms?.items || homeCuration.selected_audiobooks || []}
        reserveBooks={homeCuration.listening_rooms?.reserve_items || homeCuration.reserve_audiobooks || []}
        loading={homeCurationLoading}
        error={homeCurationError}
      />
      <div id="curated-action-cards-title" data-testid="home-shelf-architecture">
        <CuratedShelfCollage curation={homeCuration} />
      </div>
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
            <div className="overline mb-3">Reading time, clearly priced</div>
            <h2 id="reading-time-library-path-title">
              A revenue path that still feels like a library.
            </h2>
            <p>
              No fake urgency, no broad ownership promise, and no hidden audio overclaim. The reader opens calmly, and paid continuation uses a wallet only when someone chooses more quiet reading time.
            </p>
            <Link
              to="/pricing"
              className="btn-primary reference-reading-path__cta"
              data-testid="reading-path-pricing-cta"
              onClick={() => track("homepage_reading_path_click", { cta: "see_reading_passes", source: "homepage_reading_path" })}
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
              <p>Sign in to resume your place through account or library.</p>
            </article>
          </div>
        </div>
      </section>

      <section id="reading-circle" className="reading-circle">
        <div className="reading-circle__orbit" aria-hidden="true" />
        <div className="reading-circle__inner">
          <div className="reading-circle__story">
            <div className="reading-circle__eyebrow">
              <span aria-hidden="true" />
              Reading Circle
            </div>
            <h2>Follow the reading room.</h2>
            <p className="reading-circle__description">
              Receive quiet notes as Bengali and English classics move from rights review to reader-ready release.
            </p>
            {activeSocials.length > 0 ? (
              <nav className="reading-circle__socials" aria-label="Earnalism social links" data-testid="home-socials">
                <div className="reading-circle__social-label">Choose your reading-room channel</div>
                <div className="reading-circle__social-grid">
                  {activeSocials.map(({ id, ariaLabel, external, Icon, label, url }) => (
                    <a
                      key={id}
                      href={url}
                      target={external ? "_blank" : undefined}
                      rel={external ? "noopener noreferrer" : undefined}
                      aria-label={ariaLabel}
                      className="home-social-rail__link"
                      data-social={id}
                      data-testid={`home-social-${id}`}
                    >
                      <span className="home-social-rail__icon" aria-hidden="true">
                        <Icon size={18} strokeWidth={1.55} />
                      </span>
                      <span className="home-social-rail__copy">{label}</span>
                      <ArrowUpRight className="home-social-rail__external" size={14} strokeWidth={1.5} aria-hidden="true" />
                    </a>
                  ))}
                </div>
              </nav>
            ) : (
              <div className="home-social-review" data-testid="home-socials-owner-review">
                No placeholder or fake social links are shown.
              </div>
            )}
          </div>
          <form onSubmit={subscribe} className="reading-dispatch" data-testid="newsletter-card" aria-describedby="newsletter-description">
            <div className="reading-dispatch__seal" aria-hidden="true">E</div>
            <div className="reading-dispatch__eyebrow">
              <Mail size={15} strokeWidth={1.6} aria-hidden="true" /> Private dispatch
            </div>
            <p id="newsletter-description" className="reading-dispatch__description">
              Join for reading notes and release updates. No audiobook or paid campaign is live from this form.
            </p>
            <div className="reading-dispatch__fields">
              <label className="reading-dispatch__field">
                <span className="sr-only">Your name</span>
                <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" data-testid="newsletter-name" aria-label="Your name" />
              </label>
              <label className="reading-dispatch__field">
                <span className="sr-only">Your email</span>
                <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Your email" data-testid="newsletter-email" aria-label="Your email" />
              </label>
            </div>
            <button type="submit" disabled={submitting} className="reading-dispatch__submit" data-testid="newsletter-submit">
              <span>{submitting ? "Joining..." : "Join the Reading Circle"}</span>
              <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
