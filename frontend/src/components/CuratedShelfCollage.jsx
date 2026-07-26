import { ArrowRight, LibraryBig } from "lucide-react";
import { Link } from "react-router-dom";
import ShelfCollageTile from "./ShelfCollageTile";
import SelectedListeningRail from "./SelectedListeningRail";
import "./CuratedShelfCollage.css";

export default function CuratedShelfCollage({ curation }) {
  const groups = Array.isArray(curation?.groups)
    ? curation.groups.filter((group) => group?.books?.length)
    : [];
  const selectedAudiobooks = Array.isArray(curation?.selected_audiobooks)
    ? curation.selected_audiobooks
    : [];

  if (!groups.length && !selectedAudiobooks.length) return null;

  return (
    <section
      id="curated-shelf-collage"
      className="curated-shelf-collage"
      data-testid="curated-shelf-collage"
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

        <div className="curated-shelf-collage__grid">
          {groups.map((group, index) => (
            <ShelfCollageTile key={group.id || index} group={group} index={index} />
          ))}
        </div>

        <SelectedListeningRail books={selectedAudiobooks} />
      </div>
    </section>
  );
}
