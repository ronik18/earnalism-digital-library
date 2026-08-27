import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { Mail, Instagram, Facebook, Youtube, Linkedin, Twitter } from "lucide-react";
import { api, formatError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { getEnabledSocialLinks } from "../config/socialLinks";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

const SOCIAL_ICONS = { email: Mail, facebook: Facebook, instagram: Instagram, linkedin: Linkedin, x: Twitter, youtube: Youtube };
const CONTACT_EMAIL = "sales@reoenterprise.org";
const INTENTS = {
  reader: { label: "Reader support", copy: "Tell us what you need help with." },
  rights: { label: "Rights or title inquiry", copy: "Tell us which edition or rights question you are writing about." },
  institution: { label: "Institutional access", copy: "Share a little about your institution and reading needs." },
  publisher: { label: "Publisher or licensing inquiry", copy: "Share the title, rights, or licensing context." },
  partnership: { label: "Partnership inquiry", copy: "Tell us about the proposed collaboration." },
};

function contactIntent(search) {
  const params = new URLSearchParams(search);
  const kind = String(params.get("intent") || "").trim().toLowerCase();
  if (INTENTS[kind]) return { ...INTENTS[kind], subject: INTENTS[kind].label };
  const interest = String(params.get("interest") || "").trim().replace(/[^a-z0-9 -]/gi, "").slice(0, 80);
  return interest ? { label: "Title inquiry", copy: "Tell us what you would like to know about this title.", subject: "Title inquiry: " + interest } : null;
}

export default function Contact() {
  const location = useLocation();
  const intent = useMemo(() => contactIntent(location.search), [location.search]);
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const { social } = useSettings();
  const activeSocials = getEnabledSocialLinks(social).map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] })).filter((item) => item.Icon);

  useSEO({
    title: "Contact | The Earnalism",
    description: "Contact The Earnalism for reader support, rights and title inquiries, institutional access, and publisher or licensing questions.",
    canonicalPath: "/contact",
  });

  useEffect(() => {
    if (intent?.subject) setForm((current) => current.subject ? current : { ...current, subject: intent.subject });
  }, [intent?.subject]);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setStatus("");
    try {
      await api.post("/contact", form);
      trackFunnelEvent("support_complaint_created", { source: "contact_form", has_subject: Boolean(form.subject), message_type: "reader_support" });
      setStatus("Thank you. Your message has been received.");
      toast.success("Thank you. Your message has been received.");
      setForm((current) => ({ name: "", email: "", subject: current.subject, message: "" }));
    } catch (requestError) {
      const message = formatError(requestError.response?.data?.detail);
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PublicPageFrame tone="quiet" testId="contact-page">
      <section className="editorial-support-hero">
        <div className="relative mx-auto max-w-7xl px-5 pb-14 pt-20 sm:px-8 sm:pb-20 sm:pt-28 lg:px-12">
          <p className="editorial-kicker">The library desk</p>
          <h1 className="mt-5 max-w-3xl font-serif-light text-4xl leading-[1.02] tracking-tight text-burgundy sm:text-6xl">Write to us with a question, a title, or a thought.</h1>
          <p className="mt-7 max-w-2xl text-lg leading-[1.8] text-charcoal-soft">For reader support, rights and title inquiries, institutional access, and publisher or licensing questions.</p>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[.82fr_1.18fr] lg:px-12 lg:py-20">
        <aside className="editorial-surface h-fit p-7 sm:p-9">
          <p className="editorial-kicker">Direct contact</p>
          <a href={"mailto:" + CONTACT_EMAIL} className="mt-5 flex min-h-11 items-center gap-3 font-serif-display text-lg italic text-burgundy hover:text-gold" data-testid="contact-email-link">
            <Mail size={17} aria-hidden="true" /> {CONTACT_EMAIL}
          </a>
          <p className="mt-6 leading-[1.75] text-charcoal-soft">Use the form for a fuller note. Share only the details needed for us to understand the question.</p>
          {activeSocials.length ? <nav className="mt-8 flex flex-wrap gap-3" aria-label="Earnalism social links" data-testid="contact-socials">
            {activeSocials.map(({ id, ariaLabel, external, Icon, url }) => <a key={id} href={url} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined} aria-label={ariaLabel} className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-brand-soft text-charcoal-soft transition-colors hover:border-gold hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold" data-testid={"contact-social-" + id}><Icon size={17} strokeWidth={1.5} aria-hidden="true" /></a>)}
          </nav> : null}
        </aside>

        <div className="editorial-surface p-6 sm:p-10">
          <p className="editorial-kicker">A short letter</p>
          {intent ? <div className="contact-intent-note mt-5 px-4 py-3 text-sm" data-testid="contact-intent"><strong>{intent.label}.</strong> {intent.copy}</div> : null}
          <form onSubmit={submit} className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2" data-testid="contact-form" aria-describedby={error ? "contact-form-error" : status ? "contact-form-status" : undefined}>
            <label className="block"><span className="editorial-kicker mb-2 block">Your name</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} autoComplete="name" className="input-elegant" data-testid="contact-name" /></label>
            <label className="block"><span className="editorial-kicker mb-2 block">Your email</span><input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" className="input-elegant" data-testid="contact-email-input" /></label>
            <label className="block sm:col-span-2"><span className="editorial-kicker mb-2 block">Subject</span><input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })} className="input-elegant" data-testid="contact-subject" /></label>
            <label className="block sm:col-span-2"><span className="editorial-kicker mb-2 block">Your message</span><textarea required rows={7} value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} className="input-elegant" data-testid="contact-message" /></label>
            <div className="sm:col-span-2">
              {error ? <p id="contact-form-error" className="contact-form-status" role="alert">{error}</p> : <p id="contact-form-status" className="contact-form-status" role="status">{status}</p>}
              <button disabled={submitting} className="btn-primary mt-2 min-h-11 disabled:opacity-60" data-testid="contact-submit">{submitting ? "Sending…" : "Send message"}</button>
            </div>
          </form>
        </div>
      </section>
    </PublicPageFrame>
  );
}
