import { useEffect, useState } from "react";
import { ArrowRight, Headphones } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchHomeListening, getHomeListeningSnapshot } from "../lib/homeSurfaces";
import { homepageAudiobooksForExposure } from "../lib/homepageAudioGate";
import { PUBLIC_AUDIO_EXPOSURE_ENABLED } from "../lib/controlledLaunch";
import { readerRouteForBook } from "../lib/readerNavigation";
import BookCoverImage from "./BookCoverImage";
import "./HomepageListeningRoom.css";

export default function HomepageListeningRoom() {
  const [books, setBooks] = useState(() => {
    const snapshot = getHomeListeningSnapshot();
    return homepageAudiobooksForExposure(snapshot.selected_audiobooks || [], PUBLIC_AUDIO_EXPOSURE_ENABLED);
  });

  useEffect(() => {
    if (!PUBLIC_AUDIO_EXPOSURE_ENABLED) return undefined;
    const controller = new AbortController();
    fetchHomeListening(controller.signal, 3)
      .then((payload) => {
        setBooks(homepageAudiobooksForExposure(
          payload.listening_rooms?.items || payload.selected_audiobooks || [],
          PUBLIC_AUDIO_EXPOSURE_ENABLED,
        ));
      })
      .catch((error) => {
        if (error?.name !== "AbortError") setBooks([]);
      });
    return () => controller.abort();
  }, []);

  const featured = books[0];
  const durationMinutes = Number(featured?.audio_duration_ms) > 0
    ? Math.round(Number(featured.audio_duration_ms) / 60000)
    : null;

  return (
    <section className="homepage-listening" aria-labelledby="homepage-listening-title" data-testid="homepage-listening-room">
      <div className="homepage-listening__copy">
        <p className="reference-kicker">THE EARNALISM LISTENING ROOM</p>
        <h2 id="homepage-listening-title">Some books stay with you in voice.</h2>
        <p className="homepage-listening__description">The Listening Room brings selected works into a more intimate form — for walks, evenings, journeys, and moments when a story is better heard than held.</p>
        <p className="homepage-listening__quiet">Listen slowly. Listen thoughtfully. Let a good book keep you company.</p>
        <p className="homepage-listening__bridge">Read in stillness. Listen when life is in motion.</p>
        {featured ? (
          <Link className="homepage-listening__browse" to="/library?availability=approved-audiobook">
            Explore the Listening Room <ArrowRight aria-hidden="true" />
          </Link>
        ) : (
          <p className="homepage-listening__status" role="status">Audiobooks, thoughtfully arriving</p>
        )}
      </div>
      <div className="homepage-listening__visual">
        <img className="homepage-listening__still-life" src="/assets/home-option-b/listening-room.webp" alt="" loading="lazy" decoding="async" />
        {featured ? (
          <article className="homepage-listening__featured" data-testid="homepage-approved-audiobook" data-audio-state="available">
            <BookCoverImage
              book={featured}
              alt=""
              width={112}
              height={160}
              widths={[112, 168, 224]}
              sizes="72px"
              allowGraphicalFallback={false}
              loading="lazy"
            />
            <div>
              <p><Headphones aria-hidden="true" /> APPROVED LISTENING EDITION</p>
              <h3>{featured.title_en || featured.title}</h3>
              <span>{[featured.author, durationMinutes ? `${durationMinutes} min` : ""] .filter(Boolean).join(" · ")}</span>
              <div className="homepage-listening__featured-actions">
                <Link to={featured.book_url || `/book/${featured.slug}`}>Read</Link>
                <Link to={readerRouteForBook(featured.slug, { listen: true })} aria-label={`Listen to ${featured.title_en || featured.title}`}>Listen</Link>
              </div>
            </div>
          </article>
        ) : (
          <div className="homepage-listening__image-note" aria-hidden="true">
            <Headphones />
            <span>BOOKS, IN A QUIETER VOICE</span>
          </div>
        )}
      </div>
    </section>
  );
}
