import { useSettings } from "../context/SettingsContext";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const HEADER_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-logo-text.png`;

export const BRAND_HEADER_BADGE_VARIANTS = {
  exactFlag: "exact-flag",
  tricolor: "tricolor",
  none: "none",
};

function ExactFlagBadge() {
  return (
    <span
      className="brand-header-logo__badge brand-header-logo__badge--exact"
      data-testid="brand-header-logo-badge-exact"
      data-compliance-status="owner-review-required"
      aria-hidden="true"
    >
      <svg viewBox="0 0 30 20" focusable="false">
        <rect x="0" y="0" width="30" height="20" rx="1.2" fill="#FFFFFF" />
        <rect x="0" y="0" width="30" height="6.6667" rx="1.2" fill="#FF9933" />
        <rect x="0" y="13.3333" width="30" height="6.6667" rx="1.2" fill="#138808" />
        <circle cx="15" cy="10" r="2.2" fill="none" stroke="#000080" strokeWidth="0.42" />
        {Array.from({ length: 12 }).map((_, index) => (
          <path
            key={index}
            d="M15 10 L15 7.96"
            stroke="#000080"
            strokeLinecap="round"
            strokeWidth="0.22"
            transform={`rotate(${index * 30} 15 10)`}
          />
        ))}
      </svg>
    </span>
  );
}

function TricolorLiteraryBadge() {
  return (
    <span
      className="brand-header-logo__badge brand-header-logo__badge--tricolor"
      data-testid="brand-header-logo-badge-tricolor"
      aria-hidden="true"
    >
      <svg viewBox="0 0 48 48" focusable="false">
        <defs>
          <linearGradient id="tricolor-medallion" x1="8" y1="4" x2="39" y2="45" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#FF9933" />
            <stop offset="0.46" stopColor="#FFF8E8" />
            <stop offset="1" stopColor="#138808" />
          </linearGradient>
        </defs>
        <circle cx="24" cy="24" r="21" fill="url(#tricolor-medallion)" />
        <circle cx="24" cy="24" r="17.5" fill="#FFF9ED" stroke="#C69138" strokeWidth="1.2" />
        <path d="M15.5 17.5h7.1c2.2 0 4 1.8 4 4v11.2h-7.1c-2.2 0-4-1.8-4-4V17.5Z" fill="#FFF4DB" stroke="#7A321E" strokeWidth="1.2" />
        <path d="M32.5 17.5h-7.1c-2.2 0-4 1.8-4 4v11.2h7.1c2.2 0 4-1.8 4-4V17.5Z" fill="#FFF4DB" stroke="#7A321E" strokeWidth="1.2" />
        <path d="M24 20.2v12.5" stroke="#26324A" strokeWidth="1" strokeLinecap="round" />
        <circle cx="24" cy="12.4" r="2.6" fill="none" stroke="#26324A" strokeWidth="1" />
        <path d="M24 9.8v5.2M21.4 12.4h5.2" stroke="#26324A" strokeWidth="0.6" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export default function BrandHeaderLogo({
  badgeVariant = BRAND_HEADER_BADGE_VARIANTS.tricolor,
  className = "",
}) {
  const { brand } = useSettings();
  const safeBadgeVariant = Object.values(BRAND_HEADER_BADGE_VARIANTS).includes(badgeVariant)
    ? badgeVariant
    : BRAND_HEADER_BADGE_VARIANTS.tricolor;
  const customLogo = brand?.logo_url?.trim();
  const resolvedLogo = customLogo;

  if (resolvedLogo) {
    return (
      <span
        className={`brand-header-logo brand-header-logo--custom ${className}`.trim()}
        role="img"
        aria-label="Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture"
        data-testid="brand-header-logo"
        data-badge-variant={safeBadgeVariant}
        data-logo-source="admin-setting"
      >
        <img
          src={resolvedLogo}
          alt=""
          width="1400"
          height="500"
          loading="eager"
          fetchPriority="high"
          decoding="async"
          className="brand-header-logo__custom"
        />
        {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.exactFlag && <ExactFlagBadge />}
        {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.tricolor && <TricolorLiteraryBadge />}
      </span>
    );
  }

  return (
    <span
      className={`brand-header-logo brand-header-logo--wordmark ${className}`.trim()}
      role="img"
      aria-label="Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture"
      data-testid="brand-header-logo"
      data-badge-variant={safeBadgeVariant}
    >
      <img
        src={HEADER_LOGO}
        alt=""
        width="1400"
        height="500"
        loading="eager"
        fetchPriority="high"
        decoding="async"
        className="brand-header-logo__wordmark-image"
      />
      {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.exactFlag && <ExactFlagBadge />}
      {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.tricolor && <TricolorLiteraryBadge />}
    </span>
  );
}
