import productCopy from "../content/productCopy.json";
import useSEO from "../hooks/useSEO";
import { Link } from "react-router-dom";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";

const HERO_IMG = "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=1600&q=85";

const PRINCIPLES = [
  { title: "Our philosophy", body: "A good book can outlast the moment in which you meet it. A few pages may offer fresh language, a wider perspective or a useful question for study and work. What grows from that encounter is yours to shape." },
  { title: "What we curate", body: "Beloved Bengali voices and enduring English classics, chosen with care. Discover the editions available in your location, with respect for the work, its history and the people behind it." },
  { title: "For readers", body: "Read available editions online and discover selected audiobooks. Begin with a preview where offered; choose a prepaid Reading Pass when the edition requires one. No recurring subscription or automatic renewal." },
  { title: "The Earnalism promise", body: "A library should invite discovery and earn trust. We keep access clear, care for the words, and leave you free to choose what to read next." },
];

export default function About() {
  useSEO({
    title: "About Earnalism — Bengali and English Digital Library",
    description: "Bengali and English classics for a curious life. Read available editions online, discover selected audiobooks, and return when a story calls you back.",
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
              <p className="about-v3__lede">{productCopy.aboutIntroduction}</p>
              <p className="about-v3__benefit">{productCopy.aboutBenefit}</p>
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
