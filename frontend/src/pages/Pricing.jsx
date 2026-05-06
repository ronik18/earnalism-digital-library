import { Link } from "react-router-dom";
import useSEO from "../hooks/useSEO";
import { Clock } from "lucide-react";

const PACKS = [
  { id: "30m", label: "Afternoon Pause", minutes: 30, price: "₹49", note: "A single chapter, with breath to spare." },
  { id: "1h", label: "An Evening In", minutes: 60, price: "₹89", note: "An unhurried hour with a worthy book." },
  { id: "3h", label: "Long Weekend", minutes: 180, price: "₹239", note: "Three quiet hours; a finished read." },
  { id: "10h", label: "The Reader's Reserve", minutes: 600, price: "₹699", note: "Ten hours, kept until you call them in." },
];

export default function Pricing() {
  useSEO({
    title: "Reading Time — The Earnalism Digital Library",
    description: "Reading-time packs at The Earnalism. Buy minutes, read at your own pace, and return whenever you wish.",
  });
  return (
    <div className="min-h-[70vh] px-5 sm:px-8 lg:px-12 py-16 sm:py-24" data-testid="pricing-page">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <div className="italic-eyebrow">Reading time, by the pack</div>
          <h1 className="font-serif-light text-4xl sm:text-5xl lg:text-[3.5rem] text-burgundy leading-[1.05] mt-3 max-w-3xl mx-auto">
            Pay for the minutes you <span className="italic-accent">actually</span> read.
          </h1>
          <div className="gold-rule-thin mx-auto mt-7" />
          <p className="text-charcoal-soft text-base sm:text-lg font-light leading-[1.9] mt-7 max-w-2xl mx-auto">
            No subscriptions. No autorenewals. No pressure to finish before a billing cycle. Choose a pack, open a book, and the clock only runs while the words do.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
          {PACKS.map((p) => (
            <div key={p.id} className="card-elegant p-7 flex flex-col" data-testid={`pack-${p.id}`}>
              <div className="italic-eyebrow opacity-80 flex items-center gap-2"><Clock size={13} strokeWidth={1.5} /> {p.minutes >= 60 ? `${p.minutes / 60} ${p.minutes === 60 ? "hour" : "hours"}` : `${p.minutes} minutes`}</div>
              <h3 className="font-serif-display text-2xl text-burgundy leading-snug mt-3">{p.label}</h3>
              <div className="font-serif-light text-4xl text-charcoal mt-5">{p.price}</div>
              <p className="text-charcoal-soft text-sm font-light leading-relaxed mt-4">{p.note}</p>
              <button
                disabled
                title="Payments open in the next phase"
                className="btn-secondary w-full mt-7 opacity-50 cursor-not-allowed"
                data-testid={`pack-${p.id}-buy`}
              >
                Payments coming soon
              </button>
            </div>
          ))}
        </div>

        <div className="text-center mt-14">
          <p className="text-sm text-charcoal-soft font-light italic max-w-xl mx-auto">
            For now, an admin can credit your account on request — write to us and we'll set up your reading hours.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="btn-secondary">Request reading hours</Link>
            <Link to="/library" className="btn-link" data-testid="pricing-to-library">Browse the library →</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
