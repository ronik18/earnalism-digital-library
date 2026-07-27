import { useEffect, useState } from "react";
import { ArrowRight, Headphones, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { normalizeHomeCuration } from "../lib/homeCuration";

function Cover({ book, quiet = false }) {
  return (
    <Link className={`home-shelf-cover${quiet ? " home-shelf-cover--quiet" : ""}`} to={`/book/${book.slug}`} aria-label={`Open ${book.title} by ${book.author}`}>
      <img src={book.front_cover_url || book.cover_image_url || book.cover_url} alt={`${book.title} cover`} loading="lazy" />
    </Link>
  );
}

function Shelf({ shelf }) {
  if (!shelf.books.length) return null;
  const listening = shelf.id === "selected-listening";
  return (
    <section className={`home-shelf home-shelf--${shelf.id}${listening ? " home-shelf--listening" : ""}`} aria-labelledby={`home-shelf-${shelf.id}`}>
      <div className="home-shelf__header">
        <div>
          <p className="overline">{shelf.kicker || "Curated shelf"}</p>
          <h2 id={`home-shelf-${shelf.id}`}>{shelf.title}</h2>
          {shelf.description && <p>{shelf.description}</p>}
        </div>
        <Link className="home-shelf__cta" to={`/library?shelf=${encodeURIComponent(shelf.id)}`}>{shelf.cta || "Open shelf"} <ArrowRight size={15} /></Link>
      </div>
      <div className={`home-shelf__grid home-shelf__grid--${String(shelf.mode || "Trio").toLowerCase()}`}>
        {shelf.books.map((book) => (
          <article className="home-shelf-card" key={book.slug}>
            <div className="home-shelf-card__copy">
              {listening && <span className="home-shelf-card__badge"><Headphones size={13} /> Approved listening</span>}
              <h3>{book.title}</h3>
              <p className="home-shelf-card__author">{book.author}</p>
              {book.short_description && <p className="home-shelf-card__description">{book.short_description}</p>}
              <Link className="home-shelf-card__link" to={listening ? `/reader/${book.slug}?listen=1` : `/book/${book.slug}`}>
                {listening ? "Listen" : "Read edition"} <ArrowRight size={14} />
              </Link>
            </div>
            <div className="home-shelf-card__cover"><Cover book={book} /></div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function HomeShelfArchitecture() {
  const [payload, setPayload] = useState(null);
  useEffect(() => { let active = true; api.get("/home/curated").then(({ data }) => { if (active) setPayload(normalizeHomeCuration(data)); }).catch(() => { if (active) setPayload({ shelves: [] }); }); return () => { active = false; }; }, []);
  if (!payload?.shelves?.some((shelf) => shelf.books?.length)) return null;
  return <section className="home-shelf-architecture" id="curated-action-cards-title" data-testid="home-shelf-architecture"><div className="home-shelf-architecture__inner"><div className="home-shelf-architecture__intro"><span className="overline">The reading room</span><h2>Find the shelf that meets you there.</h2><p>Cover-led editions, arranged by mood and return.</p></div>{payload.shelves.map((shelf) => <Shelf shelf={shelf} key={shelf.id} />)}</div></section>;
}
