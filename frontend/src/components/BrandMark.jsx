import { useSettings } from "../context/SettingsContext";

const ALT = "Earnalism logo";
const PUBLIC_URL = process.env.PUBLIC_URL || "";
const DEFAULT_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-brand-lockup.png`;

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
      <img
        src={logo}
        alt={ALT}
        loading={variant === "header" ? "eager" : "lazy"}
        decoding="async"
        className={`${imageClass} w-auto object-contain`}
      />
    </span>
  );
}
