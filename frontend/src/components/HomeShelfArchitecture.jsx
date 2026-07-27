import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { normalizeHomeCuration } from "../lib/homeCuration";
import CuratedShelfCollage from "./CuratedShelfCollage";

function legacyCurationShape(payload = {}) {
  const normalized = normalizeHomeCuration(payload);
  const literary = Array.isArray(normalized.shelves)
    ? normalized.shelves
    : Array.isArray(normalized.groups)
      ? normalized.groups
      : [];
  const audio = normalized.audiobook_shelf || {};
  return {
    eyebrow: "CURATED PATHS THROUGH THE LIBRARY",
    title: "A shelf for every kind of curiosity.",
    description: "Find a classic for the mood you are carrying today.",
    groups: literary
      .filter((shelf) => Number(shelf.total_count || shelf.books?.length || 0) > 0)
      .map((shelf) => ({
        ...shelf,
        books: shelf.visible_books || shelf.books || [],
        layout_area: shelf.layout_area || shelf.id,
      })),
    selected_audiobooks: audio?.books || normalized.shelf_collage?.selected_audiobooks || [],
  };
}

export default function HomeShelfArchitecture() {
  const [curation, setCuration] = useState(null);

  useEffect(() => {
    let active = true;
    api.get("/home/curated")
      .then(({ data }) => { if (active) setCuration(legacyCurationShape(data)); })
      .catch(() => { if (active) setCuration({ groups: [], selected_audiobooks: [] }); });
    return () => { active = false; };
  }, []);

  if (!curation || (!curation.groups.length && !curation.selected_audiobooks.length)) return null;
  return (
    <div id="curated-action-cards-title" data-testid="home-shelf-architecture">
      <CuratedShelfCollage curation={curation} />
    </div>
  );
}
