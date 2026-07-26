import { ArrowRight, LibraryBig } from "lucide-react";
import { Link } from "react-router-dom";
import ShelfCollageTile from "./ShelfCollageTile";
import SelectedListeningRail from "./SelectedListeningRail";
import "./CuratedShelfCollage.css";

const SHELF_ORDER = [
  "bengali-life-and-legacy",
  "gothic-and-the-uncanny",
  "love-society-and-human-nature",
  "adventure-nature-and-wonder",
  "short-masterpieces",
];

export default function CuratedShelfCollage({ curation }) {
  const groups = Array.isArray(curation?.groups)
    ? curation.groups
      .filter((group) => group?.books?.length)
      .sort((left, right) => SHELF_ORDER.indexOf(left.id) - SHELF_ORDER.indexOf(right.id))
    : [];
  const selectedAudiobooks = Array.isArray(curation?.selected_audiobooks)
    ? curation.selected_audiobooks
    : [];
  const missingShelfIds = SHELF_ORDER.filter((id) => !groups.some((group) => group.id === id));
  const layoutClass = missingShelfIds.includes("short-masterpieces")
    ? "curated-shelf-collage--missing-short"
    : "";

  if (!groups.length && !selectedAudiobooks.length) return null;

  return (
    <section
      id="curated-shelf-collage"
      className={`curated-shelf-collage ${layoutClass}`.trim()}
      data-testid="curated-shelf-collage"
      data-missing-shelves={missingShelfIds.join(",")}
      aria-labelledby="curated-shelf-collage-title"
    >
      <div className="curated-shelf-collage__inner">
        <div className="curated-shelf-collage__intro">
          <div className="curated-shelf-collage__eyebrow">
            <span aria-hidden="true" />
            {curation?.eyebrow || "CURATED PATHS THROUGH THE LIBRARY"}
          </div>
          <div className="curated-shelf-collage__intro-row">
            <div>
              <h2 id="curated-shelf-collage-title">
                {curation?.title || "A shelf for every kind of curiosity."}
              </h2>
              <p>{curation?.description || "Find a classic for the mood you are carrying today."}</p>
            </div>
            <Link className="curated-shelf-collage__library-link" to="/library">
              <LibraryBig size={17} strokeWidth={1.5} aria-hidden="true" />
              Browse the complete library
              <ArrowRight size={15} strokeWidth={1.6} aria-hidden="true" />
            </Link>
          </div>
        </div>
        <div className="curated-shelf-collage__divider" aria-hidden="true"><span /></div>

        <div className="curated-shelf-collage__grid" data-testid="curated-shelf-collage-grid">
          {groups.map((group, index) => (
            <ShelfCollageTile key={group.id || index} group={group} index={index} />
          ))}
        </div>

        <SelectedListeningRail books={selectedAudiobooks} />
      </div>
    </section>
  );
}
