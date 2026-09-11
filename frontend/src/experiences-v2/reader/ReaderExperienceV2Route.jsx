import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { paragraphsFromHtml } from "./readerContent";
import {
  endReadingPassSession,
  getReadingPassPage,
  renewReadingPassLease,
  saveReadingPassPosition,
  startReadingPassSession,
} from "../../lib/readingPassApi";
import { useAuth } from "../../context/AuthContext";
import ReaderExperienceV2, { READER_V2_FIXTURE } from "./ReaderExperienceV2";
import { readerRecoveryPlan, readerRouteState } from "./readerRouteState";

function pageFromSearch(search) {
  const value = Number(search.get("p") || 1);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

function routeState(title, message, action = null) {
  return <main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p role="alert">{message}</p>{action}</section></main>;
}

function ReaderRecoveryActions({ slug, canonicalPage, user, error, awaitingAuthorization, authorizing, onAuthorize }) {
  const plan = readerRecoveryPlan({ canonicalPage, user, error, awaitingAuthorization });
  const next = `/reader/${encodeURIComponent(slug)}?p=${canonicalPage}`;
  return <div className="experience-v2-route-state__actions">
    <Link to={`/book/${slug}`} data-testid="reader-recovery-book">Return to book details</Link>
    {plan.needsSignIn && <Link to={`/login?next=${encodeURIComponent(next)}`} data-testid="reader-recovery-sign-in">Sign in to continue</Link>}
    {plan.needsAuthorization && <button type="button" data-testid="reader-authorize-chapter" onClick={onAuthorize} disabled={authorizing}>{authorizing ? "Authorizing chapter…" : "Continue to this chapter"}</button>}
    {!plan.needsSignIn && plan.needsPass && <Link to="/pricing" data-testid="reader-recovery-passes">View Reading Passes</Link>}
  </div>;
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
  const [authorizing, setAuthorizing] = useState(false);
  const leaseRef = useRef(null);
  const authorizingRef = useRef(false);

  const setLeaseState = useCallback((value) => {
    leaseRef.current = value;
    setLease(value);
  }, []);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    setLoading(true);
    setError("");
    userApi.get(readerManifestPath(slug))
      .then((response) => { if (!cancelled) setManifest(response.data); })
      .catch(() => { if (!cancelled) setError("This reader edition is not available."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [slug, visualFixture]);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    setPage(null);
    if (!manifest || canonicalPage > 3 && !lease) return undefined;
    getReadingPassPage(slug, canonicalPage, lease)
      .then((value) => {
        if (cancelled) return;
        setPage(value);
        if (!value.is_preview && lease) {
          void saveReadingPassPosition({ bookSlug: slug, pageIndex: value.page_index, chapterId: value.chapter_id });
        }
      })
      .catch((requestError) => { if (!cancelled) setError(requestError?.response?.data?.detail?.message || "Reading access could not be verified."); });
    return () => { cancelled = true; };
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
    // Once the server has issued a current lease, subsequent canonical-page
    // navigation must reuse it. Starting again would correctly be rejected as
    // an active session elsewhere and strands the reader on page four.
    if (leaseRef.current?.sessionId && leaseRef.current?.token) {
      return changePage(nextPage);
    }
    if (!user || typeof user !== "object") {
      navigate(`/login?next=${encodeURIComponent(`/reader/${slug}?p=${nextPage}`)}`);
      return;
    }
    if (authorizingRef.current) return;
    authorizingRef.current = true;
    setAuthorizing(true);
    setError("");
    try {
      const started = await startReadingPassSession({ bookSlug: slug, pageIndex: nextPage });
      const nextLease = { sessionId: started.session_id, token: started.lease_token, version: Number(started.lease_version || 1), sequence: 0 };
      setLeaseState(nextLease);
      changePage(nextPage);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail?.message || "A current Reading Pass is required to continue.");
    } finally {
      authorizingRef.current = false;
      setAuthorizing(false);
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

  const expectedCanonicalPage = (manifest?.canonical_pages?.pages || []).find(
    (item) => Number(item.page_number || item.page_index) === canonicalPage,
  );
  const expectedChapter = (manifest?.chapters || []).find(
    (item) => item.id === expectedCanonicalPage?.chapter_id,
  );
  const readingPassEnabled = manifest?.access?.reading_pass?.enabled !== false;
  const awaitingAuthorization = Boolean(
    !error
    && !lease
    && canonicalPage > 3
    && readingPassEnabled
    && manifest?.book
    && expectedCanonicalPage,
  );
  const renderState = readerRouteState({
    loading,
    canonicalPage,
    page,
    error,
    expectedChapterId: expectedCanonicalPage?.chapter_id || "",
    expectedChapterTitle: expectedChapter?.title || "",
    awaitingAuthorization,
    readingPassEnabled,
  });

  if (visualFixture) return <ReaderExperienceV2 model={READER_V2_FIXTURE} access={{ authorized: false }} onRequestPage={changePage} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug || "dracula"}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />;
  if (renderState.state === "loading") return routeState("Opening reader", "Loading this canonical edition.");
  if (renderState.state === "authorization_required") return routeState("Continue to this chapter", renderState.message, <ReaderRecoveryActions slug={slug} canonicalPage={canonicalPage} user={user} error={error} awaitingAuthorization={awaitingAuthorization} authorizing={authorizing} onAuthorize={() => authorizeAndContinue(canonicalPage)} />);
  if (renderState.state === "unavailable") return routeState("Reader unavailable", renderState.message, <ReaderRecoveryActions slug={slug} canonicalPage={canonicalPage} user={user} error={error} awaitingAuthorization={false} authorizing={false} onAuthorize={undefined} />);

  return <><ReaderExperienceV2 model={model} access={{ authorized: Boolean(lease) }} onRequestPage={authorizeAndContinue} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
    if (target === "signin") navigate(`/login?next=${encodeURIComponent(`/reader/${slug}?p=${canonicalPage}`)}`);
    if (target === "bookmark" && user && page?.chapter_id) void userApi.post("/bookmarks", { bookId: slug, chapterId: page.chapter_id });
  }} />{error ? <p className="sr-only" role="alert">{error}</p> : null}</>;
}
