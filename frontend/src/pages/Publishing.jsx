import { useState } from "react";
import { toast } from "sonner";
import { api, formatError } from "../lib/api";
import { BookText, Palette, Layout, FileText, Megaphone } from "lucide-react";

const SERVICES = [
  { icon: FileText, t: "Manuscript Formatting", b: "Print-ready typesetting that respects the rhythm of your prose." },
  { icon: Palette, t: "Cover Direction", b: "Covers chosen for a long shelf life — restrained, elegant, and unmistakable." },
  { icon: BookText, t: "KDP-Ready Paperback Setup", b: "Trim sizes, margins, bleed, and metadata configured for Amazon KDP." },
  { icon: Layout, t: "Author Landing Page", b: "A premium one-page home for your book — built to convert quietly." },
  { icon: Megaphone, t: "Book Launch Strategy", b: "A launch arc that respects the reader: slow build, steady reveal, lasting attention." },
];

export default function Publishing() {
  const [form, setForm] = useState({ name: "", email: "", project_title: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/publishing-request", form);
      toast.success("Your request has been received. We'll be in touch with care.");
      setForm({ name: "", email: "", project_title: "", message: "" });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="publishing-page">
      <section className="max-w-5xl mx-auto px-5 sm:px-8 lg:px-12 pt-20 sm:pt-28 pb-12 text-center">
        <div className="overline mb-4">Publishing Services</div>
        <h1 className="font-serif-display text-4xl sm:text-6xl text-burgundy leading-[1.05] tracking-tight text-balance">Publish With Meaning. Present With Grace.</h1>
        <p className="mt-7 text-charcoal-soft text-lg max-w-2xl mx-auto leading-relaxed">A boutique self-publishing studio for authors who want their first book to look — and live — like their tenth.</p>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
        {SERVICES.map((s) => (
          <div key={s.t} className="card-elegant p-8" data-testid={`service-${s.t.toLowerCase().replace(/\s/g, '-')}`}>
            <s.icon className="text-gold" size={26} />
            <div className="gold-rule mt-5 mb-5" />
            <h3 className="font-serif-display text-2xl text-burgundy mb-3">{s.t}</h3>
            <p className="text-charcoal-soft leading-relaxed">{s.b}</p>
          </div>
        ))}
      </section>

      <section className="max-w-3xl mx-auto px-5 sm:px-8 lg:px-12 py-16 sm:py-24" id="request">
        <div className="card-elegant p-8 sm:p-14">
          <div className="overline mb-3">Begin the Conversation</div>
          <h2 className="font-serif-display text-3xl sm:text-4xl text-burgundy">Request Publishing Guidance</h2>
          <p className="text-charcoal-soft mt-3">Tell us about your manuscript and we'll respond within a few working days.</p>
          <form onSubmit={submit} className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-5" data-testid="publishing-form">
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" className="input-elegant" data-testid="pub-name" />
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Your email" className="input-elegant" data-testid="pub-email" />
            <input value={form.project_title} onChange={(e) => setForm({ ...form, project_title: e.target.value })} placeholder="Project / book title" className="input-elegant sm:col-span-2" data-testid="pub-title" />
            <textarea required rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Tell us a little about your book — what it is, who it's for, where you are in the process." className="input-elegant sm:col-span-2" data-testid="pub-message" />
            <div className="sm:col-span-2 mt-2"><button disabled={submitting} className="btn-primary disabled:opacity-60" data-testid="pub-submit">{submitting ? "Sending…" : "Send Request"}</button></div>
          </form>
        </div>
      </section>
    </div>
  );
}
