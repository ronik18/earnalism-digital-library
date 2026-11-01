import productCopy from "../content/productCopy.json";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { selectLibraryBooks } from "../lib/libraryCatalog";
import { libraryFiltersFromSearch } from "../lib/libraryFilterState";
import { genresOfBook } from "../lib/libraryDiscovery";
import { composeLibraryCatalog } from "../lib/libraryCatalogueComposition";
import useSEO from "../hooks/useSEO";
import { ReferenceLibrarySurface } from "../components/EditorialHomeLibrarySurfaces";

export default function Library() {
  const [params, setParams] = useSearchParams();
  const [liveBooks, setLiveBooks] = useState([]);
  const [catalogueState, setCatalogueState] = useState("loading");
  const [catalogueRequest, setCatalogueRequest] = useState(0);
  const [retryingCatalogue, setRetryingCatalogue] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const catalogueRequestIdRef = useRef(0);
  const catalogueRequestInFlightRef = useRef(false);
  const { query, language, reading, listening, genre, sort, stage } = libraryFiltersFromSearch(params);

  useSEO({
    title: "Library | Bengali and English Classics on Earnalism",
    description: productCopy.libraryDescription,
    canonicalPath: "/library",
  });

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++catalogueRequestIdRef.current;
    catalogueRequestInFlightRef.current = true;
    // Catalogue readiness must not wait for Home curation or optional imagery.
    // Bound only this public request; financial and auth transports are unchanged.
    api.get("/books", { signal: controller.signal, timeout: 15000 }).then(({ data }) => {
      if (controller.signal.aborted || catalogueRequestIdRef.current !== requestId) return;
      if (!Array.isArray(data)) throw new Error("Invalid catalogue response");
      setLiveBooks(data);
      setCatalogueState(data.length ? "ready" : "empty");
    }).catch(() => {
      if (controller.signal.aborted || catalogueRequestIdRef.current !== requestId) return;
      setLiveBooks([]);
      setCatalogueState("unavailable");
    }).finally(() => {
      if (!controller.signal.aborted && catalogueRequestIdRef.current === requestId) {
        catalogueRequestInFlightRef.current = false;
        setRetryingCatalogue(false);
      }
    });
    return () => controller.abort();
  }, [catalogueRequest]);

  const retryCatalogue = () => {
    if (catalogueRequestInFlightRef.current) return;
    catalogueRequestInFlightRef.current = true;
    setRetryingCatalogue(true);
    setCatalogueRequest((request) => request + 1);
  };
  const updateParam = (key, value, fallback = "all") => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      const effective = libraryFiltersFromSearch(current);
      if (current.has("category") && !["live", "pipeline"].includes(current.get("category"))) {
        if (effective.reading !== "all") next.set("reading", effective.reading);
        if (effective.genre !== "all") next.set("genre", effective.genre);
        next.delete("category");
      }
      if (key === "stage") { next.delete("category"); return next; }
      if (!value || value === fallback) next.delete(key); else next.set(key, value);
      if (key === "listening") next.delete("availability");
      return next;
    });
  };
  const resetReferenceFilters = () => setParams((current) => {
    const next = new URLSearchParams(current);
    ["language", "reading", "listening", "genre", "category", "availability"].forEach((key) => next.delete(key));
    return next;
  });
  // An empty or failed live response must not revive bundled candidate cards.
  const allBooks = useMemo(() => catalogueState === "ready" ? composeLibraryCatalog(liveBooks) : [], [liveBooks, catalogueState]);
  const filteredBooks = useMemo(() => selectLibraryBooks(allBooks, {
    query, language, reading, listening, genre, sort, stage,
  }), [allBooks, genre, language, listening, query, reading, sort, stage]);
  const genres = useMemo(() => [...new Set(allBooks.flatMap(genresOfBook))].sort(), [allBooks]);
  const handleSearch = (value) => setParams((current) => {
    const next = new URLSearchParams(current);
    if (value.trim()) next.set("q", value); else next.delete("q");
    return next;
  }, { replace: true });

  return <div className="library-page" data-testid="library-page">
    <ReferenceLibrarySurface filteredBooks={filteredBooks} loading={catalogueState === "loading"}
      catalogueState={catalogueState} retryingCatalogue={retryingCatalogue} onRetryCatalogue={retryCatalogue}
      query={query} language={language} reading={reading} listening={listening} genre={genre} genres={genres} sort={sort} stage={stage}
      onSearch={handleSearch} onParam={updateParam} onResetFilters={resetReferenceFilters}
      filtersOpen={filtersOpen} setFiltersOpen={setFiltersOpen} />
  </div>;
}
