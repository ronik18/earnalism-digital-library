import { useEffect, useRef, useState } from "react";

export default function SmartImage({
  src,
  alt,
  dataSrcset,
  dataDominantColor,
  dataType,
  className,
}) {
  const [loaded, setLoaded] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    if (!src) return;
    const img = new window.Image();
    img.src = src;
    img.onload = () => setLoaded(true);
  }, [src]);

  const canZoom = dataType !== "diagram";
  const dominantColor = dataDominantColor || "#1A1010";

  const figureBg =
    dataType === "photo"
      ? `${dominantColor}22`
      : dataType === "diagram"
      ? "#FFFFFF"
      : "transparent";

  return (
    <>
      <figure
        className={`reader-figure reader-figure--${dataType || "illustration"}`}
        style={{ background: figureBg, margin: "2.5em 0" }}
      >
        <img
          ref={imgRef}
          src={src}
          srcSet={dataSrcset || undefined}
          sizes="(max-width:640px) 100vw,(max-width:1024px) 70vw,58ch"
          alt={alt || ""}
          className={`reader-img reader-img--${dataType || "illustration"} ${className || ""}`}
          data-loading={loaded ? "false" : "true"}
          loading="lazy"
          onClick={() => { if (canZoom) setZoomed(true); }}
          style={{ cursor: canZoom ? "zoom-in" : "default" }}
          draggable="false"
        />
        {alt ? (
          <figcaption
            style={{
              fontFamily: "Inter, sans-serif",
              fontSize: 13,
              color: "#A88A8F",
              fontStyle: "italic",
              textAlign: "center",
              marginTop: 12,
            }}
          >
            {alt}
          </figcaption>
        ) : null}
      </figure>

      {zoomed && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-fade-in"
          style={{
            background: "rgba(0,0,0,0.92)",
            backdropFilter: "blur(8px)",
          }}
          onClick={() => setZoomed(false)}
        >
          <img
            src={src}
            alt={alt || ""}
            className="max-w-full max-h-full rounded-lg"
            style={{ boxShadow: "0 24px 80px rgba(0,0,0,0.6)" }}
          />
          <button
            type="button"
            className="absolute top-4 right-4"
            style={{
              fontFamily: "Inter, sans-serif",
              fontSize: 13,
              color: "rgba(255,255,255,0.7)",
            }}
            onClick={(e) => { e.stopPropagation(); setZoomed(false); }}
          >
            ✕ Close
          </button>
        </div>
      )}
    </>
  );
}
