import React from "react";

export default function HeroBookObject({
  href,
  coverSrc,
  coverSrcSet,
  coverSizes,
  alt,
  ariaLabel,
  onClick,
  testId,
  className = "",
  width = "500",
  height = "666",
}) {
  return (
    <a
      href={href}
      className={`reference-hero-book reference-dracula-hardcopy-shell ${className}`.trim()}
      data-testid={testId}
      data-no-white-edge="true"
      aria-label={ariaLabel}
      onClick={onClick}
    >
      <span className="reference-hero-book__volume" aria-hidden="true">
        <span className="reference-hero-book__back-board" />
        <span className="reference-hero-book__top-pages" />
        <span className="reference-hero-book__page-block" />
        <span className="reference-hero-book__bottom-pages" />
        <span className="reference-hero-book__face">
          <img
            src={coverSrc}
            srcSet={coverSrcSet}
            sizes={coverSrcSet ? coverSizes : undefined}
            alt=""
            loading="eager"
            fetchPriority="high"
            width={width}
            height={height}
            className="reference-hero-book__cover reference-dracula-hardcopy-img"
          />
        </span>
      </span>
      <span className="sr-only">{alt || ariaLabel}</span>
    </a>
  );
}
