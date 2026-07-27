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
import CuratedShelfCollage from "../components/CuratedShelfCollage";
import PremiumHero from "../components/PremiumHero";
import PremiumListeningRail from "../components/PremiumListeningRail";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG } from "../lib/controlledLaunch";
import { fetchHomeCuration, getHomeCurationSnapshot } from "../lib/homeCuration";
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
  const [homeCuration, setHomeCuration] = useState(() => getHomeCurationSnapshot());
  const [homeCurationLoading, setHomeCurationLoading] = useState(true);
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
    fetchHomeCuration(controller.signal)
      .then((payload) => {
        setHomeCuration(payload);
        setHomeCurationError(false);
      })
      .catch((error) => {
        if (error?.name !== "CanceledError" && error?.name !== "AbortError") setHomeCurationError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setHomeCurationLoading(false);
      });
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

      <section id="reading-circle" className="relative overflow-hidden bg-[#1b0b10] text-[#FDFCF8]">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 px-5 py-16 sm:px-8 lg:grid-cols-12 lg:px-12 lg:py-24">
          <div className="lg:col-span-6">
            <div className="italic-eyebrow reading-circle-eyebrow mb-4">Reading Circle</div>
            <h2 className="font-serif-light text-[1.78rem] leading-tight sm:text-[2.24rem]">Follow the reading room.</h2>
            <p className="mt-6 max-w-xl text-[#F4EFEA]/76 leading-[1.8]">
              Receive quiet notes as Bengali and English classics move from rights review to reader-ready release.
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
              Join for reading notes and release updates. No audiobook or paid campaign is live from this form.
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
