import { useState } from "react";
import "./EarnalismBrandLockup.css";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const CANONICAL_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-brand-video-light.gif`;
const STATIC_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-brand-video-still.png`;
const BUNDLED_FALLBACK = `${PUBLIC_URL}/assets/brand/earnalism-logo-text-original.png`;

const VARIANTS = new Set([
  "desktop-header",
  "mobile-header",
  "footer",
  "auth",
  "account",
  "editorial",
  "standalone-experience",
]);

/** The sole visible lockup for public customer-shell surfaces. */
export default function EarnalismBrandLockup({ variant = "desktop-header", className = "" }) {
  const [source, setSource] = useState(CANONICAL_LOGO);
  const safeVariant = VARIANTS.has(variant) ? variant : "desktop-header";

  return (
    <span
      className={`earnalism-brand-lockup earnalism-brand-lockup--${safeVariant} ${className}`.trim()}
      data-testid="earnalism-brand-lockup"
      data-brand-asset="earnalism-brand-video-light.gif"
    >
      <picture>
      <source media="(prefers-reduced-motion: reduce)" srcSet={source === BUNDLED_FALLBACK ? BUNDLED_FALLBACK : STATIC_LOGO} />
      <img
        src={source}
        alt="Earnalism — Where Learning Becomes Earning"
        width="520"
        height="156"
        decoding="async"
        fetchPriority={safeVariant === "desktop-header" ? "high" : undefined}
        onError={() => {
          if (source === CANONICAL_LOGO) setSource(STATIC_LOGO);
          else if (source !== BUNDLED_FALLBACK) setSource(BUNDLED_FALLBACK);
        }}
      />
      </picture>
    </span>
  );
}
