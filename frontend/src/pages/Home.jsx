import { lazy, startTransition, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  BookText,
  CircleCheck,
  CreditCard,
  Languages,
  Mail,
  Headphones,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import DeferredMount from "../components/DeferredMount";
import { api, formatError } from "../lib/api";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG, PUBLIC_AUDIO_EXPOSURE_ENABLED, PUBLIC_PAID_COMMERCE_ENABLED } from "../lib/controlledLaunch";
import {
  fetchHomeListening,
  getHomeListeningSnapshot,
} from "../lib/homeSurfaces";
import useSEO from "../hooks/useSEO";
import { PUBLIC_PREVIEW_COPY } from "../lib/publicAccessCopy";
import { availableReadingPasses } from "../lib/readingPassOffers";
import { ReferenceHomeSurface } from "../components/EditorialHomeLibrarySurfaces";
import "./HomeOptionB.css";

const HomeShelfArchitecture = lazy(() => import("../components/HomeShelfArchitecture"));

// HomeShelfArchitecture remains the compatibility name for the editorial Home mount.

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
    description: "Stories in voice, released with care.",
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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [newsletterStatus, setNewsletterStatus] = useState("");
  const [listeningCuration, setListeningCuration] = useState(() => getHomeListeningSnapshot());
  const [homePasses, setHomePasses] = useState([]);

  useSEO({
    title: "Earnalism | Bengali and English Classics in a Calm Digital Library",
    description:
      "Earnalism is a calm digital reading room for released Bengali and English literary editions, with space to linger.",
    image: "/assets/shelves/bengali-classics.jpg",
    imageAlt: "Earnalism Bengali and English classics shelf artwork",
    canonicalPath: "/",
  });

  useEffect(() => {
    if (!PUBLIC_AUDIO_EXPOSURE_ENABLED) return undefined;
    const controller = new AbortController();
    fetchHomeListening(controller.signal, 3)
      .then((payload) => startTransition(() => setListeningCuration(payload)))
      .catch((error) => {
        if (error?.name === "CanceledError" || error?.name === "AbortError") return;
        // The compact rail is deferred when the release-safe discovery
        // contract is unavailable; it never falls back to media metadata.
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!PUBLIC_PAID_COMMERCE_ENABLED) return undefined;
    const controller = new AbortController();
    let active = true;
    const applyOffers = (payload) => {
      if (!active) return;
      setHomePasses(availableReadingPasses(payload?.packs ?? payload));
    };
    api.get("/payments/offers", { signal: controller.signal })
      .then(({ data }) => applyOffers(data))
      .catch((error) => {
        if (error?.name === "CanceledError" || error?.name === "AbortError") return;
        api.get("/payments/packs", { signal: controller.signal })
          .then(({ data }) => applyOffers(data))
          .catch(() => {
            if (active) setHomePasses([]);
          });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    trackFunnelEvent("bengali_gothic_pipeline_view", {
      source: "home",
      book_slug: LIVE_APPROVED_SLUG,
      public: false,
    });
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
    <div className={`home-reference-page${PUBLIC_PAID_COMMERCE_ENABLED ? "" : " home-reference-page--no-commerce"}${PUBLIC_AUDIO_EXPOSURE_ENABLED ? "" : " home-reference-page--no-audio"}`} data-testid="home-page">
      <ReferenceHomeSurface
        readingPasses={homePasses}
        listeningItems={listeningCuration.listening_rooms?.items || listeningCuration.selected_audiobooks || []}
      />
      <section className="home-literary-quote" aria-label="A thought on literature">
        <blockquote>“Literature is a map of the human heart.”</blockquote>
        <p>— Alice Walker</p>
      </section>
      <section id="reading-circle" className="reading-circle home-reading-circle" aria-labelledby="reading-circle-title">
        <div className="reading-circle__orbit" aria-hidden="true" />
        <div className="reading-circle__inner">
          <div className="reading-circle__story">
            <div className="reading-circle__eyebrow">STAY IN TOUCH</div>
            <h2 id="reading-circle-title">Letters for thoughtful readers.</h2>
            <p className="reading-circle__description">
              New arrivals, reading lists, essays and more—straight to your inbox.
            </p>
          </div>
          <form onSubmit={subscribe} className="reading-dispatch" data-testid="newsletter-card" aria-describedby="newsletter-description newsletter-trust newsletter-status">
            <div className="reading-dispatch__eyebrow">
              <Mail size={15} strokeWidth={1.6} aria-hidden="true" /> THE READING CIRCLE
            </div>
            <h3 className="sr-only">Subscribe to letters for thoughtful readers</h3>
            <p id="newsletter-description" className="reading-dispatch__description">
              Share your name and email to receive occasional notes from the library.
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
              <span>{submitting ? "Subscribing..." : "SUBSCRIBE"}</span>
              <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
            </button>
            <p id="newsletter-trust" className="reading-dispatch__trust">No spam. Just good reads.</p>
            <div id="newsletter-status" className={`reading-dispatch__status ${newsletterStatus && !submitting ? "is-visible" : ""}`} aria-live="polite" role="status">{newsletterStatus}</div>
          </form>
        </div>
      </section>
      <div className="reference-home__legacy-content" aria-hidden="true">
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
      <DeferredMount className="home-deferred-shelves" minHeight={0} rootMargin="1200px 0px" testId="deferred-home-shelves">
        <Suspense fallback={null}>
          <HomeShelfArchitecture />
        </Suspense>
      </DeferredMount>
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
              {PUBLIC_PREVIEW_COPY} A valid Reading Pass is required from page 4; purchases are not available yet. Passes will be one-time purchases with no subscription or autorenewal when checkout opens.
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
              <p>{PUBLIC_PREVIEW_COPY} before you add reading time.</p>
            </article>
            <article className="reference-reading-step">
              <CreditCard size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Choose your time</h3>
              <p>Pass purchases are not available yet.</p>
            </article>
            <article className="reference-reading-step">
              <CircleCheck size={18} strokeWidth={1.6} aria-hidden="true" />
              <h3>Carry it with you</h3>
              <p>Your place waits for you across account and library.</p>
            </article>
          </div>
        </div>
      </section>


      </div>
    </div>
  );
}
