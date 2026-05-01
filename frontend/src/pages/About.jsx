export default function About() {
  return (
    <div data-testid="about-page">
      <section className="max-w-4xl mx-auto px-5 sm:px-8 lg:px-12 pt-20 sm:pt-32 pb-12 text-center">
        <div className="overline mb-4">Our Story</div>
        <h1 className="font-serif-display text-4xl sm:text-6xl text-burgundy tracking-tight leading-[1.05] text-balance">A bookstore, a publishing house, and a quiet promise to readers.</h1>
        <div className="gold-rule mx-auto mt-10" />
      </section>

      <section className="max-w-3xl mx-auto px-5 sm:px-8 py-10 space-y-12">
        {[
          { t: "Our Philosophy", b: "We believe books are long instruments. They earn their place in a reader's life by returning, season after season, to be opened again. The Earnalism is built around that quiet permanence — fewer books, deeper readings, a longer relationship with each title." },
          { t: "What We Curate", b: "Our shelves are kept by hand: business books a founder can argue with, literature that lingers, self-growth that respects intelligence, spirituality that returns the reader to themselves, and Bengali reading that we love and want to make accessible to a new generation of readers." },
          { t: "For Authors and Readers", b: "We work in two directions. To readers, we promise restraint — never a book we wouldn't lend to a friend. To authors, we promise craft: manuscripts treated like furniture that has to last, covers chosen for the long shelf, and launches that build a slow, durable reputation." },
          { t: "The Earnalism Promise", b: "Read with depth. Build with discipline. Publish with grace. These are not slogans for us — they are the standards we keep when no one is watching, and they are the reason we believe this small house has a long future." },
        ].map((s) => (
          <div key={s.t} className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start" data-testid={`about-section-${s.t.toLowerCase().replace(/\s/g, '-')}`}>
            <div className="md:col-span-4">
              <h2 className="font-serif-display text-3xl text-burgundy">{s.t}</h2>
            </div>
            <p className="md:col-span-8 text-charcoal-soft leading-relaxed text-base sm:text-lg">{s.b}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
