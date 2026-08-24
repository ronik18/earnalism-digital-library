import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sources = {
  public_book: path.join(root, "data", "controlled_publications", "dracula", "public_book.json"),
  reader_manifest: path.join(root, "data", "controlled_publications", "dracula", "reader_manifest.json"),
  source_evidence: path.join(root, "data", "controlled_publications", "dracula", "source_evidence.json"),
  approval_evidence: path.join(root, "data", "controlled_publications", "dracula", "approval_evidence.json"),
};
const contractPath = path.join(root, "frontend", "static-seo", "controlled-publication-public.json");

async function jsonAndSha(filePath) {
  const bytes = await readFile(filePath);
  return {
    json: JSON.parse(bytes.toString("utf8")),
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
}

function assertApprovedDracula({ book, manifest, source, approval }) {
  const approved = book.slug === "dracula"
    && book.title === "Dracula"
    && book.author === "Bram Stoker"
    && typeof book.cover_image_url === "string"
    && book.cover_image_url.startsWith("https://")
    && manifest.slug === "dracula"
    && Number(manifest.chapter_count) === 27
    && source.source_name === "Project Gutenberg"
    && approval.approved_to_publish === true
    && approval.rights_tier === "A"
    && approval.verification_status === "approved"
    && approval.qa_status === "QA_PASSED"
    && book.audiobook_enabled === false
    && book.audio_enabled === false;

  if (!approved) {
    throw new Error("Dracula authoritative artifacts cannot produce the public static-SEO contract.");
  }
}

async function expectedContract() {
  const entries = await Promise.all(Object.entries(sources).map(async ([name, filePath]) => [name, await jsonAndSha(filePath)]));
  const values = Object.fromEntries(entries);
  assertApprovedDracula({
    book: values.public_book.json,
    manifest: values.reader_manifest.json,
    source: values.source_evidence.json,
    approval: values.approval_evidence.json,
  });

  return {
    schema_version: "earnalism.static-seo-public.v1",
    generated_from: Object.fromEntries(entries.map(([name, value]) => [
      path.relative(root, sources[name]).replace(/\\/g, "/"),
      value.sha256,
    ])),
    publications: [{
      slug: "dracula",
      title: "Dracula",
      author: "Bram Stoker",
      cover_url: values.public_book.json.cover_image_url,
      chapter_count: 27,
      source_display_name: "Project Gutenberg eBook #345",
      approved_rights_display_state: "approved_tier_a",
      text_preview_limit_canonical_pages: 3,
      audio_public_preview_seconds: 0,
      audio_availability_state: "disabled",
      canonical_routes: {
        book: "/book/dracula",
        reader: "/reader/dracula",
      },
    }],
  };
}

function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

async function main() {
  const expected = stableJson(await expectedContract());
  if (process.argv.includes("--check")) {
    let actual;
    try {
      actual = await readFile(contractPath, "utf8");
    } catch (error) {
      throw new Error(`Static SEO public contract is missing: ${error.code || error.message}`);
    }
    if (actual !== expected) {
      throw new Error("Static SEO public contract is stale. Run node scripts/generate_static_seo_public_contract.mjs and commit the result.");
    }
    console.log("STATIC_SEO_PUBLIC_CONTRACT=fresh");
    return;
  }
  await writeFile(contractPath, expected, "utf8");
  console.log(`STATIC_SEO_PUBLIC_CONTRACT=written path=${path.relative(root, contractPath)}`);
}

main().catch((error) => {
  console.error(`[static-seo-contract] ${error.message}`);
  process.exitCode = 1;
});
