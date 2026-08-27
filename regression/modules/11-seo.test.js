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
const PENDING_READER_APPROVAL_SLUGS = new Set(["picture-of-dorian-gray"]);
const CLAIMABLE_LIVE_SLUGS = [
  "alices-adventures-in-wonderland",
  "bn-027",
  "lokrahasya",
  "mrinalini",
  "nishkriti",
  "the-wonderful-wizard-of-oz",
  "bn-059",
  "bn-066",
  "the-art-of-money-getting",
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
  const staticSeoPublicContract = read("frontend/static-seo/controlled-publication-public.json");

  test("/book/dracula has crawler-visible Dracula-specific metadata", () => {
    expect(bookHtml).toContain("earnalism-static-seo:start");
    expect(titleText(bookHtml)).toBe("Dracula by Bram Stoker | The Earnalism");
    expect(metaContent(bookHtml, "name", "description")).toContain("Dracula by Bram Stoker is available as a reader-ready edition");
    expect(canonicalHref(bookHtml)).toBe(`${SITE_URL}/book/dracula`);
    expect(metaContent(bookHtml, "property", "og:type")).toBe("book");
    expect(metaContent(bookHtml, "property", "og:title")).toBe("Dracula by Bram Stoker | The Earnalism");
    expect(metaContent(bookHtml, "property", "og:url")).toBe(`${SITE_URL}/book/dracula`);
    const draculaOgImage = metaContent(bookHtml, "property", "og:image");
    const draculaTwitterImage = metaContent(bookHtml, "name", "twitter:image");
    expect(draculaOgImage).toMatch(/https:\/\/(?:res\.cloudinary\.com|theearnalism\.com)\/.+/);
    expect(draculaOgImage).toMatch(/dracula|cover_|assets\/books\/dracula|earnalism-logo/i);
    expect(draculaTwitterImage).toMatch(/https:\/\/(?:res\.cloudinary\.com|theearnalism\.com)\/.+/);
    expect(draculaTwitterImage).toMatch(/cover_|assets\/books\/|earnalism-logo/i);
    expect(metaContent(bookHtml, "name", "twitter:card")).toBe("summary_large_image");
    expect(metaContent(bookHtml, "name", "twitter:title")).toBe("Dracula by Bram Stoker | The Earnalism");
    expect(metaContent(bookHtml, "name", "twitter:image")).toMatch(/https:\/\/(?:res\.cloudinary\.com|theearnalism\.com)\/.+/);
    expect(jsonLdTypes(bookHtml)).toEqual(expect.arrayContaining(["Book", "WebPage"]));
  });

  test("Book JSON-LD is rights-safe and avoids unsupported claims", () => {
    const bookSchema = jsonLdObjects(bookHtml).find((payload) => payload["@type"] === "Book");
    expect(bookSchema).toBeTruthy();
    expect(bookSchema.name).toBe("Dracula");
    expect(bookSchema.author).toEqual({ "@type": "Person", name: "Bram Stoker" });
    expect(bookSchema.url).toBe(`${SITE_URL}/book/dracula`);
    expect(bookSchema.isAccessibleForFree).toBe(false);
    expect(bookHtml).toContain('href="/reader/dracula">Read the first 3 pages free');
    expect(JSON.stringify(bookSchema).toLowerCase()).not.toMatch(/aggregaterating|\breview\b|audioobject|audiobook|listen now/);
    expect(JSON.stringify(bookSchema)).not.toContain("source_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("content_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("provenance_hash");
    expect(JSON.stringify(bookSchema)).not.toContain("https://www.gutenberg.org/ebooks/345");
  });

  test("/reader/dracula is noindex and canonicalized to the public Dracula page", () => {
    expect(titleText(readerHtml)).toBe("Read Dracula | The Earnalism Reader");
    expect(metaContent(readerHtml, "name", "robots").replace(/\s/g, "")).toBe("noindex,follow");
    expect(canonicalHref(readerHtml)).toBe(`${SITE_URL}/book/dracula`);
    expect(metaContent(readerHtml, "property", "og:url")).toBe(`${SITE_URL}/book/dracula`);
    expect(jsonLdTypes(readerHtml)).toEqual([]);
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

  test("homepage, library, and pricing snapshots preserve the canonical preview and release-truth contract", () => {
    expect(homeHtml).toContain("A calm digital reading room for timeless Bengali and English literature.");
    expect(homeHtml).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
    expect(homeHtml).not.toMatch(/QA_PASSED|APPROVED/);
    expect(libraryHtml).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
    expect(pricingHtml).toContain("Read the first 3 pages free. Listening requires an active Reading Pass.");
    expect(pricingHtml).toContain("Reading Pass");
    for (const html of [homeHtml, libraryHtml, pricingHtml]) {
      expect(html).not.toMatch(/Chapter 1 is free|Read Chapter 1|Start with Chapter 1|The First Chapter|7-day/i);
    }
  });

  test("sitemap and robots preserve the controlled SEO surface", () => {
    expect(sitemap).toContain(`${SITE_URL}/book/dracula`);
    expect(sitemap).toContain(`${SITE_URL}/library`);
    expect(sitemap).toContain(`${SITE_URL}/pricing`);
    expect(sitemap).not.toContain(`${SITE_URL}/reader/dracula`);
    for (const slug of BATCH_1_READER_ONLY_SLUGS) {
      if (PENDING_READER_APPROVAL_SLUGS.has(slug)) {
        expect(sitemap).not.toContain(`${SITE_URL}/book/${slug}`);
        continue;
      }
      expect(sitemap).toContain(`${SITE_URL}/book/${slug}`);
      expect(sitemap).not.toContain(`${SITE_URL}/reader/${slug}`);
    }
    for (const slug of CLAIMABLE_LIVE_SLUGS) {
      expect(sitemap).toContain(`${SITE_URL}/book/${slug}`);
      expect(sitemap).not.toContain(`${SITE_URL}/reader/${slug}`);
    }
    expect(sitemap).not.toMatch(/kshudhita|\/reader\/|\/shop|\/product\/|\/blog\/|\/post\/|\/category\/|\/tag\//i);
    expect(robots).toContain("Allow: /reader/dracula");
    for (const slug of BATCH_1_READER_ONLY_SLUGS) {
      if (PENDING_READER_APPROVAL_SLUGS.has(slug)) {
        expect(robots).not.toContain(`Allow: /reader/${slug}`);
        continue;
      }
      expect(robots).toContain(`Allow: /reader/${slug}`);
    }
    for (const slug of CLAIMABLE_LIVE_SLUGS) {
      expect(robots).toContain(`Allow: /reader/${slug}`);
    }
    expect(robots).toContain("Disallow: /reader/");
    expect(robots).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
    expect(robots).not.toContain("Disallow: /shop");
    expect(robots).not.toContain("Disallow: /product/");
  });

  test("static snapshot generator documents approved route coverage and legacy safety", () => {
    expect(staticSnapshotGenerator).toContain('const bookRoute = "/book/" + book.slug');
    expect(staticSnapshotGenerator).toContain('const readerRoute = "/reader/" + book.slug');
    expect(staticSnapshotGenerator).toContain('robots: "noindex,follow"');
    expect(staticSnapshotGenerator).toContain("Static SEO contract is stale or invalid");
    expect(staticSnapshotGenerator).not.toContain("AudioObject");
    expect(staticSnapshotGenerator).not.toContain("sameAs: source.source_url");
  });

  test("the frontend-local public SEO contract is fresh, data-driven, and contains no protected publication data", () => {
    expect(() => execFileSync(process.execPath, ["scripts/generate_static_seo_public_contract.mjs", "--check"], {
      cwd: ROOT,
      stdio: "pipe",
    })).not.toThrow();
    const contract = JSON.parse(staticSeoPublicContract);
    expect(contract.schema_version).toBe("earnalism.static-seo-public.v2");
    expect(contract.publications.length).toBeGreaterThan(1);
    expect(contract.publications.find((publication) => publication.slug === "dracula")).toMatchObject({
      slug: "dracula",
      text_preview_limit_canonical_pages: 3,
      audio_public_preview_seconds: 0,
      audio_availability_state: "disabled",
    });
    for (const publication of contract.publications) {
      expect(publication).toMatchObject({
        text_preview_limit_canonical_pages: 3,
        audio_public_preview_seconds: 0,
      });
    }
    expect(staticSeoPublicContract).not.toMatch(/source_url|source_hash|content_hash|provenance_hash|audio_url|storage|credential/i);
  });
});
