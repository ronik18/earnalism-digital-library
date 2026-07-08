import { useState } from "react";
import { toast } from "sonner";
import { Mail, Instagram, Facebook, Youtube, Linkedin, Twitter } from "lucide-react";
import { api, formatError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { getEnabledSocialLinks } from "../config/socialLinks";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const SOCIAL_ICONS = {
  email: Mail,
  facebook: Facebook,
  instagram: Instagram,
  linkedin: Linkedin,
  x: Twitter,
  youtube: Youtube,
};

const CONTACT_EMAIL = "sales@reoenterprise.org";

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const { social } = useSettings();
  const activeSocials = getEnabledSocialLinks(social)
    .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
    .filter((item) => item.Icon);

  useSEO({
    title: "Contact — The Earnalism",
    description: `Write to The Earnalism — for book inquiries, order questions, reading recommendations, press, or simply to introduce yourself as a reader. Email ${CONTACT_EMAIL}.`,
  });

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/contact", form);
      trackFunnelEvent("support_complaint_created", {
        source: "contact_form",
        has_subject: Boolean(form.subject),
        message_type: "reader_support",
      });
      toast.success("Thank you. We'll respond with care.");
      setForm({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="contact-page">
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-32 pb-20 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16">
        <div className="lg:col-span-5">
          <div className="italic-eyebrow mb-4">Reach The Earnalism</div>
          <h1 className="font-serif-light text-4xl sm:text-5xl lg:text-[3.75rem] text-burgundy leading-[1.02] tracking-tight">Write to us — we read every <span className="italic-accent">letter.</span></h1>
          <div className="gold-rule-thin mt-7" />
          <p className="text-charcoal-soft mt-7 leading-[1.8] font-light">For book inquiries, order questions, reading recommendations, press, or simply to introduce yourself as a reader.</p>

          <div className="mt-10 space-y-5">
            <a href={`mailto:${CONTACT_EMAIL}`} className="flex items-center gap-3 text-charcoal hover:text-burgundy" data-testid="contact-email-link">
              <Mail size={16} className="text-gold" strokeWidth={1.5} /> <span className="font-serif-display italic text-lg">{CONTACT_EMAIL}</span>
            </a>
            {activeSocials.length > 0 && (
              <nav className="flex items-center gap-3 text-charcoal-soft" aria-label="Earnalism social links" data-testid="contact-socials">
                {activeSocials.map(({ id, ariaLabel, external, Icon, url }) => (
                  <a
                    key={id}
                    href={url}
                    target={external ? "_blank" : undefined}
                    rel={external ? "noopener noreferrer" : undefined}
                    aria-label={ariaLabel}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-brand-soft text-charcoal-soft transition-colors duration-300 hover:border-gold hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold"
                    data-testid={`contact-social-${id}`}
                  >
                    <Icon size={17} strokeWidth={1.5} aria-hidden="true" />
                  </a>
                ))}
              </nav>
            )}
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="card-elegant p-8 sm:p-12">
            <div className="italic-eyebrow mb-5">A short letter</div>
            <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-6" data-testid="contact-form">
              <label className="block">
                <span className="overline block mb-2">Your name</span>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" className="input-elegant" data-testid="contact-name" />
              </label>
              <label className="block">
                <span className="overline block mb-2">Your email</span>
                <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Your email" className="input-elegant" data-testid="contact-email-input" />
              </label>
              <label className="block sm:col-span-2">
                <span className="overline block mb-2">Subject</span>
                <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Subject" className="input-elegant" data-testid="contact-subject" />
              </label>
              <label className="block sm:col-span-2">
                <span className="overline block mb-2">Your message</span>
                <textarea required rows={6} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Your message" className="input-elegant" data-testid="contact-message" />
              </label>
              <div className="sm:col-span-2 mt-2"><button disabled={submitting} className="btn-primary disabled:opacity-60" data-testid="contact-submit">{submitting ? "Sending…" : "Send Message"}</button></div>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
