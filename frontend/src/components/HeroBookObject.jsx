import React from "react";

export default function HeroBookObject({
  href,
  coverSrc,
  alt,
  ariaLabel,
  onClick,
  testId,
  className = "",
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
        <span className="reference-hero-book__face">
          <img
            src={coverSrc}
            alt=""
            loading="eager"
            fetchPriority="high"
            width="1024"
            height="1536"
            className="reference-hero-book__cover reference-dracula-hardcopy-img"
          />
        </span>
      </span>
      <span className="sr-only">{alt || ariaLabel}</span>
    </a>
  );
}
