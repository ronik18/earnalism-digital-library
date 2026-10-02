import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const launchPath = path.join(root, "data", "controlled_launch.json");
const contractPath = path.join(root, "frontend", "static-seo", "controlled-publication-public.json");

async function jsonAndSha(filePath) {
  const bytes = await readFile(filePath);
  return { json: JSON.parse(bytes.toString("utf8")), sha256: createHash("sha256").update(bytes).digest("hex") };
}

function relative(filePath) {
  return path.relative(root, filePath).replace(/\\/g, "/");
}

function audioAvailability(book = {}) {
  if (book.audio_enabled !== true || book.audiobook_enabled !== true) return "disabled";
  const gate = String(book.audiobook_release_gate || book.release_gate || "").toUpperCase();
  const qa = String(book.audio_qa_status || book.qa_status || "").toUpperCase();
  return gate === "APPROVED" && ["QA_PASSED", "APPROVED", "PASS"].includes(qa) ? "approved" : "disabled";
}

function assertSafePublication({ slug, records }) {
  const book = records.public_book.json;
  const reader = records.reader_manifest.json;
  const source = records.source_evidence.json;
  const approval = records.approval_evidence.json;
  const publication = records.publication_manifest.json;
  const artifactsBound = ["public_book", "reader_manifest", "source_evidence", "approval_evidence"].every((name) => publication.artifacts?.[name] === records[name].sha256);
  const readerRelease = publication.reader_release;
  const chapterCount = Number(reader.chapter_count);
  const accepted = publication.slug === slug && book.slug === slug && reader.slug === slug
    && book.reader_enabled !== false && approval.approved_to_publish === true
    && readerRelease?.status === "APPROVED" && readerRelease.exposed === true
    && readerRelease.qa_status === "QA_PASSED" && Array.isArray(readerRelease.blockers) && readerRelease.blockers.length === 0
    && publication.rights?.status === "APPROVED" && publication.rights?.tier === "A"
    && /^[a-f0-9]{64}$/.test(source.source_hash || "") && /^[a-f0-9]{64}$/.test(source.content_hash || "")
    && publication.content?.source_hash === source.source_hash && publication.content?.content_hash === source.content_hash
    && chapterCount > 0 && Number(publication.content?.chapter_count) === chapterCount
    && Array.isArray(reader.chapters) && reader.chapters.length === chapterCount
    && book.audio_enabled !== true && book.audiobook_enabled !== true && publication.audio_release?.exposed === false
    && artifactsBound && book.title && book.author;
  if (!accepted) throw new Error(`Controlled publication ${slug} cannot produce a public static-SEO record.`);
}

function publicSourceName(source = {}) {
  const name = String(source.source_name || "Verified public source");
  // Keep established short source credits; internal reviewer commentary is
  // evidence, not customer metadata. Required licence credit remains in Reader.
  return name.length > 100 || /[;\n]|(?:review|evidence|decision)/i.test(name) ? "Rights-cleared edition" : name;
}

async function loadPublication(slug) {
  const directory = path.join(root, "data", "controlled_publications", slug);
  const sourcePaths = {
    public_book: path.join(directory, "public_book.json"),
    reader_manifest: path.join(directory, "reader_manifest.json"),
    source_evidence: path.join(directory, "source_evidence.json"),
    approval_evidence: path.join(directory, "approval_evidence.json"),
    publication_manifest: path.join(directory, "publication_manifest.json"),
  };
  const records = Object.fromEntries(await Promise.all(Object.entries(sourcePaths).map(async ([name, filePath]) => [name, await jsonAndSha(filePath)])));
  assertSafePublication({ slug, records });
  const book = records.public_book.json;
  const manifest = records.reader_manifest.json;
  return {
    generated_from: Object.fromEntries(Object.entries(sourcePaths).map(([name, filePath]) => [relative(filePath), records[name].sha256])),
    publication: {
      slug,
      title: book.title,
      author: book.author,
      cover_url: book.cover_image_url || null,
      chapter_count: Number(manifest.chapter_count || book.chapter_count || 0),
      source_display_name: publicSourceName(records.source_evidence.json),
      approved_rights_display_state: "approved_tier_a",
      text_preview_limit_canonical_pages: 3,
      audio_public_preview_seconds: 0,
      audio_availability_state: audioAvailability(book),
      canonical_routes: { book: `/book/${slug}`, reader: `/reader/${slug}`, listener: `/listener/${slug}` },
    },
  };
}

function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

async function expectedContract() {
  const launch = JSON.parse(await readFile(launchPath, "utf8"));
  const slugs = Array.from(new Set((launch.live_approved_slugs || []).map((slug) => String(slug || "").trim().toLowerCase()).filter(Boolean))).sort();
  const entries = await Promise.all((launch.public_reader_exposure_enabled === true ? slugs : []).map(loadPublication));
  return {
    schema_version: "earnalism.static-seo-public.v2",
    // Static rendering must distinguish an intentional all-title hold from a
    // malformed empty contract, so cached pages cannot advertise access.
    public_release_held: launch.public_reader_exposure_enabled !== true,
    generated_from: {
      [relative(launchPath)]: createHash("sha256").update(await readFile(launchPath)).digest("hex"),
      ...Object.assign({}, ...entries.map((entry) => entry.generated_from)),
    },
    publications: entries.map((entry) => entry.publication),
  };
}

async function main() {
  const expected = stableJson(await expectedContract());
  if (process.argv.includes("--check")) {
    let actual;
    try { actual = await readFile(contractPath, "utf8"); }
    catch (error) { throw new Error(`Static SEO public contract is missing: ${error.code || error.message}`); }
    if (actual !== expected) throw new Error("Static SEO public contract is stale. Run node scripts/generate_static_seo_public_contract.mjs and commit the result.");
    console.log("STATIC_SEO_PUBLIC_CONTRACT=fresh");
    return;
  }
  await writeFile(contractPath, expected, "utf8");
  console.log(`STATIC_SEO_PUBLIC_CONTRACT=written path=${relative(contractPath)}`);
}

main().catch((error) => { console.error(`[static-seo-contract] ${error.message}`); process.exitCode = 1; });
