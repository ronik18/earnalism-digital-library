import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { isRequestCancellation } from "../../lib/requestCancellation";
import {
  endReadingPassSession,
  getReadingPassPage,
  renewReadingPassLease,
  saveReadingPassPosition,
  startReadingPassSession,
} from "../../lib/readingPassApi";
import { useAuth } from "../../context/AuthContext";
import ReaderExperienceV2, { READER_V2_FIXTURE } from "./ReaderExperienceV2";

function pageFromSearch(search) {
  const value = Number(search.get("p") || 1);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

function paragraphsFromHtml(html = "") {
  if (typeof document === "undefined") return String(html).replace(/<[^>]+>/g, " ").trim() ? [String(html).replace(/<[^>]+>/g, " ").trim()] : [];
  const container = document.createElement("div");
  container.innerHTML = html;
  return [...container.querySelectorAll("p")].map((node) => node.textContent?.trim()).filter(Boolean)
    || [];
}

function routeState(title, message, action = null) {
  return <main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p>{message}</p>{action}</section></main>;
}

export default function ReaderExperienceV2Route() {
  const { slug = "" } = useParams();
  const [search, setSearch] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canonicalPage = pageFromSearch(search);
  // This is compiled only into the private visual-review build. It has no
  // reader API, protected text, lease, audio source, or production toggle.
  const visualFixture = process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1" && search.get("visual-fixture") === "1";
  const [manifest, setManifest] = useState(null);
  const [page, setPage] = useState(null);
  const [lease, setLease] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const leaseRef = useRef(null);

  const setLeaseState = useCallback((value) => {
    leaseRef.current = value;
    setLease(value);
  }, []);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    userApi.get(readerManifestPath(slug), { signal: controller.signal })
      .then((response) => { if (!cancelled) setManifest(response.data); })
      .catch((requestError) => {
        if (!cancelled && !isRequestCancellation(requestError)) setError("This reader edition is not available.");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; controller.abort(); };
  }, [slug, visualFixture]);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setPage(null);
    if (!manifest || canonicalPage > 3 && !lease) return undefined;
    getReadingPassPage(slug, canonicalPage, lease, { signal: controller.signal })
      .then((value) => {
        if (cancelled) return;
        setPage(value);
        if (!value.is_preview && lease) {
          void saveReadingPassPosition({ bookSlug: slug, pageIndex: value.page_index, chapterId: value.chapter_id });
        }
      })
      .catch((requestError) => {
        if (!cancelled && !isRequestCancellation(requestError)) {
          setError(requestError?.response?.data?.detail?.message || "Reading access could not be verified.");
        }
      });
    return () => { cancelled = true; controller.abort(); };
  }, [canonicalPage, lease, manifest, slug, visualFixture]);

  useEffect(() => {
    if (!lease) return undefined;
    const renew = () => renewReadingPassLease({
      lease,
      sequence: Number(lease.sequence || 0) + 1,
      active: document.visibilityState === "visible",
    }).then((next) => setLeaseState({ ...lease, sessionId: next.session_id || lease.sessionId, token: next.lease_token || lease.token, version: Number(next.lease_version || lease.version), sequence: Number(lease.sequence || 0) + 1 })).catch(() => setError("Reading Pass authorization expired."));
    const interval = window.setInterval(renew, 10_000);
    return () => window.clearInterval(interval);
  }, [lease, setLeaseState]);

  useEffect(() => () => { if (leaseRef.current?.sessionId) void endReadingPassSession(leaseRef.current, "reader_v2_unmount"); }, []);

  const changePage = useCallback((nextPage) => {
    const params = new URLSearchParams(search);
    params.set("p", String(nextPage));
    setSearch(params, { replace: false });
  }, [search, setSearch]);

  const authorizeAndContinue = useCallback(async (nextPage) => {
    if (nextPage <= 3) return changePage(nextPage);
    if (!user || typeof user !== "object") {
      navigate(`/login?next=${encodeURIComponent(`/reader/${slug}?p=${nextPage}`)}`);
      return;
    }
    try {
      const started = await startReadingPassSession({ bookSlug: slug, pageIndex: nextPage });
      const nextLease = { sessionId: started.session_id, token: started.lease_token, version: Number(started.lease_version || 1), sequence: 0 };
      setLeaseState(nextLease);
      changePage(nextPage);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail?.message || "A current Reading Pass is required to continue.");
    }
  }, [changePage, navigate, setLeaseState, slug, user]);

  const model = useMemo(() => {
    const book = manifest?.book || {};
    const access = manifest?.access?.reading_pass || {};
    const total = Number(access.total_pages || manifest?.canonical_pages?.page_count || page?.total_pages || 0);
    return {
      ...READER_V2_FIXTURE,
      title: book.public_title || book.display_title || book.title || READER_V2_FIXTURE.title,
      author: book.author || book.author_name || READER_V2_FIXTURE.author,
      chapterEyebrow: page?.chapter_id ? `Canonical page ${page.page_index}` : READER_V2_FIXTURE.chapterEyebrow,
      chapterTitle: page?.chapter_title || READER_V2_FIXTURE.chapterTitle,
      canonicalPage,
      totalPublicPages: 3,
      progress: total ? Math.round((canonicalPage / total) * 100) : 0,
      readingTime: manifest?.access?.wallet_seconds ? `${Math.floor(manifest.access.wallet_seconds / 60)}m` : READER_V2_FIXTURE.readingTime,
      readingPass: manifest?.access?.wallet_seconds ? `${Math.floor(manifest.access.wallet_seconds / 60)} minutes left` : "Sign in to continue",
      contents: (manifest?.canonical_pages?.pages || []).slice(0, 6).map((item) => `Page ${item.page_number}`),
      paragraphs: page ? paragraphsFromHtml(page.content) : [],
      metadata: {
        language: book.language || READER_V2_FIXTURE.metadata.language,
        genre: book.genre || READER_V2_FIXTURE.metadata.genre,
        year: book.publication_year || book.year || READER_V2_FIXTURE.metadata.year,
        source: book.rights_status || READER_V2_FIXTURE.metadata.source,
      },
    };
  }, [canonicalPage, manifest, page]);

  if (visualFixture) return <ReaderExperienceV2 model={READER_V2_FIXTURE} access={{ authorized: false }} onRequestPage={changePage} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug || "dracula"}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />;
  if (loading) return routeState("Opening reader", "Loading this canonical edition.");
  if (error && !manifest) return routeState("Reader unavailable", error, <Link to={`/book/${slug}`}>Return to book details</Link>);

  return <><ReaderExperienceV2 model={model} access={{ authorized: Boolean(lease) }} onRequestPage={authorizeAndContinue} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
    if (target === "signin") navigate(`/login?next=${encodeURIComponent(`/reader/${slug}?p=${canonicalPage}`)}`);
    if (target === "bookmark" && user && page?.chapter_id) void userApi.post("/bookmarks", { bookId: slug, chapterId: page.chapter_id });
  }} />{error ? <p className="sr-only" role="alert">{error}</p> : null}</>;
}
