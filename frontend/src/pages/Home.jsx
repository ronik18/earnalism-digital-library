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
  Twitter,
  Youtube,
} from "lucide-react";
import { toast } from "sonner";
import ComingSoonBoard from "../components/ComingSoonBoard";
import ApprovedAudiobookSpotlight from "../components/ApprovedAudiobookSpotlight";
import PremiumHero from "../components/PremiumHero";
import ShelfTwoSlideshow from "../components/ShelfTwoSlideshow";
import { useSettings } from "../context/SettingsContext";
import { api, formatError } from "../lib/api";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG } from "../lib/controlledLaunch";
import { buildShelfTwoBooks } from "../lib/shelfTwoBooks";
import { fetchHomeCuration, getHomeCurationSnapshot } from "../lib/homeCuration";
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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [homeCuration, setHomeCuration] = useState(() => getHomeCurationSnapshot());
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);
  const shelfTwoBooks = useMemo(() => buildShelfTwoBooks(), []);

  useSEO({
    title: "Earnalism | Bengali and English Classics in a Calm Digital Library",
    description:
      "Beautifully designed Bengali and English classics, immersive approved audiobooks, calm reading modes, and a curated literary experience.",
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
        if (controller.signal.aborted) return;
        setHomeCuration(payload);
      })
      .catch((error) => {
        if (controller.signal.aborted || error?.name === "CanceledError" || error?.code === "ERR_CANCELED") return;
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
        loading={!homeCuration}
        error={!homeCuration}
        onTrack={track}
      />

      <ComingSoonBoard />

      <ApprovedAudiobookSpotlight />

      <section
        className="reference-pipeline-shelf"
        data-testid="bengali-gothic-pipeline-shelf"
        aria-labelledby="bengali-gothic-pipeline-title"
      >
        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12 lg:py-12">
          <div className="mb-7">
            <div className="overline mb-2">Shelf II</div>
            <h2 id="bengali-gothic-pipeline-title" className="font-serif-light text-[1.68rem] leading-tight text-burgundy sm:text-[2.12rem]">
              Coming Through the Rights-Safe Pipeline
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-charcoal-soft">
              A quieter lower shelf for editions in preparation. Reader-only books stay intentional; unreleased titles remain editorial promises with no checkout or audiobook overclaim.
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
