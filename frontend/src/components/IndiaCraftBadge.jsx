const INDIA_BRUSH_FLAG_IMAGE = `${process.env.PUBLIC_URL || ""}/assets/brand/india-brush-flag-badge.png`;

export default function IndiaCraftBadge() {
  return (
    <span
      className="india-origin-badge"
      data-testid="india-origin-badge"
      role="img"
      aria-label="Made in India - Literary Atelier"
      title="Made in India - Literary Atelier"
    >
      <span className="india-origin-badge__plate" aria-hidden="true">
        <img
          className="india-origin-badge__image"
          src={INDIA_BRUSH_FLAG_IMAGE}
          alt=""
          loading="eager"
          decoding="async"
        />
      </span>
    </span>
  );
}
