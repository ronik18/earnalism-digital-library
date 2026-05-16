import { useEffect, useMemo, useRef } from "react";
import SecureReader from "../components/SecureReader";
import useSEO from "../hooks/useSEO";

function CanvasPage({ page, text, watermark }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const ratio = window.devicePixelRatio || 1;
    const width = 720;
    const height = 960;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = "100%";
    canvas.style.height = "auto";
    ctx.scale(ratio, ratio);

    ctx.fillStyle = "#FDFCF8";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#E5DCD3";
    ctx.strokeRect(18, 18, width - 36, height - 36);

    ctx.fillStyle = "rgba(107, 16, 32, 0.055)";
    ctx.font = "28px Georgia";
    ctx.translate(width / 2, height / 2);
    ctx.rotate(-Math.PI / 7);
    for (let y = -360; y <= 360; y += 130) {
      ctx.fillText(watermark, -300, y);
    }
    ctx.rotate(Math.PI / 7);
    ctx.translate(-width / 2, -height / 2);

    ctx.fillStyle = "#4A1C27";
    ctx.font = "34px Georgia";
    ctx.fillText(`Sample Ebook Page ${page}`, 72, 120);

    ctx.fillStyle = "#2C2C2C";
    ctx.font = "22px Georgia";
    const words = text.split(" ");
    let line = "";
    let y = 190;
    words.forEach((word) => {
      const next = `${line}${word} `;
      if (ctx.measureText(next).width > 560) {
        ctx.fillText(line, 72, y);
        line = `${word} `;
        y += 42;
      } else {
        line = next;
      }
    });
    if (line) ctx.fillText(line, 72, y);

    ctx.fillStyle = "rgba(74, 28, 39, 0.62)";
    ctx.font = "14px Inter, sans-serif";
    ctx.fillText("Licensed Digital Edition · Redistribution prohibited", 72, 890);
  }, [page, text, watermark]);

  return (
    <article className="secure-reader-test-page" aria-label={`Sample ebook page ${page}`}>
      <canvas ref={canvasRef} />
      <p className="sr-only">{text}</p>
    </article>
  );
}

export default function SecureReaderHarness() {
  useSEO({
    title: "Secure Reader Harness — Earnalism",
    description: "Internal secure reader test harness with 10 sample ebook pages.",
  });

  const pages = useMemo(() => Array.from({ length: 10 }, (_, index) => ({
    page: index + 1,
    text: "This is a legally hosted sample ebook page used to validate protected rendering, subtle watermarking, disabled download interactions, and accessibility-preserving reading behavior.",
  })), []);

  return (
    <div className="secure-reader-harness">
      <div className="secure-reader-harness__intro">
        <p className="italic-eyebrow">Internal test harness</p>
        <h1>Secure Reader simulation</h1>
        <p>Ten canvas-rendered sample pages with watermarking, blocked copy/save interactions, and security event logging.</p>
      </div>
      <SecureReader
        sessionId={`harness-${Date.now()}`}
        userName="Demo Reader"
        userEmail="demo@theearnalism.com"
        bookSlug="secure-reader-harness"
        chapterId="sample-10-pages"
        title="Secure Reader Harness"
      >
        <div className="secure-reader-test-book">
          {pages.map((item) => (
            <CanvasPage
              key={item.page}
              page={item.page}
              text={item.text}
              watermark="harness · licensed · demo"
            />
          ))}
        </div>
      </SecureReader>
    </div>
  );
}
