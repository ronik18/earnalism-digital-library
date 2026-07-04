const MADE_IN_INDIA_ATELIER_IMAGE = `${process.env.PUBLIC_URL || ""}/assets/brand/made-in-india-literary-atelier.png`;

export default function IndiaCraftBadge() {
  return (
    <span
      className="india-origin-badge"
      data-testid="india-origin-badge"
      aria-label="Made in India - Literary Atelier"
      title="Made in India - Literary Atelier"
    >
      <img
        className="india-origin-badge__image"
        src={MADE_IN_INDIA_ATELIER_IMAGE}
        alt=""
        aria-hidden="true"
        loading="eager"
        decoding="async"
      />
    </span>
  );
}
