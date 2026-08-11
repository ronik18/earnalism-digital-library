import { startTransition, useEffect, useState } from "react";
import {
  fetchHomeListening,
  getHomeListeningSnapshot,
} from "../lib/homeSurfaces";
import PremiumListeningRail from "./PremiumListeningRail";

export default function HomeListeningRoom() {
  const [curation, setCuration] = useState(() => getHomeListeningSnapshot());
  const [loading, setLoading] = useState(true);
  const [refreshFailed, setRefreshFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchHomeListening(controller.signal, 3)
      .then((payload) => {
        startTransition(() => {
          setCuration(payload);
          setLoading(false);
          setRefreshFailed(false);
        });
      })
      .catch((error) => {
        if (error?.name !== "AbortError") {
          setLoading(false);
          setRefreshFailed(true);
        }
      });
    return () => controller.abort();
  }, []);

  const books = curation.listening_rooms?.items || curation.selected_audiobooks || [];
  const reserveBooks = curation.listening_rooms?.reserve_items || curation.reserve_audiobooks || [];

  return (
    <PremiumListeningRail
      books={books}
      reserveBooks={reserveBooks}
      loading={loading}
      error={refreshFailed && books.length === 0}
    />
  );
}
