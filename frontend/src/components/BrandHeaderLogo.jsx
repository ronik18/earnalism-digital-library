const PUBLIC_URL = process.env.PUBLIC_URL || "";
const HEADER_LOGO_ICON = `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-96.webp`;
const HEADER_LOGO_SRC_SET = [
  `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-96.webp 96w`,
  `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-128.webp 128w`,
].join(", ");

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
      <svg viewBox="0 0 30 20" focusable="false">
        <path d="M5.2 3.8h10.7c2.7 0 5 2.2 5 5v7.5H10.1c-2.7 0-4.9-2.2-4.9-4.9V3.8Z" fill="#FBF6EC" />
        <path d="M7.4 6.2h9.8" stroke="#FF9933" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M7.4 9.8h12.6" stroke="#B58A45" strokeWidth="1.15" strokeLinecap="round" />
        <path d="M7.4 13.4h10.8" stroke="#138808" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="22.9" cy="5.5" r="2.15" fill="none" stroke="#26324A" strokeWidth="0.75" />
        <path d="M22.9 3.95v3.1M21.35 5.5h3.1" stroke="#26324A" strokeWidth="0.45" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export default function BrandHeaderLogo({
  badgeVariant = BRAND_HEADER_BADGE_VARIANTS.tricolor,
  className = "",
}) {
  const safeBadgeVariant = Object.values(BRAND_HEADER_BADGE_VARIANTS).includes(badgeVariant)
    ? badgeVariant
    : BRAND_HEADER_BADGE_VARIANTS.tricolor;

  return (
    <span
      className={`brand-header-logo brand-header-logo--${safeBadgeVariant} ${className}`.trim()}
      role="img"
      aria-label="LEarnalism — Where Learning Becomes Earning"
      data-testid="brand-header-logo"
      data-badge-variant={safeBadgeVariant}
    >
      <img
        src={HEADER_LOGO_ICON}
        srcSet={HEADER_LOGO_SRC_SET}
        sizes="44px"
        alt=""
        aria-hidden="true"
        loading="eager"
        decoding="async"
        className="brand-header-logo__icon"
      />
      <span className="brand-header-logo__text" aria-hidden="true">
        <span className="brand-header-logo__proofread" data-testid="brand-header-logo-proofread">
          <span className="brand-header-logo__inserted-l">L</span>
          <span className="brand-header-logo__caret">^</span>
          <span className="brand-header-logo__base">Earnalism</span>
        </span>
        <span className="brand-header-logo__tagline" data-testid="brand-header-logo-tagline">
          Where Learning Becomes Earning
        </span>
      </span>
      {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.exactFlag && <ExactFlagBadge />}
      {safeBadgeVariant === BRAND_HEADER_BADGE_VARIANTS.tricolor && <TricolorLiteraryBadge />}
    </span>
  );
}
