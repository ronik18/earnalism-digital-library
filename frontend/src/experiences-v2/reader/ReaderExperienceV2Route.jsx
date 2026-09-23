import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { ReaderContent } from "./readerContent";
import {
  endReadingPassSession, getReadingPassPosition, getReadingPassPage,
  renewReadingPassLease, saveReadingPassPosition, startReadingPassSession,
} from "../../lib/readingPassApi";
import { useAuth } from "../../context/AuthContext";
import ReaderExperienceV2, { READER_V2_FIXTURE } from "./ReaderExperienceV2";
import { readerRouteState } from "./readerRouteState";

const PREVIEW_PAGES = 3;
const pageFromSearch = (search) => {
  const value = Number(search.get("p") || 1);
  return Number.isInteger(value) && value > 0 ? value : 1;
};
const positionVersion = (value) => Number.isInteger(Number(value)) && Number(value) >= 0 ? Number(value) : 0;
const requestMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  return (typeof detail === "string" ? detail : detail?.message) || fallback;
};
const runningLease = (lease) => Boolean(lease?.status === "Running" && lease.sessionId && lease.token && lease.expiresAt > Date.now());
const validBalance = (seconds) => Number.isSafeInteger(seconds) && seconds >= 0 ? seconds : null;

function leaseResponse(response, slug, previous = null, sequence = 0) {
  if (!response?.session_id || (previous && response.session_id !== previous.sessionId)
    || (response.content_id && response.content_id !== slug)
    || (response.content_type && response.content_type !== "text")) return null;
  const value = {
    sessionId: response.session_id,
    token: response.lease_token || previous?.token,
    version: Number(response.lease_version),
    sequence,
    status: response.status,
    expiresAt: Date.parse(response.lease_expires_at),
    balance: validBalance(response.balance_seconds),
    heartbeatMs: previous?.heartbeatMs || Math.max(1000, Math.min(10000, Number(response.heartbeat_seconds || 10) * 1000)),
  };
  if (!value.token || !Number.isInteger(value.version) || value.version < 1 || !Number.isFinite(value.expiresAt)
    || !Number.isFinite(value.balance) || value.balance < 0) return null;
  return value;
}

function RouteState({ title, message, children }) {
  return <main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p role="alert">{message}</p><div className="experience-v2-route-state__actions">{children}</div></section></main>;
}

// A different title or signed-in identity must never inherit another reader's
// manifest, in-flight response, saved-position version, or paid lease.
export default function ReaderExperienceV2Route() {
  const { slug = "" } = useParams();
  const { user, setUserBalance } = useAuth();
  const identity = user?.id || user?.email || (user ? "member" : "guest");
  const syncBalance = useCallback((seconds) => setUserBalance?.(seconds, identity), [identity, setUserBalance]);
  return <ReaderSession key={`${slug}:${identity}`} slug={slug} user={user} syncBalance={syncBalance} />;
}

function ReaderSession({ slug, user, syncBalance }) {
  const [search, setSearch] = useSearchParams();
  const navigate = useNavigate();
  const canonicalPage = pageFromSearch(search);
  const visualFixtureVariant = process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1" ? search.get("visual-fixture") : null;
  const visualFixture = visualFixtureVariant === "1" || visualFixtureVariant === "bn";
  const [manifest, setManifest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pageResult, setPageResult] = useState(null);
  const [lease, setLease] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [balance, setBalance] = useState(null);
  const signedIn = Boolean(user);
  // Public/guest manifests can be cached independently of the customer. Only
  // the verified profile or a newer validated session response describes time.
  const displayedBalance = balance ?? validBalance(user?.reading_seconds_balance);
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [manifestRetry, setManifestRetry] = useState(0);
  const aliveRef = useRef(true);
  const leaseRef = useRef(null);
  const renewPromiseRef = useRef(null);
  const settlementRef = useRef(null);
  const closingRef = useRef(false);
  const actionRef = useRef(false);
  const pageRef = useRef(canonicalPage);
  pageRef.current = canonicalPage;
  const locationVersionRef = useRef({ search: search.toString(), version: 0 });
  const pendingPageRef = useRef(null);
  if (locationVersionRef.current.search !== search.toString()) {
    locationVersionRef.current = { search: search.toString(), version: locationVersionRef.current.version + 1 };
    pendingPageRef.current = null;
  }
  const lastActivityRef = useRef(Date.now());
  const displayedPageRef = useRef(false);
  displayedPageRef.current = Boolean(!error && pageResult?.number === canonicalPage && pageResult.status === "ready");
  const positionVersionRef = useRef(null);
  const positionQueueRef = useRef(Promise.resolve());

  const publishBalance = useCallback((seconds) => {
    if (!aliveRef.current || validBalance(seconds) === null) return;
    setBalance(seconds);
    syncBalance(seconds);
  }, [syncBalance]);

  const publishLease = useCallback((value) => {
    leaseRef.current = value;
    if (aliveRef.current) {
      setLease(value);
      publishBalance(value?.balance);
    }
  }, [publishBalance]);

  const settleLease = useCallback((reason) => {
    if (settlementRef.current) return settlementRef.current;
    if (!leaseRef.current?.sessionId) return Promise.resolve(true);
    closingRef.current = true;
    const current = leaseRef.current;
    const pending = (async () => {
      try {
        await renewPromiseRef.current?.catch(() => undefined);
        const ended = await endReadingPassSession(current, reason);
        // The existing endpoint returns ended:false when no active/paused
        // session remains for this exact authenticated identity and session.
        // It is an idempotent terminal result, not a fresh debit confirmation.
        if (ended?.session_id !== current.sessionId || typeof ended.ended !== "boolean") return false;
        if (leaseRef.current?.sessionId === current.sessionId) publishLease(null);
        publishBalance(ended.balance_seconds);
        return true;
      } catch {
        return false;
      } finally {
        closingRef.current = false;
        settlementRef.current = null;
      }
    })();
    settlementRef.current = pending;
    return pending;
  }, [publishBalance, publishLease]);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      // Settlement is serialized behind any heartbeat. Late start responses
      // separately close their issued session without updating this component.
      void settleLease("reader_v2_unmount");
    };
  }, [settleLease]);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    userApi.get(readerManifestPath(slug), { signal: controller.signal, timeout: 15000 })
      .then(({ data }) => {
        if (cancelled) return;
        if (data?.book?.slug !== slug) throw new Error("This reader edition does not match the requested book.");
        setManifest(data);
      })
      .catch(() => { if (!cancelled) setError("This reader edition is not available."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; controller.abort(); };
  }, [slug, visualFixture, manifestRetry]);

  const persistPosition = useCallback((value) => {
    positionQueueRef.current = positionQueueRef.current.catch(() => undefined).then(async () => {
      if (!aliveRef.current) return;
      if (positionVersionRef.current === null) {
        const saved = await getReadingPassPosition({ contentType: "text", contentId: slug });
        positionVersionRef.current = positionVersion(saved?.version);
      }
      if (!aliveRef.current) return;
      const saved = await saveReadingPassPosition({
        bookSlug: slug,
        pageIndex: value.page_index,
        chapterId: value.chapter_id,
        segmentationVersion: value.segmentation_version,
        manifestVersion: value.manifest_version,
        version: positionVersionRef.current,
      });
      positionVersionRef.current = positionVersion(saved?.version);
      return saved;
    });
    return positionQueueRef.current;
  }, [slug]);

  const invalidateLease = useCallback((message) => {
    const current = leaseRef.current;
    if (current) publishLease({ ...current, status: "Expired" });
    if (aliveRef.current) {
      setError(message);
      setPageResult(null);
    }
    void settleLease("reader_v2_access_stopped").then((settled) => {
      if (!settled && aliveRef.current) setNotice("We could not close the reading session. Retry before opening another book.");
    });
  }, [publishLease, settleLease]);

  const renewLease = useCallback((active) => {
    if (renewPromiseRef.current || closingRef.current || !aliveRef.current) return renewPromiseRef.current;
    const current = leaseRef.current;
    if (!current || !["Running", "Paused"].includes(current.status)) return null;
    const sequence = current.sequence + 1;
    const request = { lease: current, sequence, active, idempotencyKey: `${current.sessionId}:${sequence}:reader-v2` };
    const pending = (async () => {
      try {
        let response;
        try {
          response = await renewReadingPassLease(request);
        } catch (requestError) {
          const status = requestError?.response?.status;
          if ((status && status < 500) || !runningLease(current) || closingRef.current || !aliveRef.current) throw requestError;
          // One bounded transport retry of precisely the same logical request.
          // If the first response was lost, the server returns its saved result.
          response = await renewReadingPassLease(request);
        }
        if (!aliveRef.current || closingRef.current || leaseRef.current?.sessionId !== current.sessionId) return;
        const next = leaseResponse(response, slug, current, sequence);
        if (!next || response.stale || !["Running", "Paused"].includes(next.status) || (next.status === "Running" && !runningLease(next))) {
          // No recursive retries and no treating an HTTP 200 terminal/stale
          // response as a usable authorization.
          const terminalBalance = !response.stale && next && ["Exhausted", "Expired", "Ended"].includes(next.status) ? next.balance : current.balance;
          publishLease({ ...current, status: "Expired", balance: terminalBalance });
          setError(response?.status === "Exhausted" && manifest?.access?.reading_pass?.free_entitlement !== true ? "Your Reading Pass time has run out." : "Your reading session needs to be renewed. Continue when you are ready.");
          setPageResult(null);
          return;
        }
        publishLease(next);
        setNotice("");
      } catch (requestError) {
        if (!aliveRef.current || closingRef.current) return;
        if (requestError?.response?.status >= 400 && requestError.response.status < 500) {
          publishLease({ ...current, status: "Expired" });
          setPageResult(null);
          setError(requestMessage(requestError, "Your reading session has ended. Continue when you are ready."));
        } else {
          // Preserve the last validated page only until the existing server
          // lease expires. The expiry timer below does not extend that grant.
          setNotice("Connection interrupted. Reconnecting while your reading session is valid.");
        }
      } finally {
        renewPromiseRef.current = null;
      }
    })();
    renewPromiseRef.current = pending;
    return pending;
  }, [manifest, publishLease, slug]);

  const totalPages = Number(manifest?.access?.reading_pass?.total_pages || manifest?.canonical_pages?.page_count || 0);
  const expectedPage = (manifest?.canonical_pages?.pages || []).find((item) => Number(item.page_number || item.page_index) === canonicalPage);
  const expectedChapter = (manifest?.chapters || []).find((item) => item.id === expectedPage?.chapter_id);
  const enabled = manifest?.access?.reading_pass?.enabled !== false;
  const freeReading = manifest?.access?.reading_pass?.free_entitlement === true;
  const validPage = Boolean(expectedPage && Number.isInteger(totalPages) && canonicalPage <= totalPages);
  const sessionId = lease?.sessionId || "";
  const leaseStatus = lease?.status || "";
  const heartbeatMs = lease?.heartbeatMs || 10000;
  const inactivityMs = Math.max(1000, Number(manifest?.access?.reading_pass?.text_inactivity_seconds || 120) * 1000);
  const activelyReading = useCallback(() => document.visibilityState === "visible" && document.hasFocus()
    && Date.now() - lastActivityRef.current < inactivityMs && pageRef.current > PREVIEW_PAGES && displayedPageRef.current, [inactivityMs]);
  useEffect(() => {
    // Browser back/forward can change the URL without using our page buttons.
    // A preview or terminal state must never keep a paid session running.
    if (sessionId && ((canonicalPage <= PREVIEW_PAGES && pendingPageRef.current === null) || leaseStatus === "Expired" || (manifest && (!enabled || !validPage)))) {
      void settleLease("reader_v2_inactive").then((settled) => {
        if (!settled && aliveRef.current) setNotice("Your reading session could not be closed. Please retry before leaving this reader.");
      });
    }
  }, [canonicalPage, sessionId, leaseStatus, settleLease, manifest, enabled, validPage]);
  useEffect(() => {
    if (!sessionId || leaseStatus !== "Running") return undefined;
    const interval = window.setInterval(() => {
      if (pageRef.current > PREVIEW_PAGES) void renewLease(activelyReading());
    }, heartbeatMs);
    return () => window.clearInterval(interval);
  }, [sessionId, leaseStatus, heartbeatMs, renewLease, activelyReading]);

  useEffect(() => {
    if (!sessionId) return undefined;
    const onVisibility = async () => {
      // A visibility transition arriving during a request is handled after it,
      // using its new sequence/version. Hidden tabs stop billable activity.
      await renewPromiseRef.current?.catch(() => undefined);
      if (!aliveRef.current || closingRef.current) return;
      if (document.visibilityState === "visible" && document.hasFocus()) lastActivityRef.current = Date.now();
      void renewLease(activelyReading());
    };
    const onActivity = () => {
      lastActivityRef.current = Date.now();
      if (leaseRef.current?.status === "Paused" && activelyReading()) void onVisibility();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("focus", onVisibility);
    window.addEventListener("blur", onVisibility);
    ["pointerdown", "keydown", "scroll"].forEach((event) => document.addEventListener(event, onActivity, { passive: true }));
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", onVisibility);
      window.removeEventListener("blur", onVisibility);
      ["pointerdown", "keydown", "scroll"].forEach((event) => document.removeEventListener(event, onActivity));
    };
  }, [sessionId, renewLease, activelyReading]);

  useEffect(() => {
    if (leaseStatus !== "Running" || !lease?.expiresAt) return undefined;
    const expiry = lease.expiresAt;
    const timeout = window.setTimeout(() => {
      if (leaseRef.current?.expiresAt === expiry && !runningLease(leaseRef.current)) invalidateLease("Your reading session expired. Continue when you are ready.");
    }, Math.max(0, expiry - Date.now()) + 1);
    return () => window.clearTimeout(timeout);
  }, [leaseStatus, lease?.expiresAt, invalidateLease]);

  const usable = runningLease(lease);
  // Only a newly usable SESSION changes content authorization. Rotating lease
  // versions, expiry, sequence and balance never refetch the same page.
  const pageSessionKey = canonicalPage > PREVIEW_PAGES && usable ? sessionId : "";
  useEffect(() => {
    if (visualFixture || !manifest || !enabled || !validPage || (canonicalPage > PREVIEW_PAGES && !pageSessionKey)) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setPageResult({ number: canonicalPage, status: "loading" });
    setError("");
    const requestLease = canonicalPage > PREVIEW_PAGES ? leaseRef.current : null;
    getReadingPassPage(slug, canonicalPage, requestLease, { signal: controller.signal })
      .then((value) => {
        if (cancelled || !aliveRef.current) return;
        if (canonicalPage > PREVIEW_PAGES && !runningLease(leaseRef.current)) return;
        if (value.book_slug !== slug || !Number.isInteger(value.total_pages) || value.total_pages !== totalPages
          || typeof value.is_preview !== "boolean" || value.is_preview !== (canonicalPage <= PREVIEW_PAGES)
          || typeof value.content !== "string" || !value.content.trim()
          || (expectedPage.content_hash && value.content_sha256 !== expectedPage.content_hash)) throw new Error("This page does not match the selected edition. Reopen the book to load its current version.");
        const state = readerRouteState({ canonicalPage, page: value, expectedChapterId: expectedPage.chapter_id || "", expectedChapterTitle: expectedChapter?.title || "" });
        if (state.state !== "ready") throw new Error(state.message);
        setPageResult({ number: canonicalPage, status: "ready", value });
        setError("");
        if (signedIn) void persistPosition(value).catch(() => {
          if (aliveRef.current) setNotice("Your page is open, but your reading position could not be saved.");
        });
      })
      .catch((requestError) => {
        if (cancelled || !aliveRef.current) return;
        setPageResult({ number: canonicalPage, status: "error" });
        setError(requestMessage(requestError, requestError.message || "This page could not be loaded. Please retry."));
        if (leaseRef.current) publishLease({ ...leaseRef.current, status: "Expired" });
      });
    return () => { cancelled = true; controller.abort(); };
  }, [canonicalPage, pageSessionKey, manifest, enabled, validPage, expectedPage, expectedChapter, persistPosition, retry, publishLease, slug, totalPages, signedIn, visualFixture]);

  const changePage = useCallback((nextPage) => {
    const params = new URLSearchParams(search);
    params.set("p", String(nextPage));
    setSearch(params, { replace: false });
  }, [search, setSearch]);

  const authorizeAndContinue = useCallback(async (nextPage) => {
    if (!Number.isInteger(nextPage) || nextPage < 1 || nextPage > totalPages || actionRef.current) return;
    if (nextPage > PREVIEW_PAGES && !user) {
      navigate(`/login?next=${encodeURIComponent(`/reader/${slug}?p=${nextPage}`)}`);
      return;
    }
    actionRef.current = true;
    const intentVersion = locationVersionRef.current.version;
    setBusy(true);
    setNotice("");
    try {
      if (nextPage <= PREVIEW_PAGES) {
        if (!await settleLease("reader_v2_preview")) throw new Error("Your reading session could not be closed. Please retry.");
      } else if (!runningLease(leaseRef.current)) {
        if (!await settleLease("reader_v2_reauthorize")) throw new Error("Your reading session could not be closed. Please retry.");
        const started = await startReadingPassSession({ bookSlug: slug, pageIndex: nextPage });
        if (!aliveRef.current || locationVersionRef.current.version !== intentVersion) {
          if (started?.session_id) void endReadingPassSession({ sessionId: started.session_id }, "reader_v2_start_after_exit").catch(() => undefined);
          return;
        }
        const nextLease = leaseResponse(started, slug);
        if (!runningLease(nextLease)) {
          if (started?.session_id) await endReadingPassSession({ sessionId: started.session_id }, "reader_v2_invalid_start");
          throw new Error("Reading access could not be verified. Please try again.");
        }
        // Router transitions can render the old preview once before the new
        // URL commits. Do not settle the lease just issued for that transition.
        pendingPageRef.current = nextPage;
        publishLease(nextLease);
        lastActivityRef.current = Date.now();
      }
      if (!aliveRef.current || locationVersionRef.current.version !== intentVersion) return;
      setError("");
      if (nextPage === canonicalPage) setRetry((value) => value + 1);
      else changePage(nextPage);
    } catch (requestError) {
      if (aliveRef.current) setError(requestMessage(requestError, requestError.message || (freeReading ? "Free Reader access could not be verified." : "A current Reading Pass is required to continue.")));
    } finally {
      actionRef.current = false;
      if (aliveRef.current) setBusy(false);
    }
  }, [canonicalPage, changePage, freeReading, navigate, publishLease, settleLease, slug, totalPages, user]);

  const navigateAfterSettlement = useCallback(async (target) => {
    if (actionRef.current) return;
    actionRef.current = true;
    setBusy(true);
    const destinations = { back: `/book/${slug}`, library: "/library", search: "/library", passes: "/pricing", home: "/", profile: "/account", signin: `/login?next=${encodeURIComponent(`/reader/${slug}?p=${canonicalPage}`)}` };
    try {
      if (!await settleLease("reader_v2_navigation")) {
        setNotice("Your reading session could not be closed. Please retry before leaving this reader.");
        return;
      }
      if (aliveRef.current && destinations[target]) navigate(destinations[target]);
    } finally {
      actionRef.current = false;
      if (aliveRef.current) setBusy(false);
    }
  }, [canonicalPage, navigate, settleLease, slug]);

  const page = pageResult?.number === canonicalPage && pageResult.status === "ready" ? pageResult.value : null;
  const model = useMemo(() => {
    const book = manifest?.book || {};
    return {
      title: book.public_title || book.display_title || book.title || "Book",
      author: book.author || book.author_name || "",
      language: /^(bn|bengali|বাংলা)/i.test(book.language || "") ? "bn" : /^(en|english)/i.test(book.language || "") ? "en" : undefined,
      chapterEyebrow: `Page ${canonicalPage} of ${totalPages}`,
      chapterTitle: page?.chapter_title || book.title || "",
      canonicalPage, totalPages, totalPublicPages: PREVIEW_PAGES,
      progress: totalPages ? Math.round((canonicalPage / totalPages) * 100) : 0,
      readingTime: "",
      readingPass: !user ? "Sign in to continue" : displayedBalance === null ? "Balance unavailable" : displayedBalance < 60 ? `${displayedBalance} seconds left` : `${Math.floor(displayedBalance / 60)} minutes left`,
      freeReading,
      contents: (manifest?.canonical_pages?.pages || []).map((item) => ({ page: Number(item.page_number || item.page_index), label: `Page ${item.page_number || item.page_index}` })),
      content: page ? <ReaderContent html={page.content} /> : null,
      paragraphs: [],
      illustration: null,
      statusMessage: notice,
      metadata: { language: book.language || "", genre: book.genre || "", year: book.publication_year || book.year || "", source: book.rights_status || "" },
    };
  }, [displayedBalance, canonicalPage, freeReading, manifest, notice, page, totalPages, user]);

  const recovery = <>
    <button type="button" data-testid="reader-recovery-book" onClick={() => navigateAfterSettlement("back")} disabled={busy}>Return to book details</button>
    <button type="button" onClick={() => navigateAfterSettlement("library")} disabled={busy}>Library</button>
    {!manifest && !loading && <button type="button" onClick={() => setManifestRetry((value) => value + 1)}>Retry reader</button>}
    {!user && canonicalPage > PREVIEW_PAGES && <Link data-testid="reader-recovery-sign-in" to={`/login?next=${encodeURIComponent(`/reader/${slug}?p=${canonicalPage}`)}`}>Sign in to continue</Link>}
    {validPage && enabled && (canonicalPage <= PREVIEW_PAGES || user) && <button type="button" data-testid="reader-authorize-chapter" onClick={() => authorizeAndContinue(canonicalPage)} disabled={busy}>{busy ? "Opening page…" : canonicalPage <= PREVIEW_PAGES ? "Retry page" : "Continue to this page"}</button>}
    {user && !freeReading && <button type="button" data-testid="reader-recovery-passes" onClick={() => navigateAfterSettlement("passes")} disabled={busy}>View Reading Passes</button>}
    {notice && <p role="status">{notice}</p>}
  </>;
  if (visualFixture) {
    const fixtureModel = visualFixtureVariant === "bn" ? {
      ...READER_V2_FIXTURE,
      title: "পথের পাঁচালী",
      author: "বিভূতিভূষণ বন্দ্যোপাধ্যায়",
      language: "bn",
      chapterEyebrow: "প্রথম পরিচ্ছেদ",
      chapterTitle: "অপু ও দুর্গা",
      paragraphs: ["বাংলা পাঠ্যের যুক্তাক্ষর, স্বরচিহ্ন এবং বিরামচিহ্ন স্বাভাবিক পাঠের অংশ।", "এই বিচ্ছিন্ন পরীক্ষার নমুনা কেবল পাঠ-টাইপোগ্রাফি যাচাই করে; এটি কোনো প্রকাশিত পৃষ্ঠা বা অডিও অনুরোধ করে না।"],
    } : READER_V2_FIXTURE;
    return <ReaderExperienceV2 model={fixtureModel} access={{ authorized: false }} onRequestPage={changePage} onNavigate={(target) => { if (["library", "search"].includes(target)) navigate("/library"); }} />;
  }
  const loadingExit = <button type="button" onClick={() => navigateAfterSettlement("library")} disabled={busy}>{busy ? "Closing reader…" : "Library"}</button>;
  if (loading) return <RouteState title="Opening reader" message="Loading this edition.">{loadingExit}</RouteState>;
  if (error) return <RouteState title="Reading paused" message={error}>{recovery}</RouteState>;
  if (!enabled || !validPage) return <RouteState title="Page unavailable" message="This page is not available in this edition.">{recovery}</RouteState>;
  if (canonicalPage > PREVIEW_PAGES && !usable) return <RouteState title={leaseStatus === "Paused" ? "Reading paused" : "Continue reading"} message={leaseStatus === "Paused" ? "Your reading session is paused while the reader is inactive." : freeReading ? "Sign in to continue reading this edition free." : "Use your Reading Pass to open this page."}>{recovery}</RouteState>;
  if (!page) return <RouteState title="Opening page" message="Loading your selected page.">{loadingExit}</RouteState>;
  return <ReaderExperienceV2 model={model} access={{ authorized: usable, busy }} onRequestPage={authorizeAndContinue} onNavigate={(target) => {
    if (target === "bookmark") {
      if (!user) { void navigateAfterSettlement("signin"); return; }
      void persistPosition(page).then(() => { if (aliveRef.current) setNotice("Your current page is saved."); }).catch(() => { if (aliveRef.current) setNotice("Your page could not be saved. Please try again."); });
    } else void navigateAfterSettlement(target);
  }} />;
}
