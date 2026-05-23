import { useEffect, useMemo, useRef, useState } from "react";
import { API, USER_TOKEN_KEY } from "../lib/api";

const DEFAULT_LICENSE_NOTICE = "This Earnalism reading copy is provided for lawful personal reading. Do not redistribute, scrape, or reproduce the platform-rendered edition without permission. Public-domain source texts remain subject to their applicable rights status.";
const DEFAULT_LICENSE_METADATA = "Earnalism - Platform Reading Edition";

function simpleHash(value = "") {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function tokenFingerprint() {
  if (typeof window === "undefined") return "";
  const token = localStorage.getItem(USER_TOKEN_KEY) || "";
  return token ? simpleHash(token).slice(0, 12) : "";
}

function sendSecurityEvent(payload) {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem(USER_TOKEN_KEY);
  const body = JSON.stringify(payload);
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  fetch(`${API}/secure-reader/events`, {
    method: "POST",
    headers,
    body,
    keepalive: true,
  }).catch(() => {});
}

export default function SecureReader({
  sessionId,
  userName = "Reader",
  userEmail = "",
  bookSlug = "",
  chapterId = "",
  title = "Licensed ebook",
  html = "",
  children,
  contentRef,
  className = "",
  style,
  lang,
  blurred = false,
  onViolation,
  licenseNotice = DEFAULT_LICENSE_NOTICE,
  licenseMetadata = DEFAULT_LICENSE_METADATA,
  watermarkText: customWatermarkText = "",
  footerText: customFooterText = "",
}) {
  const [shielded, setShielded] = useState(false);
  const localRef = useRef(null);
  const countsRef = useRef({});
  const safeSessionId = sessionId || "reader-session";
  const emailHash = useMemo(() => simpleHash(userEmail || "guest").slice(0, 8), [userEmail]);
  const issuedAt = useMemo(() => new Date().toISOString(), []);
  const watermarkIdentity = userName || (userEmail ? userEmail.split("@")[0] : "Reader");
  const watermarkText = customWatermarkText || `Earnalism Reading Edition · ${watermarkIdentity} · ${issuedAt.slice(0, 10)}`;
  const footerText = customFooterText || `Licensed reading copy - Redistribution prohibited`;

  const report = (eventType, metadata = {}) => {
    countsRef.current[eventType] = (countsRef.current[eventType] || 0) + 1;
    onViolation?.(eventType, countsRef.current);
    sendSecurityEvent({
      session_id: safeSessionId,
      event_type: eventType,
      book_slug: bookSlug,
      chapter_id: chapterId,
      access_token_fingerprint: tokenFingerprint(),
      counts: countsRef.current,
      metadata,
    });
  };

  const temporarilyShield = () => {
    setShielded(true);
    window.setTimeout(() => setShielded(false), 1400);
  };

  useEffect(() => {
    report("session_start", { title });
    const onKeyDown = (event) => {
      const key = String(event.key || "").toLowerCase();
      const blockedShortcut = (event.ctrlKey || event.metaKey) && ["s", "p", "u", "a"].includes(key);
      if (blockedShortcut) {
        event.preventDefault();
        event.stopPropagation();
        report("blocked_shortcut", { key });
      }
    };
    const onKeyUp = (event) => {
      if (event.key === "PrintScreen") {
        report("print_screen");
        temporarilyShield();
      }
    };
    const onBeforePrint = (event) => {
      event.preventDefault?.();
      report("print");
      temporarilyShield();
    };
    const onVisibilityChange = () => {
      if (document.hidden) report("visibility_hidden");
    };

    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("keyup", onKeyUp, true);
    window.addEventListener("beforeprint", onBeforePrint);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      report("session_end");
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("keyup", onKeyUp, true);
      window.removeEventListener("beforeprint", onBeforePrint);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      if (localRef.current) localRef.current.textContent = "";
    };
    // sessionId intentionally owns the lifecycle; counts remain per reader mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safeSessionId]);

  const block = (event, eventType) => {
    event.preventDefault();
    event.stopPropagation();
    report(eventType);
    if (eventType === "copy" || eventType === "cut") temporarilyShield();
  };

  return (
    <section
      className={`secure-reader ${shielded || blurred ? "secure-reader--shielded" : ""}`}
      aria-label="Secure licensed ebook reader"
      onContextMenu={(event) => block(event, "right_click")}
      onCopy={(event) => block(event, "copy")}
      onCut={(event) => block(event, "cut")}
      onDragStart={(event) => block(event, "drag")}
      onDrop={(event) => block(event, "drop")}
    >
      <svg className="secure-reader__metadata" width="0" height="0" aria-hidden="true" focusable="false">
        <metadata>{licenseMetadata}</metadata>
      </svg>
      <div className="secure-reader__watermark" aria-hidden="true">
        {Array.from({ length: 18 }, (_, index) => (
          <span key={index}>{watermarkText}</span>
        ))}
      </div>
      <div
        ref={(node) => {
          localRef.current = node;
          if (contentRef) contentRef.current = node;
        }}
        className={`secure-reader__content ${className}`}
        style={style}
        lang={lang}
        role="document"
        aria-label={title}
        data-license={licenseMetadata}
        data-session={safeSessionId}
        data-email-hash={emailHash}
        dangerouslySetInnerHTML={html ? { __html: html } : undefined}
      >
        {!html ? children : null}
      </div>
      <footer className="secure-reader__page-footer" aria-label="Licensed reading notice">
        <span>{footerText}</span>
        {licenseNotice && (
          <details className="secure-reader__legal">
            <summary>Terms</summary>
            <p>{licenseNotice}</p>
          </details>
        )}
      </footer>
    </section>
  );
}
