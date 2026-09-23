import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildDir = path.join(frontendDir, "build");
const contractDir = path.join(frontendDir, "static-seo");
const accessCopy = "The three India pilot editions are free to read in full after sign-in; the first 3 pages are public. Audiobooks and paid checkout are unavailable.";
const heldCopy = "Reader and listening editions are temporarily unavailable while title-specific release decisions are completed.";
const forbidden = ["Chapter 1 free", "First chapter free", "Chapter 1 is on us", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample", "Listen free"];
const paidContinuation = ["Listening requires an active Reading Pass", "View Reading Passes", "Reading time is used only while you read"];
const indiaPilotSlugs = ["a-ghost-story", "radharani", "the-tell-tale-heart"];

const json = async (file) => JSON.parse(await readFile(file, "utf8"));
const snapshotFile = (route) => route === "/" ? path.join(buildDir, "index.html") : path.join(buildDir, route.replace(/^\/+/, ""), "index.html");
const isSha = (value) => /^[a-f0-9]{64}$/i.test(String(value || ""));

const fail = (message, state) => {
  state.failures += 1;
  console.error(message);
};

function requiredRoutes(publication, editorial) {
  const publicRoutes = ["/", "/library", "/pricing", "/about", "/contact", "/privacy", "/terms", "/copyright", "/micro-story", "/journal"];
  const journalRoutes = editorial.articles.map((article) => "/journal/" + article.slug);
  const books = publication.publications.flatMap((book) => ["/book/" + book.slug, "/reader/" + book.slug, "/listener/" + book.slug]);
  return [...publicRoutes, ...journalRoutes, ...books, "/login", "/signup", "/account", "/my-library"];
}

async function main() {
  const state = { inspected: 0, assertions: 0, failures: 0 };
  const publication = await json(path.join(contractDir, "controlled-publication-public.json"));
  const editorial = await json(path.join(contractDir, "editorial-public.json"));
  const manifest = await json(path.join(buildDir, "static-seo-snapshot-manifest.json"));
  const expected = requiredRoutes(publication, editorial);

  const releaseHeld = publication.public_release_held === true;
  if (publication.schema_version !== "earnalism.static-seo-public.v2" || !Object.values(publication.generated_from || {}).every(isSha) || (releaseHeld ? publication.publications.length !== 0 : publication.publications.length === 0)) fail("Publication contract provenance is invalid", state);
  if (!releaseHeld && (publication.publications.length !== indiaPilotSlugs.length || publication.publications.some((book) => !indiaPilotSlugs.includes(book.slug) || book.audio_availability_state !== "disabled"))) fail("Publication contract exceeds the free India pilot", state);
  if (editorial.schema_version !== "earnalism.static-seo-editorial.v1" || !isSha(editorial.generated_from && editorial.generated_from["https://api.theearnalism.com/api/blog"])) fail("Editorial contract provenance is invalid", state);
  if (manifest.schema_version !== "earnalism.static-seo-snapshots.v2") fail("Snapshot manifest version is invalid", state);
  if (new Set(manifest.routes.map((item) => item.route)).size !== manifest.routes.length) fail("Snapshot manifest has duplicate routes", state);

  for (const route of expected) {
    const manifestEntry = manifest.routes.find((item) => item.route === route);
    if (!manifestEntry) {
      fail("Missing manifest route: " + route, state);
      continue;
    }
    let html;
    try {
      html = await readFile(snapshotFile(route), "utf8");
    } catch (error) {
      fail("Missing snapshot for " + route + ": " + (error.code || error.message), state);
      continue;
    }
    state.inspected += 1;
    const normalized = html.toLowerCase();
    const assertions = [
      ['data-static-seo-snapshot="true"', "missing route-specific static shell"],
      ["<title>", "missing title"],
      ['name="description"', "missing description"],
      ['rel="canonical"', "missing canonical URL"],
      ['property="og:title"', "missing Open Graph title"],
      ['name="twitter:title"', "missing Twitter title"],
      ["earnalism-brand-lockup.png", "missing canonical logo"],
    ];
    for (const item of assertions) {
      state.assertions += 1;
      if (!normalized.includes(item[0].toLowerCase())) fail(route + " " + item[1], state);
    }
    for (const phrase of forbidden) {
      state.assertions += 1;
      if (normalized.includes(phrase.toLowerCase())) fail(route + " contains forbidden copy: " + phrase, state);
    }
    for (const phrase of paidContinuation) {
      state.assertions += 1;
      if (!releaseHeld && normalized.includes(phrase.toLowerCase())) fail(route + " contains stale paid-access copy: " + phrase, state);
    }
    if (route === "/" || route === "/library" || route.startsWith("/book/") || route.startsWith("/reader/") || route.startsWith("/listener/")) {
      state.assertions += 1;
      const requiredAccessCopy = releaseHeld && ["/", "/library"].includes(route) ? heldCopy : accessCopy;
      if (!normalized.includes(requiredAccessCopy.toLowerCase())) fail(route + " is missing the applicable access contract", state);
    }
    if (route === "/pricing") {
      state.assertions += 1;
      if (!normalized.includes((releaseHeld ? heldCopy : "Reading Passes and paid checkout are unavailable in this launch").toLowerCase())) fail(route + " must describe disabled checkout", state);
      if (!normalized.includes('name="robots" content="noindex,follow"')) fail(route + " must be noindex", state);
    }
    if (route.startsWith("/book/")) {
      state.assertions += 2;
      if (!normalized.includes('"isaccessibleforfree":true')) fail(route + " must mark the released book free", state);
      if (!normalized.includes("read the complete edition free")) fail(route + " must offer full free reading", state);
    }
    if (route === "/journal" || route.startsWith("/journal/") || route === "/contact") {
      state.assertions += 1;
      if (normalized.includes("a library made for lingering")) fail(route + " contains the generic Home fallback", state);
    }
    if (["/login", "/signup", "/account", "/my-library"].includes(route)) {
      state.assertions += 1;
      if (!normalized.includes('name="robots" content="noindex,nofollow"')) fail(route + " must be noindex", state);
    }
    if (route === "/my-library") {
      state.assertions += 4;
      if (manifestEntry.snapshot_classification !== "AUTHENTICATED_PRIVATE") fail(route + " must be classified AUTHENTICATED_PRIVATE", state);
      if (!normalized.includes("<title>my library | the earnalism</title>")) fail(route + " must have the route-specific title", state);
      if (normalized.includes("a library made for lingering")) fail(route + " contains the generic Home fallback", state);
      const staticBody = (html.match(/<main[^>]+data-static-seo-snapshot="true"[\s\S]*?<\/main>/i) || [""])[0];
      if (/\b(?:balance|transaction|device|saved editions|@[^\s<]+)/i.test(staticBody)) fail(route + " contains account-private data", state);
    }
    if (route.startsWith("/reader/") || route.startsWith("/listener/")) {
      state.assertions += 1;
      if (!normalized.includes('name="robots" content="noindex,follow"')) fail(route + " must be noindex", state);
    }
    state.assertions += 1;
    if (/https?:\/\/[^"'\s]+\.(?:mp3|m4a|aac|wav)(?:["'\s?]|$)/i.test(html)) fail(route + " exposes a raw media URL", state);
  }
  console.log("Static SEO snapshot verifier: inspected=" + state.inspected + " expected=" + expected.length + " assertions=" + state.assertions + " failed=" + state.failures);
  if (state.failures > 0 || state.inspected !== expected.length) process.exitCode = 1;
}

main().catch((error) => {
  console.error("Static SEO snapshot verifier failed: " + (error.stack || error.message));
  process.exitCode = 1;
});
