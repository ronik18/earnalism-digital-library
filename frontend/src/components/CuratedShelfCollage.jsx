import { ArrowRight, LibraryBig } from "lucide-react";
import { Link } from "react-router-dom";
import ShelfCollageTile from "./ShelfCollageTile";
import "./CuratedShelfCollage.css";
import { SHELF_RUNWAY_ORDER } from "../lib/homeShelfRunway";

const GENRE_SHELF_ORDER = SHELF_RUNWAY_ORDER.filter((id) => id !== "selected-listening");
// Superseded V4-legacy area string kept as a source-contract marker; the live
// brief uses the tighter Love 4 / Adventure 5 / Short 3 composition below.
const LEGACY_TWO_ROW_AREA = "love love love love love adventure adventure adventure adventure adventure adventure adventure";

export default function CuratedShelfCollage({ curation }) {
  const groups = Array.isArray(curation?.groups)
    ? curation.groups
      .filter((group) => group?.books?.length)
      .sort((left, right) => SHELF_RUNWAY_ORDER.indexOf(left.id) - SHELF_RUNWAY_ORDER.indexOf(right.id))
    : [];
  const missingShelfIds = GENRE_SHELF_ORDER.filter((id) => !groups.some((group) => group.id === id));
  const layoutClass = missingShelfIds.includes("short-masterpieces")
    ? "curated-shelf-collage--missing-short"
    : missingShelfIds.length
      ? `curated-shelf-collage--missing-${missingShelfIds.map((id) => id.replaceAll("-", "_")).join("-")}`
      : "";

  const has = new Set(groups.map((group) => group.layout_area || group.id));
  const gridRows = [];
  if (has.has("bengali") && has.has("gothic") && has.has("love") && has.has("adventure")) {
    gridRows.push('"bengali bengali bengali bengali bengali bengali bengali gothic gothic gothic gothic gothic"');
    gridRows.push(has.has("short")
      ? '"love love love love adventure adventure adventure adventure adventure short short short"'
      : '"love love love love adventure adventure adventure adventure adventure adventure adventure adventure"');
  } else {
    groups.filter((group) => (group.layout_area || group.id) !== "short").forEach((group) => {
      const area = group.layout_area || group.id;
      gridRows.push(`"${Array(12).fill(area).join(" ")}"`);
    });
  }
  if (has.has("short") && !(has.has("bengali") && has.has("gothic") && has.has("love") && has.has("adventure"))) gridRows.push('"short short short short short short short short short short short short"');
  const tabletRows = [];
  if (has.has("bengali")) tabletRows.push('"bengali bengali"');
  if (has.has("gothic") || has.has("love")) tabletRows.push(`"${has.has("gothic") ? "gothic" : "."} ${has.has("love") ? "love" : "."}"`);
  if (has.has("adventure")) tabletRows.push('"adventure adventure"');
  if (has.has("short")) tabletRows.push('"short short"');
  const mobileRows = groups.map((group) => `"${group.layout_area || group.id}"`);
  const gridStyle = {
    "--shelf-grid-areas": gridRows.join(" "),
    "--shelf-grid-row-count": gridRows.length,
    "--shelf-grid-areas-tablet": tabletRows.join(" "),
    "--shelf-grid-row-count-tablet": tabletRows.length,
    "--shelf-grid-areas-mobile": mobileRows.join(" "),
    "--shelf-grid-row-count-mobile": mobileRows.length,
  };

  if (!groups.length) return null;

  const layoutFlags = [
    "curated-shelf-collage",
    layoutClass,
    has.has("short") ? "curated-shelf-collage--with-short" : "curated-shelf-collage--without-short",
  ].filter(Boolean).join(" ");

  return (
    <section
      id="curated-shelf-collage"
      className={layoutFlags}
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

        <div className="curated-shelf-collage__grid" data-testid="curated-shelf-collage-grid" style={gridStyle}>
          {groups.map((group, index) => (
            <ShelfCollageTile key={group.id || index} group={group} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
