import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const rootDir = path.resolve(frontendDir, "..");
const buildDir = path.join(frontendDir, "build");
const publicationContractPath = path.join(frontendDir, "static-seo", "controlled-publication-public.json");
const editorialContractPath = path.join(frontendDir, "static-seo", "editorial-public.json");
const siteUrl = (process.env.REACT_APP_SITE_URL || process.env.SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const brandImage = siteUrl + "/assets/brand/earnalism-brand-lockup.png";
const accessCopy = "Read the first 3 pages free. Listening requires an active Reading Pass.";
const forbiddenCopy = ["Chapter 1 free", "First chapter free", "Chapter 1 is on us", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample", "Listen free"];
const headStart = "<!-- earnalism-static-seo:start -->";
const headEnd = "<!-- earnalism-static-seo:end -->";

const html = (value = "") => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const absolute = (route = "/") => new URL(route, siteUrl + "/").href;
const isSha = (value) => /^[a-f0-9]{64}$/i.test(String(value || ""));

async function json(file) {
  return JSON.parse(await readFile(file, "utf8"));
}

async function template() {
  try { return await readFile(path.join(buildDir, "index.html"), "utf8"); }
  catch (error) {
    if (error && error.code === "ENOENT") return readFile(path.join(frontendDir, "public", "index.html"), "utf8");
    throw error;
  }
}

async function contracts() {
  const result = await Promise.all([json(publicationContractPath), json(editorialContractPath)]);
  const publication = result[0];
  const editorial = result[1];
  const books = Array.isArray(publication.publications) ? publication.publications : [];
  const articles = Array.isArray(editorial.articles) ? editorial.articles : [];
  const validBooks = publication.schema_version === "earnalism.static-seo-public.v2"
    && books.length > 0
    && Object.values(publication.generated_from || {}).every(isSha)
    && books.every((book) => book.slug && book.title && book.author && Number(book.text_preview_limit_canonical_pages) === 3 && Number(book.audio_public_preview_seconds) === 0 && book.canonical_routes && book.canonical_routes.book === "/book/" + book.slug);
  const validEditorial = editorial.schema_version === "earnalism.static-seo-editorial.v1"
    && isSha(editorial.generated_from && editorial.generated_from["https://api.theearnalism.com/api/blog"])
    && editorial.journal && editorial.journal.canonical_route === "/journal"
    && articles.every((article) => article.slug && article.title && article.excerpt && article.author);
  if (!validBooks || !validEditorial) throw new Error("Static SEO contract is stale or invalid. Refresh the checked-in public-safe contracts before building.");
  return { books, editorial: { ...editorial, articles } };
}

function removeManagedHead(source) {
  return source
    .replace(new RegExp(headStart + "[\\s\\S]*?" + headEnd + "\\s*", "g"), "")
    .replace(/<title>[\s\S]*?<\/title>\s*/gi, "")
    .replace(/<link\s+[^>]*rel=["']canonical["'][^>]*>\s*/gi, "")
    .replace(/<script\s+[^>]*type=["']application\/ld\+json["'][^>]*>[\s\S]*?<\/script>\s*/gi, "")
    .replace(/<meta\s+[^>]*(?:name|property)=["'](?:description|robots|twitter:[^"']+|og:[^"']+)["'][^>]*>\s*/gi, "");
}

function tag(kind, name, value) {
  return value ? '<meta ' + kind + '="' + html(name) + '" content="' + html(value) + '" />' : "";
}

function schema(data) {
  return '<script type="application/ld+json">' + JSON.stringify(data).replace(/</g, "\\u003c") + "</script>";
}

function pageHead(page) {
  const canonical = absolute(page.canonicalPath || page.path);
  const image = page.image || brandImage;
  return [
    headStart,
    "<title>" + html(page.title) + "</title>",
    tag("name", "description", page.description),
    tag("name", "robots", page.robots || "index,follow"),
    '<link rel="canonical" href="' + html(canonical) + '" />',
    tag("property", "og:locale", "en_US"),
    tag("property", "og:site_name", "The Earnalism Digital Library"),
    tag("property", "og:type", page.ogType || "website"),
    tag("property", "og:title", page.title),
    tag("property", "og:description", page.description),
    tag("property", "og:url", canonical),
    tag("property", "og:image", image),
    tag("property", "og:image:alt", page.title),
    tag("name", "twitter:card", "summary_large_image"),
    tag("name", "twitter:title", page.title),
    tag("name", "twitter:description", page.description),
    tag("name", "twitter:image", image),
    tag("name", "twitter:image:alt", page.title),
    ...(page.jsonLd || []).map(schema),
    headEnd,
  ].join("\n");
}

function shell(eyebrow, title, body, links = [], facts = []) {
  const nav = links.length ? '<nav aria-label="Page links">' + links.map((link) => '<a href="' + html(link.href) + '">' + html(link.label) + "</a>").join(" · ") + "</nav>" : "";
  const list = facts.length ? "<ul>" + facts.map((fact) => "<li>" + html(fact) + "</li>").join("") + "</ul>" : "";
  return '<main class="static-seo-snapshot" data-static-seo-snapshot="true" style="font-family:Georgia,serif;max-width:820px;margin:56px auto;padding:0 22px;line-height:1.75;color:#2c1810">' +
    '<img src="' + html(brandImage) + '" width="640" height="192" alt="The Earnalism" style="display:block;width:220px;height:auto;margin:0 0 2rem">' +
    '<p style="text-transform:uppercase;letter-spacing:.18em;color:#9a7440;font-size:.72rem">' + html(eyebrow) + "</p>" +
    '<h1 style="font-size:clamp(2.4rem,6vw,4.5rem);line-height:1.05;color:#4a1c27;margin:.2em 0">' + html(title) + "</h1>" +
    '<p style="font-size:1.12rem;color:#5f5350">' + html(body) + "</p>" + list + nav + "</main>";
}

function webPage(title, description, route) {
  return { "@context": "https://schema.org", "@type": "WebPage", name: title, description, url: absolute(route), isPartOf: { "@type": "WebSite", name: "The Earnalism Digital Library", url: siteUrl } };
}

function standardPages(editorial) {
  const pages = [
    ["/", "Earnalism | Bengali and English Classics", "A calm digital reading room for timeless Bengali and English literature. " + accessCopy, "The Earnalism Digital Library", "A calmer place for timeless reading.", "/library", "Explore the Library"],
    ["/library", "Library | The Earnalism Digital Library", "Browse verified Bengali and English editions. " + accessCopy, "Library", "Bengali and English classics.", "/pricing", "View Reading Passes"],
    ["/pricing", "Reading Passes | The Earnalism", accessCopy + " Reading time is used only while you read.", "Reading Passes", "Choose time for deeper reading.", "/library", "Explore the Library"],
    ["/about", "About Earnalism | The Earnalism Digital Library", "Earnalism is a digital library for Bengali and English classics, designed for thoughtful reading and release-aware listening.", "About Earnalism", "A library made for attention.", "/library", "Explore the Library"],
    ["/contact", "Contact | The Earnalism", "Contact The Earnalism for reader support, rights and title inquiries, or institutional access.", "Library desk", "Write to The Earnalism.", "mailto:sales@reoenterprise.org", "Email the library desk"],
    ["/micro-story", "A Quiet Reading Invitation | The Earnalism", "Find a reader-ready Earnalism edition and begin with the canonical preview. " + accessCopy, "A quiet way into the library", "Begin with a story.", "/library?source=reading_invitation", "Explore the Library"],
  ].map((row) => ({
    path: row[0], title: row[1], description: row[2], jsonLd: [webPage(row[1], row[2], row[0])],
    staticBody: shell(row[3], row[4], row[2], [{ href: row[5], label: row[6] }]),
  }));
  const journal = {
    path: "/journal", title: editorial.journal.title, description: editorial.journal.description,
    jsonLd: [webPage(editorial.journal.title, editorial.journal.description, "/journal")],
    staticBody: shell("The Earnalism Journal", "Notes from the reading room.", editorial.journal.description, editorial.articles.map((article) => ({ href: "/journal/" + article.slug, label: article.title }))),
  };
  const articles = editorial.articles.map((article) => ({
    path: "/journal/" + article.slug, title: article.title + " | The Earnalism Journal", description: article.excerpt, image: article.cover_url || brandImage, ogType: "article",
    jsonLd: [
      webPage(article.title, article.excerpt, "/journal/" + article.slug),
      { "@context": "https://schema.org", "@type": "Article", headline: article.title, description: article.excerpt, datePublished: article.published_at, articleSection: article.category, author: { "@type": "Organization", name: article.author }, publisher: { "@type": "Organization", name: "The Earnalism", logo: { "@type": "ImageObject", url: brandImage } }, mainEntityOfPage: absolute("/journal/" + article.slug) },
    ],
    staticBody: shell(article.category, article.title, article.excerpt, [{ href: "/journal", label: "Back to Journal" }], ["By " + article.author]),
  }));
  const privatePages = [
    ["/login", "Sign in | The Earnalism", "Sign in to return to your library."],
    ["/signup", "Create an account | The Earnalism", "Create an account for your Earnalism library."],
    ["/account", "Your account | The Earnalism", "Your Earnalism account is private."],
  ].map((row) => ({ path: row[0], title: row[1], description: row[2], robots: "noindex,nofollow", staticBody: shell("The Earnalism", row[1], row[2], [{ href: "/library", label: "Explore the Library" }]) }));
  privatePages.push({
    path: "/my-library",
    title: "My Library | The Earnalism",
    description: "Your Earnalism library is private.",
    robots: "noindex,nofollow",
    snapshot_classification: "AUTHENTICATED_PRIVATE",
    staticBody: shell("The Earnalism", "My Library", "Your Earnalism library is private.", [{ href: "/library", label: "Explore the Library" }]),
  });
  return [...pages, journal, ...articles, ...privatePages];
}

function publicationPages(books) {
  return books.flatMap((book) => {
    const bookRoute = "/book/" + book.slug;
    const readerRoute = "/reader/" + book.slug;
    const listenerRoute = "/listener/" + book.slug;
    const bookDescription = book.title + " by " + book.author + " is available as a reader-ready edition on The Earnalism. " + accessCopy;
    const listening = book.audio_availability_state === "approved"
      ? "Listening to " + book.title + " requires an active Reading Pass from the first second."
      : "Listening is not available for " + book.title + " in the current release.";
    return [
      { path: bookRoute, title: book.title + " by " + book.author + " | The Earnalism", description: bookDescription, image: book.cover_url || brandImage, ogType: "book", jsonLd: [webPage(book.title, bookDescription, bookRoute), { "@context": "https://schema.org", "@type": "Book", name: book.title, author: { "@type": "Person", name: book.author }, url: absolute(bookRoute), image: book.cover_url || brandImage, isAccessibleForFree: false }], staticBody: shell("Reader-ready edition", book.title + " by " + book.author, bookDescription, [{ href: readerRoute, label: "Read the first 3 pages free" }, { href: "/pricing", label: "View Reading Passes" }], [accessCopy]) },
      { path: readerRoute, title: "Read " + book.title + " | The Earnalism Reader", description: accessCopy + " This reader route is noindex.", canonicalPath: bookRoute, robots: "noindex,follow", staticBody: shell("Reader", "Read " + book.title + ".", accessCopy, [{ href: bookRoute, label: "Book details" }]) },
      { path: listenerRoute, title: "Listen to " + book.title + " | The Earnalism", description: listening, canonicalPath: bookRoute, robots: "noindex,follow", staticBody: shell("Listening", book.title, listening, [{ href: bookRoute, label: "Book details" }], ["Public audio preview: 0 seconds.", accessCopy]) },
    ];
  });
}

function render(source, page) {
  const head = removeManagedHead(source).replace("</head>", pageHead(page) + "\n</head>");
  return head.replace(/<noscript>[\s\S]*?<\/noscript>/i, "<noscript>" + page.staticBody + "</noscript>").replace(/<div id="root"><\/div>/i, '<div id="root">' + page.staticBody + "</div>");
}

async function main() {
  const source = await template();
  const safe = await contracts();
  const pages = [...standardPages(safe.editorial), ...publicationPages(safe.books)];
  const paths = new Set();
  for (const page of pages) {
    if (paths.has(page.path)) throw new Error("Duplicate static SEO route: " + page.path);
    paths.add(page.path);
    const target = page.path === "/" ? path.join(buildDir, "index.html") : path.join(buildDir, page.path.replace(/^\/+/, ""), "index.html");
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, render(source, page), "utf8");
  }
  const manifest = { schema_version: "earnalism.static-seo-snapshots.v2", source_contracts: { publication: path.relative(rootDir, publicationContractPath).replace(/\\/g, "/"), editorial: path.relative(rootDir, editorialContractPath).replace(/\\/g, "/") }, forbidden_copy: forbiddenCopy, routes: pages.map((page) => ({ route: page.path, robots: page.robots || "index,follow", snapshot_classification: page.snapshot_classification || "PUBLIC_INDEXABLE" })) };
  await writeFile(path.join(buildDir, "static-seo-snapshot-manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
  console.log("[static-seo] Wrote " + pages.length + " static snapshots and a deterministic route manifest.");
}

main().catch((error) => { console.error("[static-seo] " + (error.stack || error.message)); process.exitCode = 1; });
