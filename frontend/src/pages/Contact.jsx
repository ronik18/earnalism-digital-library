import { useState } from "react";
import { toast } from "sonner";
import { Mail, Instagram, Twitter, Linkedin } from "lucide-react";
import { api, formatError } from "../lib/api";

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/contact", form);
      toast.success("Thank you. We'll respond with care.");
      setForm({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="contact-page">
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-20 sm:pt-28 pb-16 grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-5">
          <div className="overline mb-4">Reach The Earnalism</div>
          <h1 className="font-serif-display text-4xl sm:text-5xl text-burgundy leading-[1.05] tracking-tight">Write to us — we read every letter.</h1>
          <p className="text-charcoal-soft mt-6 leading-relaxed">For book inquiries, publishing conversations, press, or simply to introduce yourself as a reader.</p>

          <div className="mt-10 space-y-4">
            <a href="mailto:hello@theearnalism.com" className="flex items-center gap-3 text-charcoal hover:text-burgundy" data-testid="contact-email-link">
              <Mail size={18} className="text-gold" /> hello@theearnalism.com
            </a>
            <div className="flex items-center gap-4 text-charcoal-soft">
              <a href="#" className="hover:text-burgundy"><Instagram size={18} /></a>
              <a href="#" className="hover:text-burgundy"><Twitter size={18} /></a>
              <a href="#" className="hover:text-burgundy"><Linkedin size={18} /></a>
            </div>
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="card-elegant p-8 sm:p-12">
            <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-5" data-testid="contact-form">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" className="input-elegant" data-testid="contact-name" />
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Your email" className="input-elegant" data-testid="contact-email-input" />
              <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Subject" className="input-elegant sm:col-span-2" data-testid="contact-subject" />
              <textarea required rows={6} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Your message" className="input-elegant sm:col-span-2" data-testid="contact-message" />
              <div className="sm:col-span-2 mt-2"><button disabled={submitting} className="btn-primary disabled:opacity-60" data-testid="contact-submit">{submitting ? "Sending…" : "Send Message"}</button></div>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
