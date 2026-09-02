import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { isRequestCancellation } from "../../lib/requestCancellation";
import { endReadingPassSession, renewReadingPassLease, startReadingPassAudioSession } from "../../lib/readingPassApi";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import ListenerExperienceV2 from "./ListenerExperienceV2";
const LISTENER_VISUAL_FIXTURE_BOOK = Object.freeze({
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "Mark Twain",
  cover_image_url: "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1788115329/earnalism/covers/front/cover_candidate_controlled-a-ghost-story-d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742.png",
  thumbnail_url: "https://res.cloudinary.com/dzlrhlfpu/image/upload/c_fill,h_450,q_auto:best,w_300/v1788115329/earnalism/covers/front/cover_candidate_controlled-a-ghost-story-d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742.png",
});

function routeState(title, message) {
  return <main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p>{message}</p></section></main>;
}

export default function ListenerExperienceV2Route() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const visualFixture = process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1"
    && typeof window !== "undefined"
    && new URLSearchParams(window.location.search).get("visual-fixture") === "1";
  const [book, setBook] = useState(null);
  const [lease, setLease] = useState(null);
  const [playbackState, setPlaybackState] = useState("paused");
  const [error, setError] = useState("");
  const leaseRef = useRef(null);

  const setLeaseState = useCallback((value) => { leaseRef.current = value; setLease(value); }, []);

  useEffect(() => {
    if (visualFixture) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    userApi.get(readerManifestPath(slug), { signal: controller.signal }).then((response) => {
      if (cancelled) return;
      const value = response.data || {};
      setBook({ ...(value.book || {}), _readerManifest: { audio: value.audio || {}, access: value.access || {} } });
    }).catch((requestError) => {
      if (!cancelled && !isRequestCancellation(requestError)) setBook({});
    });
    return () => { cancelled = true; controller.abort(); };
  }, [slug, visualFixture]);

  useEffect(() => {
    if (!lease) return undefined;
    const interval = window.setInterval(() => {
      renewReadingPassLease({ lease, sequence: Number(lease.sequence || 0) + 1, active: playbackState === "playing", playbackState })
        .then((next) => setLeaseState({ ...lease, sessionId: next.session_id || lease.sessionId, token: next.lease_token || lease.token, version: Number(next.lease_version || lease.version), sequence: Number(lease.sequence || 0) + 1 }))
        .catch(() => { setError("Listening authorization expired."); setLeaseState(null); });
    }, 10_000);
    return () => window.clearInterval(interval);
  }, [lease, playbackState, setLeaseState]);

  useEffect(() => () => { if (leaseRef.current?.sessionId) void endReadingPassSession(leaseRef.current, "listener_v2_unmount"); }, []);

  const authorize = useCallback(async () => {
    if (!user || typeof user !== "object") {
      navigate(`/login?next=${encodeURIComponent(`/listener/${slug}`)}`);
      return;
    }
    try {
      // Audio has no public preview. A paid Reading Pass authorizes playback
      // from its first byte, including every Range request.
      const started = await startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 0 });
      setLeaseState({ sessionId: started.session_id, token: started.lease_token, version: Number(started.lease_version || 1), sequence: 0 });
      setError("");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail?.message || "A current Reading Pass is required to listen.");
    }
  }, [navigate, setLeaseState, slug, user]);

  if (visualFixture) return <ListenerExperienceV2 book={LISTENER_VISUAL_FIXTURE_BOOK} fixture access={{ authorized: false }} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug || "a-ghost-story"}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />;
  if (book === null) return routeState("Opening listener", "Checking approved listening access.");
  if (!listenerReleasePresentation(book).canRender) return <Navigate to={`/book/${slug}`} replace />;
  return <><ListenerExperienceV2 book={book} access={{ authorized: Boolean(lease) }} onAuthorize={authorize} onPlaybackStateChange={setPlaybackState} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />{error ? <p className="sr-only" role="alert">{error}</p> : null}</>;
}
