import { Link } from "react-router-dom";
import { ArrowRight, Quote } from "lucide-react";
import "./ReaderPerspectives.css";

// Commissioned illustrations and copy, not statements or portraits of customers.
const PERSPECTIVES = [
  {
    id: "kolkata",
    tone: "blush",
    place: "Kolkata, India",
    portrait: "/assets/reader-perspectives/kolkata-reader.webp",
    alt: "Illustrative painted portrait of a reader in Kolkata",
    quote: "এই মানেই তো শুধু পড়া নয়, এ এক নতুন জানালার পৃথিবী দেখা। একটি অর্থবহ গল্প পড়ার সময়কে করে তোলে আরও সুন্দর, গভীর এবং আপন।",
    language: "bn",
  },
  {
    id: "london",
    tone: "cool",
    place: "London, United Kingdom",
    portrait: "/assets/reader-perspectives/london-reader.webp",
    alt: "Illustrative painted portrait of a reader in London",
    quote: "A meaningful story can be a quiet sanctuary for the mind — a place where a page restores a little wonder to the day.",
    language: "en",
  },
  {
    id: "chennai",
    tone: "sage",
    place: "Chennai, India",
    portrait: "/assets/reader-perspectives/chennai-reader.webp",
    alt: "Illustrative painted portrait of a reader in Chennai",
    quote: "A good story has a gentle way of slowing a busy day. Each page feels like an invitation to pause, listen and return renewed.",
    language: "en",
  },
  {
    id: "new-delhi",
    tone: "gold",
    place: "New Delhi, India",
    portrait: "/assets/reader-perspectives/new-delhi-reader.webp",
    alt: "Illustrative painted portrait of a reader in New Delhi",
    quote: "In the middle of a full life, reading gives me a small, generous room of my own — one that stays with me long after the last page.",
    language: "en",
  },
];

export default function ReaderPerspectives() {
  return (
    <section className="reference-reader-perspectives" aria-labelledby="reader-perspectives-title" data-testid="reader-perspectives-section">
      <div className="reference-reader-perspectives__intro">
        <p className="reference-kicker">Reader perspectives · imagined with care</p>
        <h2 id="reader-perspectives-title">What reading can feel like</h2>
        <p>Four imagined reader perspectives. Different lives, languages and places — connected by the private experience of a meaningful story.</p>
      </div>
      <div className="reference-reader-perspectives__grid">
        {PERSPECTIVES.map((perspective) => (
          <article className={`reference-reader-perspective reference-reader-perspective--${perspective.tone}`} data-testid={`reader-perspective-${perspective.id}`} key={perspective.id}>
            <figure>
              <img src={perspective.portrait} alt={perspective.alt} width="640" height="800" loading="lazy" decoding="async" />
            </figure>
            <div className="reference-reader-perspective__copy">
              <p className="reference-reader-perspective__label">Illustrative reader perspective</p>
              <Quote aria-hidden="true" />
              <blockquote lang={perspective.language}>{perspective.quote}</blockquote>
              <p className="reference-reader-perspective__place">{perspective.place}</p>
            </div>
          </article>
        ))}
      </div>
      <div className="reference-reader-perspectives__closing">
        <p>Different lives. A shared love for meaningful stories.</p>
        <Link to="/library" className="reference-button reference-button--gold" data-testid="reader-perspectives-cta">Start Reading Today <ArrowRight aria-hidden="true" /></Link>
      </div>
    </section>
  );
}
