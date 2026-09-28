import { BookOpen, Leaf, Sprout, Sun } from "lucide-react";
import "./ReaderPerspectives.css";

const BENEFITS = [
  {
    Icon: Sprout,
    title: "A slower mind",
    copy: "Step away from the rush and find room for what really matters.",
  },
  {
    Icon: BookOpen,
    title: "A wider world",
    copy: "Meet new ideas, cultures and perspectives across time and place.",
  },
  {
    Icon: Sun,
    title: "A more thoughtful you",
    copy: "Return to yourself with a little more kindness and clarity.",
  },
];

const PERSPECTIVES = [
  {
    id: "kolkata",
    place: "Kolkata, India",
    portrait: "/assets/reader-perspectives/kolkata-reader.webp",
    alt: "Illustrative painted portrait of a reader in Kolkata",
    quote: "এই মানেই তো শুধু পড়া নয়, এ এক নতুন জানালার পৃথিবী দেখা। একটি অর্থবহ গল্প পড়ার সময়কে করে তোলে আরও সুন্দর, গভীর এবং আপন।",
    language: "bn",
  },
  {
    id: "london",
    place: "London, United Kingdom",
    portrait: "/assets/reader-perspectives/london-reader.webp",
    alt: "Illustrative painted portrait of a reader in London",
    quote: "A meaningful story can be a quiet sanctuary for the mind — a place where a page restores a little wonder to the day.",
    language: "en",
  },
  {
    id: "chennai",
    place: "Chennai, India",
    portrait: "/assets/reader-perspectives/chennai-reader.webp",
    alt: "Illustrative painted portrait of a reader in Chennai",
    quote: "A good story has a gentle way of slowing a busy day. Each page feels like an invitation to pause, listen and return renewed.",
    language: "en",
  },
  {
    id: "new-delhi",
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
      <div className="reference-reader-perspectives__layout">
        <div className="reference-reader-perspectives__intro">
          <p className="reference-kicker">WHAT READING CAN FEEL LIKE</p>
          <h2 id="reader-perspectives-title">A gentler, richer way to be in the world.</h2>
        <p>Reading slows us down. It gives us space to think, to feel, and to see life through other eyes. At The Earnalism Digital Library, we believe in the quiet power of books — to comfort, to challenge, and to keep us curiously human.</p>
        </div>
        <div className="reference-reader-perspectives__benefits" aria-label="What reading can bring">
          {BENEFITS.map(({ Icon, title, copy }) => (
            <article key={title}>
              <Icon aria-hidden="true" />
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </div>
      <div className="reference-reader-perspectives__closing">
        <blockquote>“A book is a way to hold a conversation across time.”</blockquote>
        <p>— Chimamanda Ngozi Adichie</p>
        <div className="reference-reader-perspectives__portraits" aria-label="Illustrative reader portraits">
          {PERSPECTIVES.slice(0, 2).map((perspective) => (
            <img key={perspective.id} src={perspective.portrait} alt={perspective.alt} width="64" height="64" loading="lazy" decoding="async" />
          ))}
          <Leaf aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}
