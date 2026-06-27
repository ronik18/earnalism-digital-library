#!/usr/bin/env node

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const DEFAULT_STATUS = path.join(ROOT, "output/bengali_draft_publish_readiness_latest.json");
const DEFAULT_OUTPUT = path.join(ROOT, "output/generated_bengali_covers");
const DEFAULT_MANIFESTS = [
  path.join(ROOT, "book_import_manifest.json"),
  path.join(ROOT, "output/source_repair/20260602T192021Z/source_repaired_404_manifest.json"),
  path.join(ROOT, "output/bengali_source_repair/20260603T084835Z/bengali_source_repaired_upload_manifest.json"),
];

function parseArgs(argv) {
  const args = { status: DEFAULT_STATUS, output: DEFAULT_OUTPUT, manifests: [] };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--status" && next) {
      args.status = path.resolve(next);
      index += 1;
    } else if (arg === "--output-dir" && next) {
      args.output = path.resolve(next);
      index += 1;
    } else if (arg === "--manifest" && next) {
      args.manifests.push(path.resolve(next));
      index += 1;
    }
  }
  if (!args.manifests.length) args.manifests = DEFAULT_MANIFESTS;
  return args;
}

const CATEGORY_LABELS = {
  "literary-fiction": "Literary Fiction",
  "young-readers": "Young Readers",
  adventure: "Adventure",
  "gothic-fiction": "Gothic Fiction",
  "history-strategy": "History & Strategy",
  "bengali-classics": "Bengali Classics",
};

const PALETTES = [
  ["#4c1d25", "#f7f0e6", "#c9964a", "#241819"],
  ["#183c3d", "#f4efe7", "#a85f3f", "#152124"],
  ["#28334a", "#f7f2e8", "#b88a44", "#171b24"],
  ["#4d3226", "#f5eddf", "#8f6a3f", "#1f1915"],
  ["#284229", "#f6f0e5", "#b06c4c", "#151d17"],
];

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function displayText(value) {
  return String(value || "")
    .replace(/[\u200c\u200d]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeHtml(value) {
  return displayText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function loadManifestBooks(manifestFiles) {
  const books = new Map();
  const byTitle = new Map();
  for (const file of manifestFiles) {
    if (!fs.existsSync(file)) continue;
    const data = readJson(file);
    const rows = Array.isArray(data) ? data : data.books || [];
    for (const row of rows) {
      if (!row) continue;
      if (row.slug) books.set(row.slug, row);
      const titleKey = displayText(row.title).toLocaleLowerCase();
      if (titleKey) byTitle.set(titleKey, row);
    }
  }
  return { books, byTitle };
}

function paletteFor(slug) {
  const score = [...slug].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return PALETTES[score % PALETTES.length];
}

function titleSize(title) {
  const length = [...displayText(title)].length;
  if (length > 24) return 76;
  if (length > 18) return 88;
  return 108;
}

function htmlFor(book, kind) {
  const slug = book.slug;
  const title = escapeHtml(book.title || slug);
  const author = escapeHtml(book.author || "Earnalism");
  const category = escapeHtml(CATEGORY_LABELS[book.category_slug] || "Bengali Library");
  const [ink, paper, accent, dark] = paletteFor(slug);
  const titleFontSize = titleSize(book.title || slug);
  const isFront = kind === "front";
  return `<!doctype html>
<html lang="bn">
<head>
  <meta charset="utf-8" />
  <style>
    * { box-sizing: border-box; }
    html, body {
      width: 1200px;
      height: 1800px;
      margin: 0;
      background: ${paper};
      color: ${dark};
      font-family: "Bangla MN", "Bangla Sangam MN", "Kohinoor Bangla", "Noto Serif Bengali", Georgia, serif;
    }
    .cover {
      position: relative;
      width: 1200px;
      height: 1800px;
      border: 42px solid ${paper};
      outline: 4px solid ${accent};
      outline-offset: -42px;
      overflow: hidden;
    }
    .inner {
      position: absolute;
      inset: 66px;
      border: 2px solid ${ink};
      padding: 58px 30px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .brand {
      align-self: stretch;
      color: ${accent};
      font-family: Avenir, Helvetica, Arial, sans-serif;
      font-size: 28px;
      letter-spacing: 0;
      padding-bottom: 32px;
      border-bottom: 3px solid ${accent};
    }
    .front-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 100%;
      transform: translateY(-20px);
    }
    .title {
      color: ${ink};
      font-size: ${titleFontSize}px;
      line-height: 1.14;
      max-width: 930px;
      text-align: center;
      overflow-wrap: anywhere;
    }
    .author {
      margin-top: 54px;
      color: ${dark};
      font-size: 48px;
      line-height: 1.18;
      max-width: 900px;
      text-align: center;
    }
    .rule {
      width: 580px;
      height: 3px;
      background: ${accent};
      margin: 42px 0 34px;
    }
    .category {
      color: ${ink};
      font-family: Avenir, Helvetica, Arial, sans-serif;
      font-size: 33px;
      letter-spacing: 0;
      text-align: center;
    }
    .footer {
      align-self: stretch;
      font-family: Avenir, Helvetica, Arial, sans-serif;
      font-size: 25px;
      color: ${dark};
    }
    .back-main {
      flex: 1;
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 44px;
      transform: translateY(-8px);
    }
    .back-copy {
      color: ${dark};
      font-family: Avenir, Helvetica, Arial, sans-serif;
      font-size: 27px;
      line-height: 1.75;
      max-width: 760px;
      text-align: center;
    }
  </style>
</head>
<body>
  <main class="cover">
    <section class="inner">
      <div class="brand">${isFront ? "Earnalism Digital Library" : "Earnalism"}</div>
      ${
        isFront
          ? `<div class="front-main">
              <div class="title">${title}</div>
              <div class="author">${author}</div>
            </div>
            <div class="rule"></div>
            <div class="category">${category} / Bengali</div>
            <div class="footer">A clean reader-ready edition</div>`
          : `<div class="back-main">
              <div class="title" style="font-size:${Math.max(58, titleFontSize - 24)}px">${title}</div>
              <div class="author">${author}</div>
              <div class="rule"></div>
              <div class="back-copy">
                Prepared for quiet, focused digital reading.<br />
                Source provenance and rights evidence are retained internally.<br />
                Reader-facing text is kept free from repository boilerplate.
              </div>
              <div class="category">${category}</div>
            </div>`
      }
    </section>
  </main>
</body>
</html>`;
}

async function main() {
  const args = parseArgs(process.argv);
  fs.mkdirSync(args.output, { recursive: true });
  const statusRows = readJson(args.status);
  const { books, byTitle } = loadManifestBooks(args.manifests);
  const executablePath = fs.existsSync("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    : undefined;
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1200, height: 1800 }, deviceScaleFactor: 1 });
  const rendered = [];

  for (const row of statusRows) {
    const slug = row.slug;
    if (!slug || (row.front && row.back)) continue;
    const source = books.get(slug) || byTitle.get(displayText(row.title).toLocaleLowerCase());
    if (!source) {
      rendered.push({ slug, status: "skipped", reason: "not found in cover metadata manifests" });
      continue;
    }
    const book = {
      ...source,
      ...row,
      slug,
      title: row.title || source.title,
      author: row.author || source.author,
      category_slug: row.category_slug || source.category_slug || source.categoryslug || "bengali-classics",
    };
    for (const kind of ["front", "back"]) {
      await page.setContent(htmlFor(book, kind), { waitUntil: "load" });
      const file = path.join(args.output, `${slug}_${kind}.png`);
      await page.screenshot({ path: file, type: "png", clip: { x: 0, y: 0, width: 1200, height: 1800 } });
      rendered.push({ slug, title: book.title, kind, file });
      console.log(`${slug}: rendered ${kind} ${file}`);
    }
  }

  await browser.close();
  const report = path.join(args.output, "browser_render_report.json");
  fs.writeFileSync(report, JSON.stringify({ rendered }, null, 2));
  console.log(`Report: ${report}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
