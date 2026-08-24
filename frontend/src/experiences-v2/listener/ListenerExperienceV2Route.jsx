import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { userApi } from "../../lib/api";
import { readerManifestPath } from "../../lib/audioReleaseSafety";
import { endReadingPassSession, renewReadingPassLease, startReadingPassAudioSession } from "../../lib/readingPassApi";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import ListenerExperienceV2 from "./ListenerExperienceV2";

function routeState(title, message) {
  return <main className="experience-v2-route-state"><section className="experience-v2-route-state__card"><h1>{title}</h1><p>{message}</p></section></main>;
}

export default function ListenerExperienceV2Route() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [book, setBook] = useState(null);
  const [lease, setLease] = useState(null);
  const [playbackState, setPlaybackState] = useState("paused");
  const [error, setError] = useState("");
  const leaseRef = useRef(null);

  const setLeaseState = useCallback((value) => { leaseRef.current = value; setLease(value); }, []);

  useEffect(() => {
    let cancelled = false;
    userApi.get(readerManifestPath(slug)).then((response) => {
      if (cancelled) return;
      const value = response.data || {};
      setBook({ ...(value.book || {}), _readerManifest: { audio: value.audio || {}, access: value.access || {} } });
    }).catch(() => { if (!cancelled) setBook({}); });
    return () => { cancelled = true; };
  }, [slug]);

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
      // Audio preview is not a public capability. The current server marks
      // 180 seconds as the protected continuation boundary.
      const started = await startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 180 });
      setLeaseState({ sessionId: started.session_id, token: started.lease_token, version: Number(started.lease_version || 1), sequence: 0 });
      setError("");
    } catch (requestError) {
      setError(requestError?.response?.data?.detail?.message || "A current Reading Pass is required to listen.");
    }
  }, [navigate, setLeaseState, slug, user]);

  if (book === null) return routeState("Opening listener", "Checking approved listening access.");
  if (!listenerReleasePresentation(book).canRender) return <Navigate to={`/book/${slug}`} replace />;
  return <><ListenerExperienceV2 book={book} access={{ authorized: Boolean(lease) }} onAuthorize={authorize} onPlaybackStateChange={setPlaybackState} onNavigate={(target) => {
    if (target === "back") navigate(`/book/${slug}`);
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
  }} />{error ? <p className="sr-only" role="alert">{error}</p> : null}</>;
}
