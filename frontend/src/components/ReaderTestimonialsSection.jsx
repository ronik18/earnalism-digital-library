import "./ReaderTestimonialsSection.css";

const TESTIMONIALS = [
  {
    avatar: "/assets/testimonials/ananya.svg",
    name: "Ananya S.",
    role: "Reader, Kolkata",
    quote: "Earnalism feels less like a platform and more like a lantern. I come here when the world is noisy, and somehow every page returns me to myself.",
  },
  {
    avatar: "/assets/testimonials/ritam.svg",
    name: "Ritam D.",
    role: "Weekend Reader, Bengaluru",
    quote: "There is a rare gentleness here—the kind that lets literature breathe. Each visit feels like stepping into a quiet room lined with memory, meaning, and light.",
  },
  {
    avatar: "/assets/testimonials/mrittika.svg",
    name: "Mrittika P.",
    role: "Story Listener, Mumbai",
    quote: "I arrived for books and stayed for the feeling. Earnalism turns reading into a ritual—slow, intimate, and unexpectedly beautiful.",
  },
  {
    avatar: "/assets/testimonials/soham.svg",
    name: "Soham R.",
    role: "Late-Night Reader, Delhi",
    quote: "Some places sell content; Earnalism offers presence. It reminds me that words can still hold warmth, wonder, and a kind of healing silence.",
  },
];

export default function ReaderTestimonialsSection() {
  return (
    <section className="reference-reader-testimonials" aria-labelledby="reader-testimonials-title" data-testid="reader-testimonials">
      <div className="reference-reader-testimonials__inner">
        <header className="reference-reader-testimonials__heading">
          <p className="reference-kicker">THE READING ROOM</p>
          <h2 id="reader-testimonials-title">What Our Readers Say</h2>
          <p>Small notes from readers who found quiet companionship, beauty, and depth inside Earnalism.</p>
          <small>Editorial sample notes, ready to be replaced with verified reader quotes.</small>
        </header>
        <div className="reference-reader-testimonials__grid">
          {TESTIMONIALS.map(({ avatar, name, role, quote }) => (
            <figure className="reference-reader-testimonial" key={name}>
              <figcaption>
                <img src={avatar} width="56" height="56" alt="" />
                <span>
                  <strong>{name}</strong>
                  <small>{role}</small>
                </span>
              </figcaption>
              <blockquote>“{quote}”</blockquote>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

export { TESTIMONIALS };
