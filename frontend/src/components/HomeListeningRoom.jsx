import { startTransition, useEffect, useState } from "react";
import {
  fetchHomeListening,
  getHomeListeningCache,
  getHomeListeningSnapshot,
} from "../lib/homeSurfaces";
import PremiumListeningRail from "./PremiumListeningRail";

export default function HomeListeningRoom() {
  const [curation, setCuration] = useState(() => (
    getHomeListeningCache() || getHomeListeningSnapshot()
  ));
  const [refreshFailed, setRefreshFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchHomeListening(controller.signal, 3)
      .then((payload) => {
        startTransition(() => {
          setCuration(payload);
          setRefreshFailed(false);
        });
      })
      .catch((error) => {
        if (error?.name !== "AbortError") setRefreshFailed(true);
      });
    return () => controller.abort();
  }, []);

  const books = curation.listening_rooms?.items || curation.selected_audiobooks || [];
  const reserveBooks = curation.listening_rooms?.reserve_items || curation.reserve_audiobooks || [];

  return (
    <PremiumListeningRail
      books={books}
      reserveBooks={reserveBooks}
      loading={false}
      error={refreshFailed && books.length === 0}
    />
  );
}
