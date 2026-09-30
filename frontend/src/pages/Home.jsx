import { useEffect, useState } from "react";
import { ArrowRight, Mail } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "../lib/api";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { LIVE_APPROVED_SLUG, PUBLIC_AUDIO_EXPOSURE_ENABLED, PUBLIC_PAID_COMMERCE_ENABLED } from "../lib/controlledLaunch";
import useSEO from "../hooks/useSEO";
import { availableReadingPasses } from "../lib/readingPassOffers";
import { ReferenceHomeSurface } from "../components/EditorialHomeLibrarySurfaces";
import "./HomeOptionB.css";

function trackNewsletterEvent(event) {
  try {
    // Newsletter analytics is supplemental: tracking must never interrupt signup.
    // Keep metadata intentionally free of the submitted name and email.
    trackFunnelEvent(event, { source: "reading_circle" });
  } catch {
    // A tracking failure must not block the newsletter request or its feedback.
  }
}

export default function Home() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [newsletterStatus, setNewsletterStatus] = useState("");
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
    trackNewsletterEvent("newsletter_submit_attempt");
    setSubmitting(true);
    setNewsletterStatus("");
    try {
      const { data } = await api.post("/newsletter", { name, email });
      const message = "Welcome to the Reading Circle. We will write when a story is worth opening together.";
      toast.success(data.message || message);
      setName("");
      setEmail("");
      setNewsletterStatus(message);
      trackNewsletterEvent("newsletter_submit_success");
    } catch (err) {
      const message = formatError(err.response?.data?.detail);
      toast.error(message);
      setNewsletterStatus(message);
      trackNewsletterEvent("newsletter_submit_failure");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`home-reference-page${PUBLIC_PAID_COMMERCE_ENABLED ? "" : " home-reference-page--no-commerce"}${PUBLIC_AUDIO_EXPOSURE_ENABLED ? "" : " home-reference-page--no-audio"}`} data-testid="home-page">
      <ReferenceHomeSurface
        readingPasses={homePasses}
      />
      <section className="home-literary-quote" aria-label="A thought on literature">
        <img className="home-literary-quote__art" src="/assets/home-option-b/river-quote.webp" alt="" aria-hidden="true" loading="lazy" decoding="async" />
        <blockquote>“A good story has a gentle way of slowing a busy day.”</blockquote>
        <p>— A reflection from the reading room</p>
      </section>
      <section id="reading-circle" className="reading-circle home-reading-circle" aria-labelledby="reading-circle-title">
        <div className="reading-circle__orbit" aria-hidden="true" />
        <img className="reading-circle__art" src="/assets/home-option-b/newsletter-botanical.webp" alt="" loading="lazy" decoding="async" />
        <div className="reading-circle__inner">
          <div className="reading-circle__story">
            <div className="reading-circle__eyebrow">STAY IN TOUCH</div>
            <h2 id="reading-circle-title">Letters for thoughtful readers.</h2>
            <p className="reading-circle__description">
              New arrivals, reading lists, essays and more — straight to your inbox.
            </p>
          </div>
          <form onSubmit={subscribe} className="reading-dispatch" data-testid="newsletter-card" aria-describedby="newsletter-description newsletter-trust newsletter-status">
            <div className="reading-dispatch__eyebrow sr-only">
              <Mail size={15} strokeWidth={1.6} aria-hidden="true" /> THE READING CIRCLE
            </div>
            <h3 className="sr-only">Subscribe to letters for thoughtful readers</h3>
            <p id="newsletter-description" className="reading-dispatch__description sr-only">
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
              <button type="submit" disabled={submitting} className="reading-dispatch__submit" data-testid="newsletter-submit">
                <span>{submitting ? "Subscribing..." : "SUBSCRIBE"}</span>
                <ArrowRight size={16} strokeWidth={1.6} aria-hidden="true" />
              </button>
            </div>
            <p id="newsletter-trust" className="reading-dispatch__trust">No spam. Just good reads.</p>
            <div id="newsletter-status" className={`reading-dispatch__status ${newsletterStatus && !submitting ? "is-visible" : ""}`} aria-live="polite" role="status">{newsletterStatus}</div>
          </form>
        </div>
      </section>
    </div>
  );
}
