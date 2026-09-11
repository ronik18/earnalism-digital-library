import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { normalizeAudioManifest } from "../../lib/audioPackageManifest";
import { endReadingPassSession, renewReadingPassLease, startReadingPassAudioSession } from "../../lib/readingPassApi";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import ExperienceHeader from "../shared/ExperienceHeader";
import ListenerExperienceV2 from "./ListenerExperienceV2";
import { listenerRecoveryPlan } from "./listenerRouteState";
const LISTENER_VISUAL_FIXTURE_BOOK = Object.freeze({
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "Mark Twain",
  cover_image_url: "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1788115329/earnalism/covers/front/cover_candidate_controlled-a-ghost-story-d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742.png",
  thumbnail_url: "https://res.cloudinary.com/dzlrhlfpu/image/upload/c_fill,h_450,q_auto:best,w_300/v1788115329/earnalism/covers/front/cover_candidate_controlled-a-ghost-story-d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742.png",
});

function routeState(title, message, action = null, onSearch = null) {
  return <><ExperienceHeader onSearch={onSearch} trailingLabel="Library" /><main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p role="alert">{message}</p>{action}</section></main></>;
}

function ListenerRecoveryActions({ slug, error, onRetry = null }) {
  const plan = listenerRecoveryPlan({ error });
  return <div className="experience-v2-route-state__actions">
    <Link to={`/book/${slug}`} data-testid="listener-recovery-book">Return to book details</Link>
    {onRetry && <button type="button" onClick={onRetry} data-testid="listener-recovery-retry">Try again</button>}
    {plan.needsPass && <Link to="/pricing" data-testid="listener-recovery-passes">View Reading Passes</Link>}
  </div>;
}

export default function ListenerExperienceV2Route() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const visualFixture = process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1"
    && typeof window !== "undefined"
    && new URLSearchParams(window.location.search).get("visual-fixture") === "1";
  const [book, setBook] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [reloadAttempt, setReloadAttempt] = useState(0);
  const [lease, setLease] = useState(null);
  const [audioManifest, setAudioManifest] = useState(null);
  const [playbackState, setPlaybackState] = useState("paused");
  const [error, setError] = useState("");
  const [authorizing, setAuthorizing] = useState(false);
  const leaseRef = useRef(null);
  const authorizingRef = useRef(false);
  const endingRef = useRef(false);

  const setLeaseState = useCallback((value) => { leaseRef.current = value; setLease(value); }, []);

  const settleLease = useCallback(async (reason) => {
    const current = leaseRef.current;
    if (!current?.sessionId || endingRef.current) return;
    endingRef.current = true;
    // Stop renewal before sending the settlement request so a completed or
    // navigated Listener cannot revive its lease while the request is in flight.
    setLeaseState(null);
    setAudioManifest(null);
    try {
      await endReadingPassSession(current, reason);
    } catch {
      setError("Listening ended locally, but session settlement could not be confirmed.");
    } finally {
      endingRef.current = false;
    }
  }, [setLeaseState]);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    setBook(null);
    setLoadError("");
    userApi.get(readerManifestPath(slug)).then((response) => {
      if (cancelled) return;
      const value = response.data || {};
      setBook({ ...(value.book || {}), _readerManifest: { audio: value.audio || {}, access: value.access || {} } });
    }).catch(() => { if (!cancelled) setLoadError("Listening access could not be checked. Try again or return to this book’s details."); });
    return () => { cancelled = true; };
  }, [reloadAttempt, slug, visualFixture]);

  useEffect(() => {
    if (!lease || !book || visualFixture) return undefined;
    const presentation = listenerReleasePresentation(book);
    if (!presentation.packageManifestUrl || !presentation.packageVersion) {
      setError("This approved audiobook package is unavailable in the current Listener.");
      void settleLease("listener_v2_package_unavailable");
      return undefined;
    }
    if (audioManifest?.packageVersion === presentation.packageVersion) return undefined;
    let cancelled = false;
    setAudioManifest(null);
    userApi.get(presentation.packageManifestUrl, {
      headers: {
        "X-Reading-Pass-Session": lease.sessionId,
        "X-Reading-Pass-Lease": lease.token,
      },
      withCredentials: true,
    }).then((response) => {
      if (cancelled) return;
      const normalized = normalizeAudioManifest(response.data || {}, (value) => value, {
        expectedSlug: slug,
        expectedPackageVersion: presentation.packageVersion,
      });
      if (!normalized.valid) throw new Error("Approved listening package did not match release truth.");
      setAudioManifest(normalized);
    }).catch(() => {
      if (cancelled) return;
      setError("Approved listening package could not be verified. No audio was opened.");
      void settleLease("listener_v2_package_rejected");
    });
    return () => { cancelled = true; };
  }, [audioManifest?.packageVersion, book, lease, settleLease, slug, visualFixture]);

  useEffect(() => {
    if (!lease) return undefined;
    const interval = window.setInterval(() => {
      renewReadingPassLease({ lease, sequence: Number(lease.sequence || 0) + 1, active: playbackState === "playing", playbackState })
        .then((next) => setLeaseState({ ...lease, sessionId: next.session_id || lease.sessionId, token: next.lease_token || lease.token, version: Number(next.lease_version || lease.version), sequence: Number(lease.sequence || 0) + 1 }))
        .catch(() => { setError("Listening authorization expired."); setLeaseState(null); });
    }, 10_000);
    return () => window.clearInterval(interval);
  }, [lease, playbackState, setLeaseState]);

  useEffect(() => () => { void settleLease("listener_v2_unmount"); }, [settleLease]);

  const authorize = useCallback(async () => {
    if (!user || typeof user !== "object") {
      navigate(`/login?next=${encodeURIComponent(`/listener/${slug}`)}`);
      return;
    }
    if (authorizingRef.current) return;
    authorizingRef.current = true;
    setAuthorizing(true);
    try {
      // Audio has no public preview. A paid Reading Pass authorizes playback
      // from its first byte, including every Range request.
      const started = await startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 0 });
      setAudioManifest(null);
      setLeaseState({ sessionId: started.session_id, token: started.lease_token, version: Number(started.lease_version || 1), sequence: 0 });
      setError("");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail?.message || "A current Reading Pass is required to listen.");
    } finally {
      authorizingRef.current = false;
      setAuthorizing(false);
    }
  }, [navigate, setLeaseState, slug, user]);

  if (visualFixture) return <ListenerExperienceV2 book={LISTENER_VISUAL_FIXTURE_BOOK} fixture access={{ authorized: false }} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug || "a-ghost-story"}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />;
  const searchLibrary = () => navigate("/library");
  if (loadError) return routeState("Listener unavailable", loadError, <ListenerRecoveryActions slug={slug} error={loadError} onRetry={() => setReloadAttempt((attempt) => attempt + 1)} />, searchLibrary);
  if (book === null) return routeState("Opening listener", "Checking approved listening access.", null, searchLibrary);
  if (!listenerReleasePresentation(book).canRender) return routeState("Listening unavailable", "This edition is not approved for listening. Its book details show the available formats.", <ListenerRecoveryActions slug={slug} error="This edition is not approved for listening." />, searchLibrary);
  if (error) return routeState("Listening access needs attention", error, <ListenerRecoveryActions slug={slug} error={error} />, searchLibrary);
  if (lease && !audioManifest) return routeState("Preparing listening package", "Verifying the approved narration package before audio opens.", null, searchLibrary);
  const leaveListener = async (target) => {
    await settleLease("listener_v2_navigation");
    if (target === "back") navigate(`/book/${slug}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  };
  return <><ListenerExperienceV2 book={book} audioManifest={audioManifest} access={{ authorized: Boolean(lease && audioManifest) }} authorizing={authorizing} onAuthorize={authorize} onPlaybackStateChange={setPlaybackState} onStop={() => settleLease("listener_v2_stop")} onPlaybackComplete={() => settleLease("listener_v2_complete")} onMediaError={() => { setError("Approved listening audio could not continue. No further audio was requested."); void settleLease("listener_v2_media_error"); }} onNavigate={leaveListener} />{error ? <p className="sr-only" role="alert">{error}</p> : null}</>;
}
