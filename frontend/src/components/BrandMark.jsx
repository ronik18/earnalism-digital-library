import { useSettings } from "../context/SettingsContext";

const ALT = "Earnalism logo";
const PUBLIC_URL = process.env.PUBLIC_URL || "";
const DEFAULT_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-brand-lockup.png`;
const RESPONSIVE_LOGO_BASE = `${PUBLIC_URL}/assets/performance/earnalism-brand-lockup`;
const RESPONSIVE_LOGO_SIZES = "(min-width: 1024px) 280px, (min-width: 640px) 240px, 160px";

/**
 * BrandMark — renders the brand identity. If admin has uploaded a logo URL via
 * Settings → Brand, it uses that image. Otherwise it uses the bundled mark.
 * The image is capped so an oversized upload cannot blow out the layout.
 *
 * Props:
 *   variant: "header" | "footer" | "auth" | "compact"
 *           — picks the lockup scale and alignment.
 *   className: extra wrapper classes.
 */
export default function BrandMark({ variant = "header", className = "" }) {
  const { brand } = useSettings();
  const logo = brand?.logo_url?.trim() || DEFAULT_LOGO;
  const bundledLogo = logo === DEFAULT_LOGO;
  const priority = variant === "header" || variant === "footer";

  const wrapperClass = {
    header: "inline-flex items-center gap-2.5 sm:gap-3 text-left",
    footer: "inline-flex items-center gap-3 sm:gap-4 text-left",
    auth: "inline-flex flex-col items-center gap-3 text-center",
    compact: "inline-flex items-center gap-2 text-left",
  }[variant] || "inline-flex items-center gap-3 text-left";

  const imageClass = {
    header: "max-h-12 max-w-[20rem] sm:max-w-[25rem]",
    footer: "max-h-16 max-w-[24rem]",
    auth: "max-h-20 max-w-[24rem]",
    compact: "max-h-10 max-w-[16rem]",
  }[variant] || "max-h-14 max-w-[22rem]";
  return (
    <span className={`${wrapperClass} min-w-0 ${className}`} data-testid="brand-mark">
      <picture>
        {bundledLogo ? (
          <>
            <source
              type="image/avif"
              srcSet={`${RESPONSIVE_LOGO_BASE}-320.avif 320w, ${RESPONSIVE_LOGO_BASE}-640.avif 640w`}
              sizes={RESPONSIVE_LOGO_SIZES}
            />
            <source
              type="image/webp"
              srcSet={`${RESPONSIVE_LOGO_BASE}-320.webp 320w, ${RESPONSIVE_LOGO_BASE}-640.webp 640w`}
              sizes={RESPONSIVE_LOGO_SIZES}
            />
          </>
        ) : null}
        <img
          src={logo}
          alt={ALT}
          width="640"
          height="192"
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : undefined}
          decoding="async"
          className={`${imageClass} w-auto object-contain`}
        />
      </picture>
    </span>
  );
}
