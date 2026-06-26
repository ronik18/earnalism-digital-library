import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendDir, "..");
const buildDir = path.join(frontendDir, "build");
const indexPath = path.join(buildDir, "index.html");
const publicIndexPath = path.join(frontendDir, "public", "index.html");
const siteUrl = (process.env.REACT_APP_SITE_URL || process.env.SITE_URL || "https://theearnalism.com").replace(/\/+$/, "");
const draculaBookPath = path.join(repoRoot, "data", "controlled_publications", "dracula", "public_book.json");
const draculaManifestPath = path.join(repoRoot, "data", "controlled_publications", "dracula", "reader_manifest.json");
const draculaSourcePath = path.join(repoRoot, "data", "controlled_publications", "dracula", "source_evidence.json");
const draculaApprovalPath = path.join(repoRoot, "data", "controlled_publications", "dracula", "approval_evidence.json");

const MANAGED_HEAD_START = "<!-- earnalism-static-seo:start -->";
const MANAGED_HEAD_END = "<!-- earnalism-static-seo:end -->";
const BRAND = "The Earnalism";
const SITE_NAME = "The Earnalism";
const DRACULA_IMAGE = `${siteUrl}/assets/books/dracula/dracula-front-cover.webp`;

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function absoluteUrl(route) {
  const url = new URL(route || "/", `${siteUrl}/`);
  if (url.pathname !== "/" && url.pathname.endsWith("/")) {
    url.pathname = url.pathname.replace(/\/+$/, "");
  }
  return url.href;
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

async function readSnapshotTemplate() {
  try {
    return await readFile(indexPath, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      return readFile(publicIndexPath, "utf8");
    }
    throw error;
  }
}

async function loadDraculaArtifacts() {
  const [book, manifest, source, approval] = await Promise.all([
    readJson(draculaBookPath),
    readJson(draculaManifestPath),
    readJson(draculaSourcePath),
    readJson(draculaApprovalPath),
  ]);

  const approved = approval.approved_to_publish === true
    && approval.rights_tier === "A"
    && approval.verification_status === "approved"
    && approval.qa_status === "QA_PASSED"
    && source.source_url === "https://www.gutenberg.org/ebooks/345"
    && source.source_name === "Project Gutenberg eBook #345";

  if (!approved) {
    throw new Error("Dracula controlled-publication artifacts are not approved for static SEO snapshots.");
  }

  return { book, manifest, source, approval };
}

function stripManagedHead(html) {
  const managedNames = [
    "description",
    "robots",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
    "twitter:image:alt",
  ];
  const managedProperties = [
    "og:locale",
    "og:site_name",
    "og:type",
    "og:title",
    "og:description",
    "og:url",
    "og:image",
    "og:image:alt",
    "book:author",
    "book:release_date",
    "book:tag",
  ];

  let next = html
    .replace(new RegExp(`${MANAGED_HEAD_START}[\\s\\S]*?${MANAGED_HEAD_END}\\s*`, "g"), "")
    .replace(/<title>[\s\S]*?<\/title>\s*/gi, "")
    .replace(/<link\s+[^>]*rel=["']canonical["'][^>]*>\s*/gi, "")
    .replace(/<script\s+[^>]*type=["']application\/ld\+json["'][^>]*>[\s\S]*?<\/script>\s*/gi, "");

  for (const name of managedNames) {
    next = next.replace(new RegExp(`<meta\\s+[^>]*name=["']${escapeRegExp(name)}["'][^>]*>\\s*`, "gi"), "");
  }
  for (const property of managedProperties) {
    next = next.replace(new RegExp(`<meta\\s+[^>]*property=["']${escapeRegExp(property)}["'][^>]*>\\s*`, "gi"), "");
  }

  return next;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function metaTag(attr, name, content) {
  if (!content) return "";
  return `<meta ${attr}="${escapeHtml(name)}" content="${escapeHtml(content)}" />`;
}

function jsonLdScript(data) {
  return `<script type="application/ld+json">${JSON.stringify(data, null, 2).replace(/</g, "\\u003c")}</script>`;
}

function managedHead(page) {
  const canonical = absoluteUrl(page.canonicalPath || page.path);
  const image = page.image || DRACULA_IMAGE;
  const robots = page.robots || "index,follow";
  const jsonLd = page.jsonLd || [];
  const ogType = page.ogType || "website";

  return [
    MANAGED_HEAD_START,
    `<title>${escapeHtml(page.title)}</title>`,
    metaTag("name", "description", page.description),
    metaTag("name", "robots", robots),
    `<link rel="canonical" href="${escapeHtml(canonical)}" />`,
    metaTag("property", "og:locale", "en_US"),
    metaTag("property", "og:site_name", SITE_NAME),
    metaTag("property", "og:type", ogType),
    metaTag("property", "og:title", page.ogTitle || page.title),
    metaTag("property", "og:description", page.ogDescription || page.description),
    metaTag("property", "og:url", canonical),
    metaTag("property", "og:image", image),
    metaTag("property", "og:image:alt", page.imageAlt || page.title),
    ...(page.bookOgTags || []),
    metaTag("name", "twitter:card", "summary_large_image"),
    metaTag("name", "twitter:title", page.twitterTitle || page.ogTitle || page.title),
    metaTag("name", "twitter:description", page.twitterDescription || page.ogDescription || page.description),
    metaTag("name", "twitter:image", image),
    metaTag("name", "twitter:image:alt", page.imageAlt || page.title),
    ...jsonLd.map(jsonLdScript),
    MANAGED_HEAD_END,
  ].filter(Boolean).join("\n");
}

function withStaticFallback(html, page) {
  const headManaged = managedHead(page);
  const withHead = stripManagedHead(html).replace("</head>", `${headManaged}\n</head>`);
  const noscript = [
    "<noscript>",
    page.staticBody,
    "</noscript>",
  ].join("\n");

  return withHead
    .replace(/<noscript>[\s\S]*?<\/noscript>/i, noscript)
    .replace(/<div id="root">[\s\S]*?<\/div>/i, `<div id="root">\n${page.staticBody}\n</div>`);
}

function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "The Earnalism",
    alternateName: "Earnalism",
    url: siteUrl,
    email: "sales@reoenterprise.org",
    logo: `${siteUrl}/assets/brand/earnalism-logo.png`,
  };
}

function websiteJsonLd(description) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "The Earnalism Digital Library",
    url: siteUrl,
    description,
    inLanguage: "en",
  };
}

function webpageJsonLd({ title, description, path: pagePath }) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: title,
    description,
    url: absoluteUrl(pagePath),
    isPartOf: {
      "@type": "WebSite",
      name: "The Earnalism Digital Library",
      url: siteUrl,
    },
  };
}

function breadcrumbsJsonLd(items) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: absoluteUrl(item.path),
    })),
  };
}

function draculaBookJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Book",
    name: "Dracula",
    description: "Bram Stoker's 1897 Gothic novel, available on The Earnalism as a controlled, rights-approved core reading release.",
    url: absoluteUrl("/book/dracula"),
    image: DRACULA_IMAGE,
    author: {
      "@type": "Person",
      name: "Bram Stoker",
    },
    publisher: {
      "@type": "Organization",
      name: "The Earnalism",
      url: siteUrl,
    },
    inLanguage: "en",
    genre: "Gothic fiction",
    bookFormat: "https://schema.org/EBook",
    copyrightYear: 1897,
    isAccessibleForFree: false,
    hasPart: [
      {
        "@type": "Chapter",
        name: "Chapter 1 preview",
        isAccessibleForFree: true,
        url: absoluteUrl("/reader/dracula"),
      },
    ],
  };
}

function pageShell({ eyebrow, title, body, links = [], facts = [] }) {
  return [
    '<main class="static-seo-snapshot" data-static-seo-snapshot="true" style="font-family: Georgia, serif; max-width: 820px; margin: 56px auto; padding: 0 22px; line-height: 1.75; color: #2C1810;">',
    `<p style="text-transform: uppercase; letter-spacing: .18em; color: #9a7440; font-size: .72rem;">${escapeHtml(eyebrow)}</p>`,
    `<h1 style="font-size: clamp(2.4rem, 6vw, 4.5rem); line-height: 1.05; color: #4A1C27; margin: .2em 0;">${escapeHtml(title)}</h1>`,
    `<p style="font-size: 1.12rem; color: #5f5350;">${escapeHtml(body)}</p>`,
    facts.length
      ? `<ul>${facts.map((fact) => `<li>${escapeHtml(fact)}</li>`).join("")}</ul>`
      : "",
    links.length
      ? `<nav aria-label="Static page links">${links.map((link) => `<a href="${escapeHtml(link.href)}">${escapeHtml(link.label)}</a>`).join(" | ")}</nav>`
      : "",
    "</main>",
  ].filter(Boolean).join("\n");
}

function buildPages({ book, manifest }) {
  const homeDescription = "The Earnalism controlled launch begins with Dracula by Bram Stoker. Read Chapter 1 free, then continue with a reading pass. Bengali Gothic and other classics are moving through the rights-safe pipeline.";
  const bookDescription = "Read Dracula by Bram Stoker in The Earnalism’s controlled digital reading room. Chapter 1 is free. Continue with a 7-day reading pass. Audiobook experience is in private review.";
  const libraryDescription = "Live Controlled Release: Dracula only. Future classics are coming through The Earnalism rights-safe pipeline and are not live reading products yet.";
  const pricingDescription = "Choose your reading time for Dracula on The Earnalism. Chapter 1 is free, with premium reading-time packs and no subscription or autorenewal.";
  const journalDescription = "Launch notes from The Earnalism's Dracula-first controlled digital reading room and rights-safe publication pipeline.";
  const contactDescription = "Contact The Earnalism about Dracula reading-time access, support, refunds, school interest, and rights-safe publication questions.";
  const readerDescription = "The Dracula reader is the reading interface for approved Earnalism access. Search engines should use the public Dracula book page instead.";

  return [
    {
      path: "/",
      title: "Begin with Dracula | The Earnalism Digital Library",
      description: homeDescription,
      canonicalPath: "/",
      ogTitle: "Begin with Dracula | The Earnalism",
      ogDescription: "Chapter 1 is free. Continue with a reading pass as more classics move through the rights-safe pipeline.",
      imageAlt: "The Earnalism Dracula controlled launch",
      jsonLd: [organizationJsonLd(), websiteJsonLd(homeDescription), webpageJsonLd({ title: "Begin with Dracula", description: homeDescription, path: "/" })],
      staticBody: pageShell({
        eyebrow: "The Earnalism Digital Library",
        title: "Begin with Dracula.",
        body: homeDescription,
        facts: ["Dracula is the only live approved classic reading release today.", "Audiobook experience is in private review.", "Kshudhita Pashan remains pipeline-only."],
        links: [
          { href: "/reader/dracula", label: "Read Chapter 1 Free" },
          { href: "/book/dracula", label: "Start Dracula" },
          { href: "/pricing?book=dracula", label: "Get 7-Day Reading Pass" },
          { href: "/library?category=pipeline", label: "Explore Pipeline / Library" },
        ],
      }),
    },
    {
      path: "/book/dracula",
      title: "Dracula by Bram Stoker | The Earnalism Digital Library",
      description: bookDescription,
      canonicalPath: "/book/dracula",
      ogType: "book",
      ogTitle: "Dracula by Bram Stoker | The Earnalism",
      ogDescription: "Chapter 1 is free. Continue with a 7-day reading pass.",
      twitterTitle: "Dracula by Bram Stoker | The Earnalism",
      twitterDescription: "Chapter 1 is free. Continue with a 7-day reading pass.",
      image: book.cover_image_url || DRACULA_IMAGE,
      imageAlt: "Dracula by Bram Stoker on The Earnalism",
      bookOgTags: [
        metaTag("property", "book:author", "Bram Stoker"),
        metaTag("property", "book:release_date", "1897"),
        metaTag("property", "book:tag", "Gothic fiction"),
      ],
      jsonLd: [
        webpageJsonLd({ title: "Dracula by Bram Stoker", description: bookDescription, path: "/book/dracula" }),
        draculaBookJsonLd(),
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: "Library", path: "/library" },
          { name: "Dracula", path: "/book/dracula" },
        ]),
      ],
      staticBody: pageShell({
        eyebrow: "Live Controlled Release",
        title: "Dracula by Bram Stoker",
        body: bookDescription,
        facts: [
          `${manifest.chapter_count} chapters.`,
          "Chapter 1 is free.",
          "Public-domain source verified.",
          "Rights status: approved classic reading release.",
          "Audiobook experience is in private review.",
        ],
        links: [
          { href: "/reader/dracula", label: "Read Chapter 1 Free" },
          { href: "/pricing?book=dracula", label: "Get 7-Day Reading Pass" },
          { href: "/library", label: "Back to Library" },
        ],
      }),
    },
    {
      path: "/library",
      title: "Library | Dracula Is Live on The Earnalism",
      description: libraryDescription,
      canonicalPath: "/library",
      ogTitle: "Library | Dracula Is Live on The Earnalism",
      ogDescription: "Dracula is the only live controlled reading release. Future books are pipeline-only until rights and QA pass.",
      imageAlt: "The Earnalism controlled library",
      jsonLd: [
        webpageJsonLd({ title: "Library | Dracula Is Live", description: libraryDescription, path: "/library" }),
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: "Library", path: "/library" },
        ]),
      ],
      staticBody: pageShell({
        eyebrow: "Library - Controlled Launch",
        title: "Live Controlled Release: Dracula only.",
        body: "Coming Through the Rights-Safe Pipeline: future titles only. These books are not live products yet and have Notify Me CTAs only.",
        facts: ["Unapproved books are not live reading products.", "No unapproved title offers reader, preview, or listening CTAs."],
        links: [
          { href: "/book/dracula", label: "Open Dracula" },
          { href: "/reader/dracula", label: "Read Chapter 1 Free" },
        ],
      }),
    },
    {
      path: "/pricing",
      title: "Choose Your Reading Time | Dracula on The Earnalism",
      description: pricingDescription,
      canonicalPath: "/pricing",
      ogTitle: "Choose Your Reading Time | The Earnalism",
      ogDescription: "Continue Dracula with premium reading-time packs. No subscription or autorenewal.",
      imageAlt: "Earnalism Dracula reading-time pricing",
      jsonLd: [webpageJsonLd({ title: "Choose Your Reading Time", description: pricingDescription, path: "/pricing" })],
      staticBody: pageShell({
        eyebrow: "Reading Time",
        title: "Choose your reading time. Return whenever the book calls.",
        body: "Start with Chapter 1 free. When you are ready to continue Dracula, add reading time. Your time is used only while you read.",
        facts: [
          "The First Chapter - Rs 49.",
          "The Quiet Hour - Rs 89 - Best first choice.",
          "The Deep Reading Pass - Rs 239.",
          "The Reader’s Reserve - Rs 499 - Best value.",
          "Secure payment by Razorpay. No subscription or autorenewal.",
        ],
        links: [{ href: "/pricing?book=dracula", label: "Continue Dracula" }],
      }),
    },
    {
      path: "/journal",
      title: "Journal | The Earnalism Dracula Launch Notes",
      description: journalDescription,
      canonicalPath: "/journal",
      ogTitle: "Journal | The Earnalism",
      ogDescription: "Notes from the Dracula-first controlled launch and rights-safe reading pipeline.",
      imageAlt: "Earnalism journal",
      jsonLd: [webpageJsonLd({ title: "Journal | The Earnalism", description: journalDescription, path: "/journal" })],
      staticBody: pageShell({
        eyebrow: "Journal",
        title: "Notes from a Dracula-first reading room.",
        body: journalDescription,
        links: [
          { href: "/book/dracula", label: "Open Dracula" },
          { href: "/library", label: "Library" },
        ],
      }),
    },
    {
      path: "/contact",
      title: "Contact The Earnalism | Dracula Reading Support",
      description: contactDescription,
      canonicalPath: "/contact",
      ogTitle: "Contact The Earnalism",
      ogDescription: "Contact The Earnalism for Dracula reading-time support, refunds, school interest, and rights questions.",
      imageAlt: "Contact The Earnalism",
      jsonLd: [organizationJsonLd(), webpageJsonLd({ title: "Contact The Earnalism", description: contactDescription, path: "/contact" })],
      staticBody: pageShell({
        eyebrow: "Contact",
        title: "Contact The Earnalism.",
        body: contactDescription,
        facts: ["Support and refund questions: sales@reoenterprise.org."],
        links: [
          { href: "mailto:sales@reoenterprise.org", label: "Email support" },
          { href: "/book/dracula", label: "Open Dracula" },
        ],
      }),
    },
    {
      path: "/reader/dracula",
      title: "Read Dracula Chapter 1 | The Earnalism Reader",
      description: readerDescription,
      canonicalPath: "/book/dracula",
      robots: "noindex,follow",
      ogTitle: "Read Dracula Chapter 1 | The Earnalism",
      ogDescription: "Chapter 1 is free. Use the Dracula book page for sharing and discovery.",
      imageAlt: "The Earnalism Dracula reader",
      jsonLd: [webpageJsonLd({ title: "Read Dracula Chapter 1", description: readerDescription, path: "/reader/dracula" })],
      staticBody: pageShell({
        eyebrow: "Reader Interface",
        title: "Read Dracula Chapter 1.",
        body: "This reader page is noindex and canonicalized to the public Dracula book page. Audiobook experience is in private review.",
        facts: [`${manifest.chapter_count} chapters in the manifest.`, "Preview chapter unlocked.", "Audio controls hidden."],
        links: [
          { href: "/book/dracula", label: "Public Dracula Page" },
          { href: "/pricing?book=dracula", label: "Get 7-Day Reading Pass" },
        ],
      }),
    },
  ];
}

async function writeSnapshot(page, template) {
  const targetPath = page.path === "/"
    ? path.join(buildDir, "index.html")
    : path.join(buildDir, page.path.replace(/^\/+/, ""), "index.html");
  await mkdir(path.dirname(targetPath), { recursive: true });
  await writeFile(targetPath, withStaticFallback(template, page), "utf8");
  return path.relative(buildDir, targetPath);
}

async function main() {
  const template = await readSnapshotTemplate();
  const artifacts = await loadDraculaArtifacts();
  const pages = buildPages(artifacts);
  const written = [];

  for (const page of pages) {
    written.push(await writeSnapshot(page, template));
  }

  console.log(`[static-seo] Wrote ${written.length} static snapshots: ${written.join(", ")}`);
}

main().catch((error) => {
  console.error(`[static-seo] ${error.stack || error.message}`);
  process.exitCode = 1;
});
