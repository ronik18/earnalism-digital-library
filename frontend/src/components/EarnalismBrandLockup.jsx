import { useState } from "react";
import "./EarnalismBrandLockup.css";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const CANONICAL_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-brand-lockup.png`;
const BUNDLED_FALLBACK = `${PUBLIC_URL}/assets/brand/earnalism-logo-text-original.png`;

const VARIANTS = new Set([
  "desktop-header",
  "mobile-header",
  "footer",
  "auth",
  "account",
  "editorial",
]);

/** The sole visible lockup for public customer-shell surfaces. */
export default function EarnalismBrandLockup({ variant = "desktop-header", className = "" }) {
  const [source, setSource] = useState(CANONICAL_LOGO);
  const safeVariant = VARIANTS.has(variant) ? variant : "desktop-header";

  return (
    <span
      className={`earnalism-brand-lockup earnalism-brand-lockup--${safeVariant} ${className}`.trim()}
      data-testid="earnalism-brand-lockup"
      data-brand-asset="earnalism-brand-lockup.png"
    >
      <img
        src={source}
        alt="The Earnalism — Read. Reflect. Remember."
        width="2400"
        height="720"
        decoding="async"
        fetchPriority={safeVariant === "desktop-header" ? "high" : undefined}
        onError={() => {
          if (source !== BUNDLED_FALLBACK) setSource(BUNDLED_FALLBACK);
        }}
      />
    </span>
  );
}
