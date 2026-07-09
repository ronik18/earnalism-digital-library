import useSEO from "../hooks/useSEO";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1600&q=85";

export default function About() {
  useSEO({
    title: "About Earnalism — Bengali and English Digital Library",
    description: "Earnalism is a calm Bengali and English digital library where reader-ready classics are published with source care, graphical covers, and evidence-gated audiobooks.",
    image: HERO_IMG,
  });
  return (
    <div data-testid="about-page">
      <section className="max-w-4xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-36 pb-16 text-center">
        <div className="issue-marker mb-6">Our Story &middot; Volume I</div>
        <h1 className="font-serif-light text-4xl sm:text-6xl lg:text-[4.5rem] text-burgundy tracking-tight leading-[1.02] text-balance">A quiet <span className="italic-accent">reading room</span> for Bengali and English classics.</h1>
        <p className="font-serif-display italic text-lg sm:text-xl text-charcoal-soft mt-8 max-w-2xl mx-auto leading-snug">A small literary room with deep margins, graphical editions, and release truth before every public claim.</p>
        <div className="gold-rule mx-auto mt-12" />
      </section>

      <section className="max-w-3xl mx-auto px-5 sm:px-8 py-12 space-y-16 sm:space-y-20">
        {[
          { t: "Our Philosophy", b: "We believe books are long instruments. They earn their place in a reader's life by returning, season after season, to be opened again. Earnalism grows through restraint, not volume, so trust stays ahead of persuasion." },
          { t: "What We Curate", b: "Bengali classics, English classics, and reader-first editions move through source, rights, text QA, cover, and publication review before any public reading or listening claim is made." },
          { t: "For Readers", b: "Reader-ready titles are complete literary editions, not placeholders waiting for audio. Audiobooks appear only when approval evidence proves the listening room is ready." },
          { t: "The Earnalism Promise", b: "Read with depth. Curate with care. Publish with evidence. These are the standards we keep before a book, audiobook, or campaign becomes public." },
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
