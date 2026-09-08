import useSEO from "../hooks/useSEO";
import { Link } from "react-router-dom";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1600&q=85";

const PRINCIPLES = [
  { title: "Our philosophy", body: "We believe books are long instruments. They earn their place in a reader's life by returning, season after season, to be opened again. Earnalism grows through restraint, not volume, so trust stays ahead of persuasion." },
  { title: "What we curate", body: "Bengali classics, English classics, and reader-first editions move through source, rights, text QA, cover, and publication review before any public reading or listening claim is made." },
  { title: "For readers", body: "Reader-ready titles are complete literary editions, not placeholders waiting for audio. Audiobooks appear only when approval evidence proves the listening room is ready." },
  { title: "The Earnalism promise", body: "Read with depth. Curate with care. Publish with evidence. These are the standards we keep before a book, audiobook, or campaign becomes public." },
];

export default function About() {
  useSEO({
    title: "About Earnalism — Bengali and English Digital Library",
    description: "Earnalism is a calm Bengali and English digital library where reader-ready classics are published with source care, graphical covers, and evidence-gated audiobooks.",
    image: HERO_IMG,
  });
  return (
    <PublicPageFrame tone="editorial" testId="about-page">
      <div className="about-v3">
        <section className="about-v3__masthead" aria-labelledby="about-page-title">
          <div className="about-v3__masthead-inner">
            <div>
              <p className="editorial-kicker">Our story · volume I</p>
              <h1 id="about-page-title">A quiet <em>reading room</em> for Bengali and English classics.</h1>
              <p className="about-v3__lede">A small literary room with deep margins, graphical editions, and release truth before every public claim.</p>
            </div>
            <aside className="about-v3__library-note" aria-label="Begin with the Library">
              <span>From the reading desk</span>
              <p>Every lasting reading life begins with a book that meets you where you are.</p>
              <Link to="/library" data-testid="about-library-link">Explore the Library</Link>
            </aside>
          </div>
        </section>

        <section className="about-v3__principles" aria-label="The Earnalism principles">
          {PRINCIPLES.map(({ title, body }, index) => (
            <article key={title} data-testid={`about-section-${title.replace(/\s/g, "-")}`}>
              <p className="editorial-kicker">No. 0{index + 1}</p>
              <h2>{title}</h2>
              <p>{body}</p>
            </article>
          ))}
        </section>

        <section className="about-v3__desk" aria-labelledby="about-desk-title">
          <div>
            <p className="editorial-kicker">The library desk</p>
            <h2 id="about-desk-title">A title, a rights question, or a thought to share?</h2>
            <p>Write to the library desk and we will direct your note to the right conversation.</p>
          </div>
          <Link to="/contact" data-testid="about-contact-link">Write to us</Link>
        </section>
      </div>
    </PublicPageFrame>
  );
}
