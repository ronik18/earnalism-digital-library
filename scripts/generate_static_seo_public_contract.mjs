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

function assertSafePublication({ slug, book, manifest, source, approval }) {
  const readerEnabled = book.reader_enabled !== false;
  const live = book.is_published !== false && book.publication_status === "LIVE_APPROVED";
  const canonical = manifest.slug === slug;
  // Older immutable approval records predate `verification_status`; the
  // authoritative, release-gating field is `approved_to_publish`.
  const approved = approval.approved_to_publish === true;
  if (!live || !readerEnabled || !canonical || !approved || !book.title || !book.author || !source) {
    throw new Error(`Controlled publication ${slug} cannot produce a public static-SEO record.`);
  }
}

async function loadPublication(slug) {
  const directory = path.join(root, "data", "controlled_publications", slug);
  const sourcePaths = {
    public_book: path.join(directory, "public_book.json"),
    reader_manifest: path.join(directory, "reader_manifest.json"),
    source_evidence: path.join(directory, "source_evidence.json"),
    approval_evidence: path.join(directory, "approval_evidence.json"),
  };
  const records = Object.fromEntries(await Promise.all(Object.entries(sourcePaths).map(async ([name, filePath]) => [name, await jsonAndSha(filePath)])));
  assertSafePublication({ slug, book: records.public_book.json, manifest: records.reader_manifest.json, source: records.source_evidence.json, approval: records.approval_evidence.json });
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
      source_display_name: String(records.source_evidence.json.source_name || "Verified public source"),
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
  if (slugs.length === 0) throw new Error("Controlled launch has no public live slugs.");
  const entries = await Promise.all(slugs.map(loadPublication));
  return {
    schema_version: "earnalism.static-seo-public.v2",
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
