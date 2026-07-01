const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "../..");
const SITE_URL = "https://theearnalism.com";
const STATIC_SNAPSHOT_ROUTES = ["/", "/book/dracula", "/library", "/pricing", "/reader/dracula"];
const BATCH_1_READER_ONLY_SLUGS = [
  "frankenstein",
  "jekyll-and-hyde",
  "carmilla",
  "hound-of-the-baskervilles",
  "picture-of-dorian-gray",
  "woman-in-white",
  "hungry-stones",
  "devdas",
  "pather-panchali",
  "eyesore-chokher-bali",
];

function snapshotPath(route) {
  return route === "/"
    ? "frontend/build/index.html"
    : `frontend/build/${route.replace(/^\/+/, "")}/index.html`;
}

function ensureStaticSeoSnapshots() {
  const missing = STATIC_SNAPSHOT_ROUTES
    .map(snapshotPath)
    .filter((relativePath) => !fs.existsSync(path.join(ROOT, relativePath)));

  if (missing.length === 0) return;

  execFileSync(process.execPath, ["frontend/scripts/generate-static-seo-snapshots.mjs"], {
    cwd: ROOT,
    stdio: "inherit",
  });
}

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function readSnapshot(route) {
  ensureStaticSeoSnapshots();
  return read(snapshotPath(route));
}

function metaContent(html, attr, value) {
  const tag = html.match(new RegExp(`<meta\\s+[^>]*${attr}=["']${value}["'][^>]*>`, "i"));
  if (!tag) return "";
  const content = tag[0].match(/content=["']([^"']*)["']/i);
  return content ? content[1] : "";
}

function canonicalHref(html) {
  const tag = html.match(/<link\s+[^>]*rel=["']canonical["'][^>]*>/i);
  if (!tag) return "";
  const href = tag[0].match(/href=["']([^"']*)["']/i);
  return href ? href[1] : "";
}

function titleText(html) {
  const title = html.match(/<title>\s*([\s\S]*?)\s*<\/title>/i);
  return title ? title[1].replace(/\s+/g, " ").trim() : "";
}

function jsonLdObjects(html) {
  const blocks = [];
  for (const match of html.matchAll(/<script\s+[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)) {
    blocks.push(JSON.parse(match[1]));
  }
  return blocks;
}

function jsonLdTypes(html) {
  return jsonLdObjects(html).flatMap((payload) => {
    const items = Array.isArray(payload) ? payload : [payload];
    return items.flatMap((item) => Array.isArray(item["@type"]) ? item["@type"] : [item["@type"]]).filter(Boolean);
  });
}

function audioLikeFiles(relativeRoot) {
  const absoluteRoot = path.join(ROOT, relativeRoot);
  if (!fs.existsSync(absoluteRoot)) return [];
  const results = [];
  const audioExtensions = new Set([".aac", ".m4a", ".mp3", ".ogg", ".wav"]);
  const sidecars = ["_chapters.json", "_highlight.vtt", "_meta.json", "_timestamps.json"];

  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        walk(target);
        continue;
      }
      const relative = path.relative(absoluteRoot, target).replace(/\\/g, "/");
      const lower = relative.toLowerCase();
      const isAudioFile = audioExtensions.has(path.extname(lower));
      const isAudioSidecar = lower.split("/").includes("audio") && sidecars.some((suffix) => lower.endsWith(suffix));
      if (isAudioFile || isAudioSidecar) {
        results.push(`${relativeRoot}/${relative}`);
      }
    }
  }

  walk(absoluteRoot);
  return results.sort();
}

function withoutNegatedAudioSafetyCopy(value) {
  return String(value || "")
    .replace(/No unapproved title offers Start Reading, Read Preview, or Listen Now\./gi, "")
    .replace(/Audio is not available yet\./gi, "")
    .replace(/Audiobook experience is in private review\./gi, "")
    .replace(/Audio controls hidden\./gi, "");
}

describe("Crawler-visible Dracula SEO snapshots", () => {
  const homeHtml = readSnapshot("/");
  const bookHtml = readSnapshot("/book/dracula");
  const libraryHtml = readSnapshot("/library");
  const pricingHtml = readSnapshot("/pricing");
  const readerHtml = readSnapshot("/reader/dracula");
  const sitemap = read("frontend/public/sitemap.xml");
  const robots = read("frontend/public/robots.txt");
  const staticSnapshotGenerator = read("frontend/scripts/generate-static-seo-snapshots.mjs");

  test("/book/dracula has crawler-visible Dracula-specific metadata", () => {
    expect(bookHtml).toContain("earnalism-static-seo:start");
    expect(titleText(bookHtml)).toBe("Dracula by Bram Stoker | The Earnalism Digital Library");
    expect(metaContent(bookHtml, "name", "description")).toContain("Read Dracula by Bram Stoker");
    expect(canonicalHref(bookHtml)).toBe(`${SITE_URL}/book/dracula`);
    expect(metaContent(bookHtml, "property", "og:type")).toBe("book");
    expect(metaContent(bookHtml, "property", "og:title")).toBe("Dracula by Bram Stoker | The Earnalism");
    expect(metaContent(bookHtml, "property", "og:url")).toBe(`${SITE_URL}/book/dracula`);
    expect(metaContent(bookHtml, "property", "og:image")).toMatch(/^https:\/\/theearnalism\.com\/assets\/books\/dracula\/dracula-front-cover\.webp/);
    expect(metaContent(bookHtml, "name", "twitter:card")).toBe("summary_large_image");
    expect(metaContent(bookHtml, "name", "twitter:title")).toBe("Dracula by Bram Stoker | The Earnalism");
    expect(metaContent(bookHtml, "name", "twitter:image")).toMatch(/^https:\/\/theearnalism\.com\/assets\/books\/dracula\/dracula-front-cover\.webp/);
    expect(jsonLdTypes(bookHtml)).toEqual(expect.arrayContaining(["Book", "WebPage", "BreadcrumbList"]));
  });

  test("Book JSON-LD is rights-safe and avoids unsupported claims", () => {
    const bookSchema = jsonLdObjects(bookHtml).find((payload) => payload["@type"] === "Book");
    expect(bookSchema).toBeTruthy();
    expect(bookSchema.name).toBe("Dracula");
    expect(bookSchema.author).toEqual({ "@type": "Person", name: "Bram Stoker" });
    expect(bookSchema.url).toBe(`${SITE_URL}/book/dracula`);
    expect(bookSchema.isAccessibleForFree).toBe(false);
    expect(bookSchema.hasPart).toEqual([
      {
        "@type": "Chapter",
        name: "Chapter 1 preview",
        isAccessibleForFree: true,
        url: `${SITE_URL}/reader/dracula`,
      },
    ]);
    expect(JSON.stringify(bookSchema).toLowerCase()).not.toMatch(/aggregaterating|\breview\b|audioobject|audiobook|listen now/);
    expect(JSON.stringify(bookSchema)).not.toContain("source_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("content_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("provenance_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("https://www.gutenberg.org/ebooks/345");
  });

  test("/reader/dracula is noindex and canonicalized to the public Dracula page", () => {
    expect(titleText(readerHtml)).toBe("Read Dracula Chapter 1 | The Earnalism Reader");
    expect(metaContent(readerHtml, "name", "robots").replace(/\s/g, "")).toBe("noindex,follow");
    expect(canonicalHref(readerHtml)).toBe(`${SITE_URL}/book/dracula`);
    expect(metaContent(readerHtml, "property", "og:url")).toBe(`${SITE_URL}/book/dracula`);
    expect(jsonLdTypes(readerHtml)).toEqual(["WebPage"]);
    expect(readerHtml).not.toContain("AudioObject");
    expect(readerHtml).not.toMatch(/\bListen Now\b/i);
  });

  test("static snapshots do not leak paid chapter text or public audiobook metadata", () => {
    const snapshots = [homeHtml, bookHtml, libraryHtml, pricingHtml, readerHtml].join("\n");
    const positiveAudioClaimSurface = withoutNegatedAudioSafetyCopy(snapshots);
    expect(snapshots).not.toContain("I was not able to light on any map or work giving the exact locality of the Castle Dracula");
    expect(snapshots).not.toContain("When I found that I was a prisoner a sort of wild feeling came over me");
    expect(positiveAudioClaimSurface).not.toMatch(/audio_url|audiobook_assets|audioobject|audiobook available|play audiobook|listen now/i);
    expect(snapshots).not.toMatch(/source_hash|content_hash|provenance_hash|rights_metadata/i);
  });

  test("public and built static output contain no directly reachable audio-like assets", () => {
    expect(audioLikeFiles("frontend/public")).toEqual([]);
    expect(audioLikeFiles("frontend/build")).toEqual([]);
  });

  test("homepage, library, and pricing snapshots stay Dracula-first and not broad-catalog", () => {
    expect(homeHtml).toContain("Begin with Dracula.");
    expect(homeHtml).toContain("Controlled launch begins with Dracula");
    expect(homeHtml).toContain("Dracula remains the featured live approved reading release.");
    expect(libraryHtml).toContain("Live Controlled Reader Releases.");
    expect(libraryHtml).toContain("Reader-only releases do not offer checkout, payment, or listening CTAs.");
    expect(pricingHtml).toContain("Choose your reading time. Return whenever the book calls.");
    for (const html of [homeHtml, libraryHtml, pricingHtml]) {
      expect(html).not.toMatch(/Preview every book before you pay|A quieter bookstore for readers who linger|Discover thoughtful books across/i);
    }
  });

  test("sitemap and robots preserve the controlled SEO surface", () => {
    expect(sitemap).toContain(`${SITE_URL}/book/dracula`);
    expect(sitemap).toContain(`${SITE_URL}/library`);
    expect(sitemap).toContain(`${SITE_URL}/pricing`);
    expect(sitemap).not.toContain(`${SITE_URL}/reader/dracula`);
    for (const slug of BATCH_1_READER_ONLY_SLUGS) {
      expect(sitemap).toContain(`${SITE_URL}/book/${slug}`);
      expect(sitemap).not.toContain(`${SITE_URL}/reader/${slug}`);
    }
    expect(sitemap).not.toMatch(/kshudhita|bn-|\/reader\/|\/shop|\/product\/|\/blog\/|\/post\/|\/category\/|\/tag\//i);
    expect(robots).toContain("Allow: /reader/dracula");
    for (const slug of BATCH_1_READER_ONLY_SLUGS) {
      expect(robots).toContain(`Allow: /reader/${slug}`);
    }
    expect(robots).toContain("Disallow: /reader/");
    expect(robots).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
    expect(robots).not.toContain("Disallow: /shop");
    expect(robots).not.toContain("Disallow: /product/");
  });

  test("static snapshot generator documents approved route coverage and legacy safety", () => {
    expect(staticSnapshotGenerator).toContain('path: "/book/dracula"');
    expect(staticSnapshotGenerator).toContain('path: "/reader/dracula"');
    expect(staticSnapshotGenerator).toContain('robots: "noindex,follow"');
    expect(staticSnapshotGenerator).toContain("Dracula controlled-publication artifacts are not approved");
    expect(staticSnapshotGenerator).not.toContain("AudioObject");
    expect(staticSnapshotGenerator).not.toContain("sameAs: source.source_url");
  });
});
