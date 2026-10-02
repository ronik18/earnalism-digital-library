const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "../..");
const SITE_URL = "https://theearnalism.com";
const STATIC_SEO_PUBLIC_CONTRACT = JSON.parse(fs.readFileSync(
  path.join(ROOT, "frontend/static-seo/controlled-publication-public.json"),
  "utf8",
));
const PUBLIC_RELEASE_HELD = STATIC_SEO_PUBLIC_CONTRACT.public_release_held === true;
const PUBLICATIONS = Array.isArray(STATIC_SEO_PUBLIC_CONTRACT.publications)
  ? STATIC_SEO_PUBLIC_CONTRACT.publications
  : [];
const PRIMARY_PUBLICATION = PUBLICATIONS[0] || null;
const STATIC_SNAPSHOT_ROUTES = PUBLIC_RELEASE_HELD
  ? ["/", "/library", "/pricing"]
  : [
    "/",
    "/library",
    "/pricing",
    ...PUBLICATIONS.flatMap((publication) => [
      publication.canonical_routes.book,
      publication.canonical_routes.reader,
    ]),
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

function snapshotManifest() {
  ensureStaticSeoSnapshots();
  return JSON.parse(read("frontend/build/static-seo-snapshot-manifest.json"));
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
  return [...html.matchAll(/<script\s+[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)]
    .map((match) => JSON.parse(match[1]));
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
  const audioExtensions = new Set([".aac", ".m4a", ".mp3", ".ogg", ".wav"]);
  const results = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(target);
      else if (audioExtensions.has(path.extname(entry.name.toLowerCase()))) results.push(path.relative(absoluteRoot, target));
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

describe("Crawler-visible controlled-release SEO snapshots", () => {
  const homeHtml = readSnapshot("/");
  const libraryHtml = readSnapshot("/library");
  const pricingHtml = readSnapshot("/pricing");
  const primaryBookHtml = PRIMARY_PUBLICATION ? readSnapshot(PRIMARY_PUBLICATION.canonical_routes.book) : "";
  const primaryReaderHtml = PRIMARY_PUBLICATION ? readSnapshot(PRIMARY_PUBLICATION.canonical_routes.reader) : "";
  const sitemap = read("frontend/public/sitemap.xml");
  const robots = read("frontend/public/robots.txt");
  const staticSnapshotGenerator = read("frontend/scripts/generate-static-seo-snapshots.mjs");
  const staticSeoPublicContract = read("frontend/static-seo/controlled-publication-public.json");

  test("each released title has only its own crawler-visible book metadata", () => {
    if (PUBLIC_RELEASE_HELD) {
      const routes = snapshotManifest().routes.map((entry) => entry.route);
      expect(PUBLICATIONS).toEqual([]);
      expect(routes).not.toContain("/book/");
      return;
    }
    expect(PUBLICATIONS.length).toBeGreaterThan(0);
    for (const publication of PUBLICATIONS) {
      const bookHtml = readSnapshot(publication.canonical_routes.book);
      expect(bookHtml).toContain("earnalism-static-seo:start");
      expect(titleText(bookHtml)).toBe(`${publication.title} by ${publication.author} | The Earnalism`);
      expect(metaContent(bookHtml, "name", "description")).toContain(`${publication.title} by ${publication.author}`);
      expect(canonicalHref(bookHtml)).toBe(`${SITE_URL}${publication.canonical_routes.book}`);
      expect(metaContent(bookHtml, "property", "og:type")).toBe("book");
      expect(metaContent(bookHtml, "property", "og:title")).toBe(`${publication.title} by ${publication.author} | The Earnalism`);
      expect(metaContent(bookHtml, "property", "og:url")).toBe(`${SITE_URL}${publication.canonical_routes.book}`);
      expect(metaContent(bookHtml, "property", "og:image")).toMatch(/https:\/\/(?:res\.cloudinary\.com|theearnalism\.com)\/.+/);
      expect(metaContent(bookHtml, "name", "twitter:image")).toMatch(/https:\/\/(?:res\.cloudinary\.com|theearnalism\.com)\/.+/);
      expect(metaContent(bookHtml, "name", "twitter:card")).toBe("summary_large_image");
      expect(jsonLdTypes(bookHtml)).toEqual(expect.arrayContaining(["Book", "WebPage"]));
    }
  });

  test("the primary released reader is noindex and canonicalized to its public book page", () => {
    if (PUBLIC_RELEASE_HELD) return;
    expect(titleText(primaryReaderHtml)).toBe(`Read ${PRIMARY_PUBLICATION.title} | The Earnalism Reader`);
    expect(metaContent(primaryReaderHtml, "name", "robots").replace(/\s/g, "")).toBe("noindex,follow");
    expect(canonicalHref(primaryReaderHtml)).toBe(`${SITE_URL}${PRIMARY_PUBLICATION.canonical_routes.book}`);
    expect(metaContent(primaryReaderHtml, "property", "og:url")).toBe(`${SITE_URL}${PRIMARY_PUBLICATION.canonical_routes.book}`);
    expect(jsonLdTypes(primaryReaderHtml)).toEqual([]);
    expect(primaryReaderHtml).not.toContain("AudioObject");
    expect(primaryReaderHtml).not.toMatch(/\bListen Now\b/i);
  });

  test("static snapshots do not leak protected text, internal evidence, or public audio metadata", () => {
    const snapshots = [homeHtml, libraryHtml, pricingHtml, primaryBookHtml, primaryReaderHtml].join("\n");
    expect(withoutNegatedAudioSafetyCopy(snapshots)).not.toMatch(/audio_url|audiobook_assets|audioobject|audiobook available|play audiobook|listen now/i);
    expect(snapshots).not.toMatch(/source_hash|content_hash|provenance_hash|rights_metadata/i);
  });

  test("public and built static output contain no directly reachable audio files", () => {
    expect(audioLikeFiles("frontend/public")).toEqual([]);
    expect(audioLikeFiles("frontend/build")).toEqual([]);
  });

  test("homepage, library, and pricing snapshots preserve the release-truth contract", () => {
    const releaseCopy = PUBLIC_RELEASE_HELD
      ? "Reader and listening editions are temporarily unavailable while title-specific release decisions are completed."
      : "The first 3 canonical pages are available as a free preview. A Reading Pass is required from page 4; paid checkout and audiobooks are unavailable in this launch.";
    expect(homeHtml).toContain("A calm digital reading room for timeless Bengali and English literature.");
    for (const html of [homeHtml, libraryHtml]) {
      expect(html).toContain(releaseCopy);
      expect(html).not.toMatch(/QA_PASSED|APPROVED/);
      expect(html).not.toMatch(/Chapter 1 is free|Read Chapter 1|Start with Chapter 1|The First Chapter|7-day/i);
    }
    if (!PUBLIC_RELEASE_HELD) {
      expect(pricingHtml).toContain("Reading Passes and paid checkout are unavailable in this launch.");
      expect(pricingHtml).toContain('name="robots" content="noindex,follow"');
    }
  });

  test("sitemap and robots expose only the configured controlled-release titles", () => {
    expect(sitemap).toContain(`${SITE_URL}/library`);
    expect(sitemap).toContain(`${SITE_URL}/pricing`);
    for (const publication of PUBLICATIONS) {
      expect(sitemap).toContain(`${SITE_URL}${publication.canonical_routes.book}`);
      expect(sitemap).not.toContain(`${SITE_URL}${publication.canonical_routes.reader}`);
      expect(robots).toContain(`Allow: ${publication.canonical_routes.reader}`);
    }
    expect(sitemap).not.toMatch(/\/reader\/|\/shop|\/product\/|\/blog\/|\/post\/|\/category\/|\/tag\//i);
    expect(robots).toContain("Disallow: /reader/");
    expect(robots).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
  });

  test("sitemap authority requires exact projection hashes, approved manifest and live allowlist", () => {
    const os = require("os");
    const crypto = require("crypto");
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "seo-authority-"));
    try {
      const script = path.join(temporary, "frontend/scripts/generate-seo-assets.mjs");
      fs.mkdirSync(path.dirname(script), { recursive: true });
      fs.copyFileSync(path.join(ROOT, "frontend/scripts/generate-seo-assets.mjs"), script);
      const packageDir = path.join(temporary, "data/controlled_publications/approved-story");
      fs.mkdirSync(packageDir, { recursive: true });
      const write = (relative, value) => { const destination = path.join(temporary, relative); fs.mkdirSync(path.dirname(destination), { recursive: true }); fs.writeFileSync(destination, JSON.stringify(value)); };
      const metadataPath = "data/controlled_publications/approved-story/public_book.json";
      write(metadataPath, { slug: "approved-story", publication_status: "DRAFT", is_published: false });
      const digest = crypto.createHash("sha256").update(fs.readFileSync(path.join(temporary, metadataPath))).digest("hex");
      const projection = { schema_version: "earnalism.static-seo-public.v2", generated_from: { [metadataPath]: digest }, publications: [{ slug: "approved-story" }] };
      write("frontend/static-seo/controlled-publication-public.json", projection);
      const launch = { public_reader_exposure_enabled: true, live_approved_slugs: ["approved-story"] };
      write("data/controlled_launch.json", launch);
      const manifest = { slug: "approved-story", rights: { status: "APPROVED" }, reader_release: { status: "APPROVED", exposed: true, qa_status: "QA_PASSED", blockers: [] } };
      write("data/controlled_publications/approved-story/publication_manifest.json", manifest);
      const output = path.join(temporary, "output");
      const generate = () => { execFileSync(process.execPath, [script], { env: { ...process.env, SEO_ASSETS_OUTPUT_DIR: output, REACT_APP_BACKEND_URL: "", REACT_APP_API_URL: "", SEO_API_BASE_URL: "" }, stdio: "pipe" }); return fs.readFileSync(path.join(output, "sitemap.xml"), "utf8"); };
      expect(generate()).toContain("/book/approved-story");
      write(metadataPath, { slug: "approved-story", title: "unbound mutation" });
      expect(generate()).not.toContain("/book/approved-story");
      write(metadataPath, { slug: "approved-story", publication_status: "DRAFT", is_published: false });
      write("data/controlled_publications/approved-story/publication_manifest.json", { ...manifest, reader_release: { ...manifest.reader_release, exposed: false } });
      expect(generate()).not.toContain("/book/approved-story");
      write("data/controlled_publications/approved-story/publication_manifest.json", manifest);
      write("data/controlled_launch.json", { ...launch, live_approved_slugs: [] });
      expect(generate()).not.toContain("/book/approved-story");
    } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
  });

  test("public contract builder rejects blocked manifests and altered exact artifacts", () => {
    const os = require("os");
    const crypto = require("crypto");
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "public-contract-authority-"));
    try {
      const script = path.join(temporary, "scripts/generate_static_seo_public_contract.mjs");
      fs.mkdirSync(path.dirname(script), { recursive: true });
      fs.copyFileSync(path.join(ROOT, "scripts/generate_static_seo_public_contract.mjs"), script);
      const directory = path.join(temporary, "data/controlled_publications/approved-story");
      fs.mkdirSync(directory, { recursive: true });
      fs.mkdirSync(path.join(temporary, "frontend/static-seo"), { recursive: true });
      fs.writeFileSync(path.join(temporary, "data/controlled_launch.json"), JSON.stringify({ public_reader_exposure_enabled: true, live_approved_slugs: ["approved-story"] }));
      const records = {
        public_book: { slug: "approved-story", title: "Story", author: "Author", publication_status: "DRAFT", is_published: false, audio_enabled: false, audiobook_enabled: false },
        reader_manifest: { slug: "approved-story", chapter_count: 1, chapters: [{ id: "chapter-001" }] },
        source_evidence: { source_hash: "a".repeat(64), content_hash: "b".repeat(64), source_name: "Internal edition; review evidence" },
        approval_evidence: { approved_to_publish: true },
      };
      const artifacts = {};
      for (const [name, record] of Object.entries(records)) {
        const bytes = JSON.stringify(record);
        fs.writeFileSync(path.join(directory, name + ".json"), bytes);
        artifacts[name] = crypto.createHash("sha256").update(bytes).digest("hex");
      }
      const manifest = { slug: "approved-story", artifacts, content: { source_hash: "a".repeat(64), content_hash: "b".repeat(64), chapter_count: 1 }, rights: { status: "APPROVED", tier: "A" }, reader_release: { status: "APPROVED", exposed: true, qa_status: "QA_PASSED", blockers: [] }, audio_release: { exposed: false } };
      const writeManifest = (value) => fs.writeFileSync(path.join(directory, "publication_manifest.json"), JSON.stringify(value));
      writeManifest(manifest);
      const run = () => execFileSync(process.execPath, [script], { stdio: "pipe" });
      expect(run).not.toThrow();
      const projection = JSON.parse(fs.readFileSync(path.join(temporary, "frontend/static-seo/controlled-publication-public.json"), "utf8"));
      expect(projection.publications[0].source_display_name).toBe("Rights-cleared edition");
      expect(projection.generated_from["data/controlled_publications/approved-story/publication_manifest.json"]).toMatch(/^[a-f0-9]{64}$/);
      writeManifest({ ...manifest, reader_release: { ...manifest.reader_release, blockers: ["unresolved"] } });
      expect(run).toThrow();
      writeManifest(manifest);
      fs.writeFileSync(path.join(directory, "public_book.json"), JSON.stringify({ ...records.public_book, title: "Unbound mutation" }));
      expect(run).toThrow();
    } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
  });

  test("the static SEO contract is data-driven, fresh, and contains no protected publication data", () => {
    expect(() => execFileSync(process.execPath, ["scripts/generate_static_seo_public_contract.mjs", "--check"], {
      cwd: ROOT,
      stdio: "pipe",
    })).not.toThrow();
    expect(STATIC_SEO_PUBLIC_CONTRACT.schema_version).toBe("earnalism.static-seo-public.v2");
    if (PUBLIC_RELEASE_HELD) {
      expect(PUBLICATIONS).toEqual([]);
      return;
    }
    for (const publication of PUBLICATIONS) {
      expect(publication).toMatchObject({
        text_preview_limit_canonical_pages: 3,
        audio_public_preview_seconds: 0,
        audio_availability_state: "disabled",
      });
    }
    expect(staticSnapshotGenerator).toContain('const bookRoute = "/book/" + book.slug');
    expect(staticSnapshotGenerator).toContain('const readerRoute = "/reader/" + book.slug');
    expect(staticSnapshotGenerator).not.toContain("AudioObject");
    expect(staticSeoPublicContract).not.toMatch(/source_url|source_hash|content_hash|provenance_hash|audio_url|storage|credential/i);
  });
});
