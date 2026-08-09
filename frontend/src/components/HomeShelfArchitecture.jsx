import { useEffect, useState } from "react";
import {
  fetchHomeCuration,
  getHomeCurationSnapshot,
  normalizeHomeCuration,
} from "../lib/homeCuration";
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
  const [curation, setCuration] = useState(() => legacyCurationShape(getHomeCurationSnapshot()));

  useEffect(() => {
    const controller = new AbortController();
    fetchHomeCuration(controller.signal)
      .then((payload) => setCuration(legacyCurationShape(payload)))
      .catch((error) => {
        if (error?.name !== "AbortError") {
          // Keep the bundled release snapshot visible when the deferred refresh fails.
        }
      });
    return () => controller.abort();
  }, []);

  if (!curation || (!curation.groups.length && !curation.selected_audiobooks.length)) return null;
  return (
    <div id="curated-action-cards-title" data-testid="home-shelf-architecture">
      <CuratedShelfCollage curation={curation} />
    </div>
  );
}
