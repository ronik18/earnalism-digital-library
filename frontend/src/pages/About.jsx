import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1600&q=85";

export default function About() {
  useSEO({
    title: "About The Earnalism — Dracula-First Digital Reading Room",
    description: "The Earnalism is a quiet digital reading room beginning with Dracula by Bram Stoker while Bengali Gothic and other classics move through a rights-safe pipeline.",
    image: HERO_IMG,
  });
  return (
    <div data-testid="about-page">
      <section className="max-w-4xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-36 pb-16 text-center">
        <div className="issue-marker mb-6">Our Story &middot; Volume I</div>
        <h1 className="font-serif-light text-4xl sm:text-6xl lg:text-[4.5rem] text-burgundy tracking-tight leading-[1.02] text-balance">A quiet <span className="italic-accent">reading room,</span> beginning with Dracula.</h1>
        <p className="font-serif-display italic text-lg sm:text-xl text-charcoal-soft mt-8 max-w-2xl mx-auto leading-snug">A small literary room with deep margins — built for the reader who still believes in slow attention.</p>
        <div className="gold-rule mx-auto mt-12" />
      </section>

      <section className="max-w-3xl mx-auto px-5 sm:px-8 py-12 space-y-16 sm:space-y-20">
        {[
          { t: "Our Philosophy", b: "We believe books are long instruments. They earn their place in a reader's life by returning, season after season, to be opened again. The Earnalism begins with one approved classic because trust is built through restraint." },
          { t: "What We Curate", b: "Dracula is live first. Bengali Gothic and other classics move through source, rights, text QA, and publication review before any public reading claim is made." },
          { t: "For Readers", b: "Our single promise is restraint. The collection grows only when evidence is ready, so every public reading path can stay clear, truthful, and calm." },
          { t: "The Earnalism Promise", b: "Read with depth. Curate with care. Publish with evidence. These are the standards we keep before a book becomes public." },
        ].map((s, i) => (
          <div key={s.t} className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start" data-testid={`about-section-${s.t.toLowerCase().replace(/\s/g, '-')}`}>
            <div className="md:col-span-4">
              <div className="italic-eyebrow mb-3">No. 0{i + 1}</div>
              <h2 className="font-serif-light text-3xl sm:text-[2.1rem] text-burgundy leading-tight">{s.t}</h2>
            </div>
            <p className="md:col-span-8 text-charcoal-soft leading-[1.85] text-base sm:text-[1.05rem] font-light">{s.b}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
