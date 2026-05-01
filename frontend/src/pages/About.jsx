import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1600&q=85";

export default function About() {
  useSEO({
    title: "About The Earnalism — Independent Bookstore & Self-Publishing House",
    description: "The story of The Earnalism — an independent online bookstore and self-publishing house built around quiet permanence: fewer books, deeper readings, a longer relationship with each title.",
    image: HERO_IMG,
  });
  return (
    <div data-testid="about-page">
      <section className="max-w-4xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-36 pb-16 text-center">
        <div className="issue-marker mb-6">Our Story &middot; Volume I</div>
        <h1 className="font-serif-light text-4xl sm:text-6xl lg:text-[4.5rem] text-burgundy tracking-tight leading-[1.02] text-balance">An independent <span className="italic-accent">bookstore,</span> and a quiet promise to readers.</h1>
        <p className="font-serif-display italic text-lg sm:text-xl text-charcoal-soft mt-8 max-w-2xl mx-auto leading-snug">A small house with deep margins — built for the reader who still believes in slow attention.</p>
        <div className="gold-rule mx-auto mt-12" />
      </section>

      <section className="max-w-3xl mx-auto px-5 sm:px-8 py-12 space-y-16 sm:space-y-20">
        {[
          { t: "Our Philosophy", b: "We believe books are long instruments. They earn their place in a reader's life by returning, season after season, to be opened again. The Earnalism is built around that quiet permanence — fewer books, deeper readings, a longer relationship with each title." },
          { t: "What We Curate", b: "Our shelves are kept by hand: business books a founder can argue with, literature that lingers, self-growth that respects intelligence, spirituality that returns the reader to themselves, technology written with craft, and Bengali reading we love and want to make accessible to a new generation." },
          { t: "For Readers", b: "Our single promise is restraint — never a book we wouldn't lend to a close friend. The collection grows slowly because the trust of a careful reader compounds over years, not weeks. We design the bookstore, the packaging, and the reading notes for the one customer who still lingers over a single chapter." },
          { t: "The Earnalism Promise", b: "Read with depth. Curate with care. Share with meaning. These are not slogans for us — they are the standards we keep when no one is watching, and they are the reason we believe this small bookstore has a long future." },
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
