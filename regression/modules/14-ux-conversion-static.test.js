const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

describe("UX conversion static signals", () => {
  const home = read("frontend/src/pages/Home.jsx");
  const bookDetail = read("frontend/src/pages/BookDetail.jsx");
  const library = read("frontend/src/pages/Library.jsx");
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const header = read("frontend/src/components/Header.jsx");
  const app = read("frontend/src/App.js");

  test("homepage exposes primary reading and reading-time CTAs", () => {
    expect(home).toContain('data-testid="hero-cta-read"');
    expect(home).toContain('data-testid="hero-cta-pricing"');
    expect(home).toContain("Start Reading");
    expect(home).toContain("Buy Reading Time");
  });

  test("library and book pages expose preview and reading-time purchase paths", () => {
    expect(library).toContain("Read Preview");
    expect(library).toContain("Start Reading");
    expect(bookDetail).toContain('data-testid="read-preview"');
    expect(bookDetail).toContain('data-testid="bottom-buy-reading-time"');
    expect(bookDetail).toContain("/pricing?pack=1h&source=book_detail");
  });

  test("pricing page has checkout CTA, payment trust copy, and support/refund copy", () => {
    expect(pricing).toContain("Buy reading time");
    expect(pricing).toContain("Payments are processed securely by Razorpay");
    expect(pricing).toMatch(/support or refund questions/i);
    expect(pricing).toContain('data-testid={`pack-${p.id}-buy`}');
  });

  test("mobile navigation keeps a visible library CTA", () => {
    expect(header).toContain('data-testid="mobile-cta-library"');
    expect(header).toContain("Start Reading");
  });

  test("public route tree does not expose admin controls in the public layout", () => {
    const publicRouteBlock = app.split("{/* Standalone full-screen routes")[0];
    expect(publicRouteBlock).not.toContain('path="/admin"');
    expect(publicRouteBlock).not.toContain("<Admin ");
    expect(publicRouteBlock).toContain('path="/pricing"');
    expect(publicRouteBlock).toContain('path="/library"');
  });

  test("public pages have loading, empty, and error states for reader-facing flows", () => {
    expect(bookDetail).toContain("Loading");
    expect(bookDetail).toContain('data-testid="book-load-error"');
    expect(bookDetail).toContain('data-testid="book-not-found"');
    expect(library).toContain('data-testid="library-empty"');
  });
});
