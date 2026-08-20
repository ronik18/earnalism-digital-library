import { ArrowRight, LibraryBig } from "lucide-react";
import { Link } from "react-router-dom";
import ShelfCollageTile from "./ShelfCollageTile";
import "./CuratedShelfCollage.css";
import { allocateUniqueShelfBooks, SHELF_RUNWAY_ORDER } from "../lib/homeShelfRunway";
import { buildShelfGridLayout, normalizeShelfArea, SHELF_AREAS } from "../lib/shelfGridLayout";

export default function CuratedShelfCollage({ curation }) {
  const groups = Array.isArray(curation?.groups)
    ? allocateUniqueShelfBooks(curation.groups
      .map((group) => ({ ...group, layout_area: normalizeShelfArea(group) }))
      .sort((left, right) => SHELF_RUNWAY_ORDER.indexOf(left.id) - SHELF_RUNWAY_ORDER.indexOf(right.id)))
    : [];
  const gridLayout = buildShelfGridLayout(groups);
  const missingShelfIds = SHELF_AREAS.filter((area) => !gridLayout.areas.has(area));
  const layoutClass = missingShelfIds.includes("short")
    ? "curated-shelf-collage--missing-short"
    : missingShelfIds.length
      ? `curated-shelf-collage--missing-${missingShelfIds.map((id) => id.replaceAll("-", "_")).join("-")}`
      : "";
  const gridStyle = {
    "--shelf-grid-areas": gridLayout.desktop,
    "--shelf-grid-row-count": gridLayout.desktopRowCount,
    "--shelf-grid-areas-tablet": gridLayout.tablet,
    "--shelf-grid-row-count-tablet": gridLayout.tabletRowCount,
    "--shelf-grid-areas-mobile": gridLayout.mobile,
    "--shelf-grid-row-count-mobile": gridLayout.mobileRowCount,
  };

  if (!groups.length) return null;

  const layoutFlags = [
    "curated-shelf-collage",
    layoutClass,
    gridLayout.areas.has("short") ? "curated-shelf-collage--with-short" : "curated-shelf-collage--without-short",
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
            <Link className="curated-shelf-collage__library-link" to="/library" data-testid="home-cta-complete-library">
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
