#!/usr/bin/env node

const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");
const crypto = require("crypto");
const { spawn, spawnSync } = require("child_process");
const { uploadAudiobook } = require("../../lib/storage/audioUploader");

const ROOT = path.resolve(__dirname, "../..");
const DEFAULT_API_URL = "https://api.theearnalism.com/api";
const DEFAULT_OUTPUT_ROOT = path.join(ROOT, "output", "bengali_audiobook_polish");
const BENGALI_RE = /[\u0980-\u09ff]/;
const ENGLISH_TOKEN_RE = /\b[A-Za-z][A-Za-z0-9.+#&'/-]*\b/g;
const WORD_RE = /[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?|[\u0980-\u09ff]+/g;
const TTS_PAUSE_TOKEN_RE = /\[\[break:(\d+)ms\]\]/g;
const DEFAULT_QA_THRESHOLD = 9.3;
const DEFAULT_CHUNK_CHARS = 3600;
const DEFAULT_CONCURRENCY = 1;
const DEFAULT_STORAGE_FOLDER = "earnalism/audiobooks-polished";
const REPORT_FILE = "bengali_audiobook_polish_report.json";
const PROGRESS_FILE = "progress.json";
const DEFAULT_TTS_REQUEST_DELAY_MS = 3000;
const DEFAULT_TTS_MAX_RETRIES = 8;
const DEFAULT_TTS_RETRY_BASE_DELAY_MS = 30000;
const DEFAULT_TTS_RETRY_MAX_DELAY_MS = 600000;
const DEFAULT_TTS_COMMAND_TIMEOUT_MS = 300000;
const DEFAULT_TRANSIENT_NETWORK_MAX_RETRIES = 4;
const DEFAULT_TRANSIENT_NETWORK_BASE_DELAY_MS = 2000;
const DEFAULT_TRANSIENT_NETWORK_MAX_DELAY_MS = 30000;
const DEFAULT_TTS_RATE = "+3%";
const DEFAULT_TTS_PITCH = "+1Hz";
const DEFAULT_PAUSE_PROFILE = "natural-expressive";
const NATURAL_EXPRESSIVE_PAUSES = {
  comma: 120,
  semicolon: 180,
  colon: 220,
  sentence: 280,
  question: 320,
  exclamation: 300,
  dash: 180,
  repeatedDash: 220,
  ellipsis: 380,
  dialogueChange: 260,
  paragraph: 420,
  section: 650,
  chapter: 900,
};
const PROSODY_PROFILES = {
  narration: { rate: DEFAULT_TTS_RATE, pitch: DEFAULT_TTS_PITCH },
  dialogue: { rate: "+5%", pitch: "+2Hz" },
  dramatic: { rate: "0%", pitch: "+0Hz" },
  chapter: { rate: "-2%", pitch: DEFAULT_TTS_PITCH },
};

const DEFAULT_LEXICON = {
  Earnalism: "আর্নালিজম",
  "Reo Enterprise": "রিও এন্টারপ্রাইজ",
  Chapter: "অধ্যায়",
  AI: "এ আই",
  API: "এ পি আই",
  AWS: "এ ডাব্লিউ এস",
  B2: "বি টু",
  CDN: "সি ডি এন",
  CEO: "সি ই ও",
  CSS: "সি এস এস",
  HTML: "এইচ টি এম এল",
  HTTP: "এইচ টি টি পি",
  HTTPS: "এইচ টি টি পি এস",
  JSON: "জেসন",
  MongoDB: "মঙ্গো ডি বি",
  Redis: "রেডিস",
  SEO: "এস ই ও",
  TTS: "টি টি এস",
  URL: "ইউ আর এল",
  audiobook: "অডিওবুক",
  "audio book": "অডিওবুক",
  "digital library": "ডিজিটাল লাইব্রেরি",
  business: "বিজনেস",
  history: "হিস্ট্রি",
  library: "লাইব্রেরি",
  online: "অনলাইন",
  technology: "টেকনোলজি",
};

function usage() {
  return `
Usage:
  node scripts/audio/polishBengaliAudiobooks.js --sample 3
  node scripts/audio/polishBengaliAudiobooks.js --slug book-slug
  node scripts/audio/polishBengaliAudiobooks.js --all-bengali --commit

Selectors:
  --sample N                 Randomly audit N Bengali audiobooks
  --slug SLUG                Process one slug; repeatable
  --all-bengali              Process all detected Bengali audiobooks
  --manifest PATH            Process slugs from a queue/list JSON in file order
  --export-queue PATH        Write a Bengali audiobook queue JSON and exit
  --queue-sort NAME          generation-size, current-audio-size, or slug; default generation-size

Safety:
  --dry-run                  Report only; default
  --commit                   Generate, upload, and patch admin audiobook fields
  --concurrency N            Worker count; default 1
  --job-id ID                Stable output/progress folder for resumable runs
  --resume                   Resume existing progress; default
  --no-resume                Ignore existing progress for this job
  --restart                  Clear existing progress for this job before running
  --force                    Regenerate completed chunks and books for this job
  --max-books N              Process at most N selected books
  --start-after SLUG         Start after this slug/id in the selected order

Quality/TTS:
  --qa-threshold N           Default ${DEFAULT_QA_THRESHOLD}
  --tts-provider NAME        Default BENGALI_TTS_PROVIDER or "none"
  --chunk-chars N            Default ${DEFAULT_CHUNK_CHARS}
  --lexicon PATH             JSON or key=value pronunciation lexicon
  --verbose                  Save/print normalization, SSML, pause, and chunk diagnostics
  --self-test-normalization  Run local normalization/SSML examples without admin API access
  --human-reviewed           Allows a verified generated bundle to satisfy a 9.9 gate
  --allow-review-commit      Upload even when automated QA recommends manual review
`;
}

function parseArgs(argv) {
  const args = {
    slug: [],
    sample: 0,
    allBengali: false,
    dryRun: false,
    commit: false,
    concurrency: DEFAULT_CONCURRENCY,
    apiUrl: process.env.EARNALISM_API_URL || DEFAULT_API_URL,
    envFile: [],
    manifest: "",
    exportQueue: "",
    queueSort: "generation-size",
    maxBooks: 0,
    startAfter: "",
    outputDir: DEFAULT_OUTPUT_ROOT,
    jobId: "",
    resume: true,
    restart: false,
    qaThreshold: Number(process.env.BENGALI_AUDIO_QA_THRESHOLD || DEFAULT_QA_THRESHOLD),
    ttsProvider: process.env.BENGALI_TTS_PROVIDER || "none",
    chunkChars: Number(process.env.BENGALI_TTS_CHUNK_CHARS || DEFAULT_CHUNK_CHARS),
    lexicon: process.env.BENGALI_AUDIO_PRONUNCIATION_LEXICON || "",
    humanReviewed: false,
    allowReviewCommit: false,
    forceRegenerate: false,
    verbose: false,
    selfTestNormalization: false,
    ttsRate: process.env.BENGALI_TTS_RATE || process.env.BENGALI_TTS_SSML_RATE || DEFAULT_TTS_RATE,
    ttsPitch: process.env.BENGALI_TTS_PITCH || process.env.BENGALI_TTS_SSML_PITCH || DEFAULT_TTS_PITCH,
    ttsRequestDelayMs: Number(process.env.BENGALI_TTS_REQUEST_DELAY_MS || process.env.BENGALI_TTS_CHUNK_DELAY_MS || DEFAULT_TTS_REQUEST_DELAY_MS),
    ttsMaxRetries: Number(process.env.BENGALI_TTS_MAX_RETRIES || DEFAULT_TTS_MAX_RETRIES),
    ttsRetryBaseDelayMs: Number(process.env.BENGALI_TTS_RETRY_BASE_DELAY_MS || DEFAULT_TTS_RETRY_BASE_DELAY_MS),
    ttsRetryMaxDelayMs: Number(process.env.BENGALI_TTS_RETRY_MAX_DELAY_MS || DEFAULT_TTS_RETRY_MAX_DELAY_MS),
    ttsRetryJitter: !/^false|0|no$/i.test(String(process.env.BENGALI_TTS_RETRY_JITTER || "true")),
    stopOnQuota: !/^false|0|no$/i.test(String(process.env.BENGALI_TTS_PAUSE_ON_429 || process.env.BENGALI_TTS_STOP_ON_QUOTA || "true")),
    pauseProfile: process.env.BENGALI_TTS_PAUSE_PROFILE || DEFAULT_PAUSE_PROFILE,
    storageFolder: process.env.BENGALI_AUDIO_POLISH_STORAGE_FOLDER || DEFAULT_STORAGE_FOLDER,
    explicit: {},
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    const readValue = (name) => {
      if (!next || next.startsWith("--")) throw new Error(`${name} requires a value`);
      index += 1;
      return next;
    };

    if (token === "--help" || token === "-h") {
      args.help = true;
    } else if (token === "--sample") {
      args.sample = Number.parseInt(readValue(token), 10) || 0;
    } else if (token === "--slug") {
      args.slug.push(normalizeSlug(readValue(token)));
    } else if (token === "--all-bengali") {
      args.allBengali = true;
    } else if (token === "--dry-run") {
      args.dryRun = true;
    } else if (token === "--commit") {
      args.commit = true;
    } else if (token === "--concurrency") {
      args.concurrency = Math.max(1, Number.parseInt(readValue(token), 10) || DEFAULT_CONCURRENCY);
    } else if (token === "--api-url") {
      args.apiUrl = readValue(token);
      args.explicit.apiUrl = true;
    } else if (token === "--env-file") {
      args.envFile.push(readValue(token));
    } else if (token === "--manifest") {
      args.manifest = path.resolve(readValue(token));
    } else if (token === "--export-queue") {
      args.exportQueue = path.resolve(readValue(token));
    } else if (token === "--queue-sort") {
      args.queueSort = readValue(token).trim().toLowerCase();
    } else if (token === "--output-dir") {
      args.outputDir = path.resolve(readValue(token));
    } else if (token === "--job-id") {
      args.jobId = safeFileName(readValue(token), "default");
    } else if (token === "--resume") {
      args.resume = true;
    } else if (token === "--no-resume") {
      args.resume = false;
    } else if (token === "--restart") {
      args.restart = true;
      args.resume = false;
    } else if (token === "--qa-threshold") {
      args.qaThreshold = Number(readValue(token)) || DEFAULT_QA_THRESHOLD;
      args.explicit.qaThreshold = true;
    } else if (token === "--tts-provider") {
      args.ttsProvider = readValue(token).trim().toLowerCase();
      args.explicit.ttsProvider = true;
    } else if (token === "--chunk-chars") {
      args.chunkChars = Math.max(300, Number.parseInt(readValue(token), 10) || DEFAULT_CHUNK_CHARS);
      args.explicit.chunkChars = true;
    } else if (token === "--lexicon") {
      args.lexicon = readValue(token);
      args.explicit.lexicon = true;
    } else if (token === "--human-reviewed") {
      args.humanReviewed = true;
    } else if (token === "--allow-review-commit") {
      args.allowReviewCommit = true;
    } else if (token === "--force-regenerate") {
      args.forceRegenerate = true;
    } else if (token === "--force") {
      args.forceRegenerate = true;
      args.resume = true;
    } else if (token === "--max-books") {
      args.maxBooks = Math.max(0, Number.parseInt(readValue(token), 10) || 0);
    } else if (token === "--start-after") {
      args.startAfter = normalizeSlug(readValue(token));
    } else if (token === "--verbose") {
      args.verbose = true;
    } else if (token === "--self-test-normalization") {
      args.selfTestNormalization = true;
      args.resume = false;
      args.dryRun = true;
    } else if (token === "--storage-folder") {
      args.storageFolder = readValue(token).replace(/^\/+|\/+$/g, "") || DEFAULT_STORAGE_FOLDER;
      args.explicit.storageFolder = true;
    } else {
      throw new Error(`Unknown option: ${token}`);
    }
  }

  if (args.commit && args.dryRun) {
    throw new Error("Use either --dry-run or --commit, not both.");
  }
  if (!["generation-size", "current-audio-size", "slug"].includes(args.queueSort)) {
    throw new Error("--queue-sort must be generation-size, current-audio-size, or slug.");
  }
  args.dryRun = !args.commit;
  args.apiUrl = normalizeApiUrl(args.apiUrl);
  args.jobId = args.jobId || new Date().toISOString().replace(/[:.]/g, "-");
  args.jobDir = path.join(args.outputDir, args.jobId);
  return args;
}

function applyEnvDefaults(args) {
  if (!args.explicit.apiUrl && process.env.EARNALISM_API_URL) {
    args.apiUrl = process.env.EARNALISM_API_URL;
  }
  if (!args.explicit.qaThreshold && process.env.BENGALI_AUDIO_QA_THRESHOLD) {
    args.qaThreshold = Number(process.env.BENGALI_AUDIO_QA_THRESHOLD) || args.qaThreshold;
  }
  if (!args.explicit.ttsProvider && process.env.BENGALI_TTS_PROVIDER) {
    args.ttsProvider = process.env.BENGALI_TTS_PROVIDER.trim().toLowerCase();
  }
  if (!args.explicit.chunkChars && process.env.BENGALI_TTS_CHUNK_CHARS) {
    args.chunkChars = Math.max(300, Number.parseInt(process.env.BENGALI_TTS_CHUNK_CHARS, 10) || args.chunkChars);
  }
  if (!args.explicit.lexicon && process.env.BENGALI_AUDIO_PRONUNCIATION_LEXICON) {
    args.lexicon = process.env.BENGALI_AUDIO_PRONUNCIATION_LEXICON;
  }
  if (process.env.BENGALI_TTS_RATE || process.env.BENGALI_TTS_SSML_RATE) {
    args.ttsRate = process.env.BENGALI_TTS_RATE || process.env.BENGALI_TTS_SSML_RATE;
  }
  if (process.env.BENGALI_TTS_PITCH || process.env.BENGALI_TTS_SSML_PITCH) {
    args.ttsPitch = process.env.BENGALI_TTS_PITCH || process.env.BENGALI_TTS_SSML_PITCH;
  }
  if (process.env.BENGALI_TTS_PAUSE_PROFILE) {
    args.pauseProfile = process.env.BENGALI_TTS_PAUSE_PROFILE;
  }
  if (process.env.BENGALI_TTS_CONCURRENCY) {
    args.concurrency = Math.max(1, Number.parseInt(process.env.BENGALI_TTS_CONCURRENCY, 10) || args.concurrency);
  }
  if (process.env.BENGALI_TTS_REQUEST_DELAY_MS || process.env.BENGALI_TTS_CHUNK_DELAY_MS) {
    args.ttsRequestDelayMs = Number(process.env.BENGALI_TTS_REQUEST_DELAY_MS || process.env.BENGALI_TTS_CHUNK_DELAY_MS) || args.ttsRequestDelayMs;
  }
  if (process.env.BENGALI_TTS_MAX_RETRIES) {
    args.ttsMaxRetries = Number(process.env.BENGALI_TTS_MAX_RETRIES) || args.ttsMaxRetries;
  }
  if (process.env.BENGALI_TTS_RETRY_BASE_DELAY_MS) {
    args.ttsRetryBaseDelayMs = Number(process.env.BENGALI_TTS_RETRY_BASE_DELAY_MS) || args.ttsRetryBaseDelayMs;
  }
  if (process.env.BENGALI_TTS_RETRY_MAX_DELAY_MS) {
    args.ttsRetryMaxDelayMs = Number(process.env.BENGALI_TTS_RETRY_MAX_DELAY_MS) || args.ttsRetryMaxDelayMs;
  }
  if (process.env.BENGALI_TTS_RETRY_JITTER) {
    args.ttsRetryJitter = !/^false|0|no$/i.test(String(process.env.BENGALI_TTS_RETRY_JITTER));
  }
  if (process.env.BENGALI_TTS_PAUSE_ON_429 || process.env.BENGALI_TTS_STOP_ON_QUOTA) {
    args.stopOnQuota = !/^false|0|no$/i.test(String(process.env.BENGALI_TTS_PAUSE_ON_429 || process.env.BENGALI_TTS_STOP_ON_QUOTA));
  }
  if (!args.explicit.storageFolder && process.env.BENGALI_AUDIO_POLISH_STORAGE_FOLDER) {
    args.storageFolder = process.env.BENGALI_AUDIO_POLISH_STORAGE_FOLDER.replace(/^\/+|\/+$/g, "") || args.storageFolder;
  }
  args.apiUrl = normalizeApiUrl(args.apiUrl);
}

function loadEnvFile(filePath) {
  const resolved = path.resolve(ROOT, filePath);
  if (!fs.existsSync(resolved)) return;
  const lines = fs.readFileSync(resolved, "utf8").split(/\r?\n/);
  for (const raw of lines) {
    let line = raw.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    if (line.startsWith("export ")) line = line.slice("export ".length).trim();
    const separator = line.indexOf("=");
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
    if (key && process.env[key] === undefined) process.env[key] = value;
  }
}

function normalizeApiUrl(value) {
  const trimmed = String(value || DEFAULT_API_URL).replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

function normalizeSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/_/g, "-")
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function safeFileName(value, fallback) {
  return normalizeSlug(value) || fallback;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function ensureDir(dir) {
  await fsp.mkdir(dir, { recursive: true });
}

async function writeJson(filePath, data) {
  await ensureDir(path.dirname(filePath));
  await fsp.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function sha256Short(value) {
  return crypto.createHash("sha256").update(String(value || "")).digest("hex").slice(0, 16);
}

function cleanText(value) {
  return String(value || "")
    .replace(/\ufeff/g, "")
    .replace(/[\u200c\u200d]/g, "")
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t\u00a0]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function htmlToText(value) {
  return cleanText(
    String(value || "")
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<\/(p|div|section|article|h[1-6]|li)>/gi, "\n")
      .replace(/<(br|hr)\s*\/?>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&quot;/g, '"')
      .replace(/&#39;|&apos;/g, "'")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">"),
  );
}

function escapeXml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function escapeRegExp(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function stripTtsPauseTokens(value, replacement = " ") {
  return String(value || "").replace(TTS_PAUSE_TOKEN_RE, replacement);
}

function tokenizeWords(text) {
  return Array.from(stripTtsPauseTokens(text).matchAll(WORD_RE)).map((match) => match[0]).filter(Boolean);
}

function detectEnglishTerms(text) {
  const counts = new Map();
  for (const match of stripTtsPauseTokens(text).matchAll(ENGLISH_TOKEN_RE)) {
    const token = match[0];
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([term, count]) => ({ term, count }))
    .sort((a, b) => b.count - a.count || a.term.localeCompare(b.term));
}

function lexiconCoverageStats(englishTerms, lexicon) {
  const totalTerms = englishTerms.length;
  const coveredTerms = englishTerms.filter(({ term }) => lexicon[term] || lexicon[term.toLowerCase()]);
  const totalOccurrences = englishTerms.reduce((sum, item) => sum + Number(item.count || 0), 0);
  const coveredOccurrences = coveredTerms.reduce((sum, item) => sum + Number(item.count || 0), 0);
  return {
    coveredTerms,
    uniqueCoverage: totalTerms ? coveredTerms.length / totalTerms : 1,
    weightedCoverage: totalOccurrences ? coveredOccurrences / totalOccurrences : 1,
    totalOccurrences,
    coveredOccurrences,
  };
}

function normalizeWholeWordLexicon(text, lexicon) {
  let output = String(text || "");
  const stats = {
    replacements: 0,
    terms: {},
  };
  const entries = Object.entries(lexicon || {})
    .filter(([term, value]) => term && value && /[A-Za-z]/.test(term))
    .sort((a, b) => b[0].length - a[0].length);

  for (const [term, value] of entries) {
    const pattern = escapeRegExp(term).replace(/\s+/g, "\\s+");
    const regex = new RegExp(`(^|[^A-Za-z0-9])(${pattern})(?=$|[^A-Za-z0-9])`, "gi");
    output = output.replace(regex, (match, prefix) => {
      stats.replacements += 1;
      stats.terms[term] = (stats.terms[term] || 0) + 1;
      return `${prefix}${value}`;
    });
  }

  return { text: output, stats };
}

function replaceWithCount(text, regex, replacer) {
  let count = 0;
  const next = String(text || "").replace(regex, (...args) => {
    count += 1;
    return typeof replacer === "function" ? replacer(...args) : replacer;
  });
  return { text: next, count };
}

function normalizeBengaliTtsText(text, options = {}) {
  let output = cleanText(text)
    .replace(/\u09f7/g, "।")
    .replace(/\.{3,}|…/g, "...")
    .replace(/[ \t]+([।?!,;:])/g, "$1")
    .replace(/([,;:?!।॥])(?=\S)/g, "$1 ")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]+\n/g, "\n");

  const stats = {
    lexiconReplacementCount: 0,
    lexiconReplacementTerms: {},
    hyphenMinusNormalizationCount: 0,
    hyphenMinusNormalizationApplied: false,
    mixedLanguageTermsNormalized: 0,
  };

  const lexiconResult = normalizeWholeWordLexicon(output, options.lexicon || {});
  output = lexiconResult.text;
  stats.lexiconReplacementCount = lexiconResult.stats.replacements;
  stats.lexiconReplacementTerms = lexiconResult.stats.terms;
  stats.mixedLanguageTermsNormalized = lexiconResult.stats.replacements;

  const rules = [
    {
      name: "negative_number",
      regex: /(^|[\s([{"'“‘])[-−]\s*([০-৯0-9]+)/g,
      replace: (_match, prefix, number) => `${prefix}ঋণাত্মক ${number}`,
    },
    {
      name: "numeric_range",
      regex: /([০-৯0-9]+)\s*[-−]\s*([০-৯0-9]+)/g,
      replace: (_match, left, right) => `${left} থেকে ${right}`,
    },
    {
      name: "bengali_hyphen",
      regex: /([\u0980-\u09ff]+)\s*-\s*([\u0980-\u09ff]+)/g,
      replace: (_match, left, right) => `${left} ${right}`,
    },
    {
      name: "english_hyphen",
      regex: /([A-Za-z]+)\s*-\s*([A-Za-z]+)/g,
      replace: (_match, left, right) => `${left} ${right}`,
    },
    {
      name: "english_bengali_hyphen",
      regex: /([A-Za-z]+)\s*-\s*([\u0980-\u09ff]+)/g,
      replace: (_match, left, right) => `${left} ${right}`,
    },
    {
      name: "bengali_english_hyphen",
      regex: /([\u0980-\u09ff]+)\s*-\s*([A-Za-z]+)/g,
      replace: (_match, left, right) => `${left} ${right}`,
    },
    {
      name: "stray_minus",
      regex: /[-−]/g,
      replace: " ",
    },
  ];

  for (const rule of rules) {
    const result = replaceWithCount(output, rule.regex, rule.replace);
    output = result.text;
    stats.hyphenMinusNormalizationCount += result.count;
    if (rule.name.includes("english") && result.count) {
      stats.mixedLanguageTermsNormalized += result.count;
    }
  }

  stats.hyphenMinusNormalizationApplied = stats.hyphenMinusNormalizationCount > 0;
  output = output
    .replace(/[ \t]{2,}/g, " ")
    .replace(/ ?\[\[break:(\d+)ms\]\] ?/g, " [[break:$1ms]] ")
    .replace(/\n{4,}/g, "\n\n\n")
    .trim();

  return { text: output, stats };
}

function isBengaliBook(book) {
  const explicit = String(book.language || book.language_hint || book.in_language || "").toLowerCase();
  if (["bn", "ben", "bengali", "bn-in", "bn-bd"].includes(explicit)) return true;
  return BENGALI_RE.test(`${book.title || ""} ${book.author || ""} ${book.description || ""} ${book.short_description || ""}`);
}

function currentAudioInfo(book) {
  const nested = book.audiobook && typeof book.audiobook === "object" ? book.audiobook : {};
  const nestedAssets = nested.assets && typeof nested.assets === "object" ? nested.assets : {};
  const assets = book.audiobook_assets && typeof book.audiobook_assets === "object" ? book.audiobook_assets : {};
  const mergedAssets = { ...assets, ...nestedAssets };
  const mp3 = nested.url || mergedAssets.mp3 || "";
  const provider = String(nested.provider || book.audiobook_provider || providerFromUrl(mp3) || "").toLowerCase();
  const duration = Number(nested.duration_ms || nested.duration || book.audiobook_duration_ms || 0) || 0;
  const size = Number(nested.size || book.audiobook_size || 0) || 0;
  return {
    provider,
    url: mp3,
    assets: mergedAssets,
    duration_ms: duration,
    size,
    voice: book.audiobook_voice || nested.voice || "",
    enabled: Boolean(book.audiobook_enabled || book.generate_audiobook || mp3 || mergedAssets.timestamps),
  };
}

function providerFromUrl(url) {
  const text = String(url || "").toLowerCase();
  if (!text) return "";
  if (text.includes("backblazeb2.com")) return "b2";
  if (text.includes("res.cloudinary.com")) return "cloudinary";
  return "";
}

function resolveAssetUrl(url, apiUrl) {
  const value = String(url || "").trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith("/api/")) return `${apiUrl.replace(/\/api$/, "")}${value}`;
  if (value.startsWith("/")) return `${process.env.EARNALISM_SITE_URL || "https://theearnalism.com"}${value}`;
  return value;
}

async function fetchWithRetry(url, options = {}, attempts = 3) {
  let lastError = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          Accept: "application/json",
          ...(options.headers || {}),
        },
      });
      if ([502, 503, 504].includes(response.status) && attempt < attempts) {
        await sleep(attempt * 2000);
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
      if (attempt < attempts) await sleep(attempt * 2000);
    }
  }
  throw lastError || new Error(`Request failed: ${url}`);
}

async function requestJson(method, url, { headers = {}, body } = {}) {
  const response = await fetchWithRetry(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${method} ${url} failed: HTTP ${response.status} ${text.slice(0, 300)}`);
  }
  return text.trim() ? JSON.parse(text) : {};
}

class EarnalismAdminClient {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
    this.headers = {};
  }

  async login() {
    let token = String(process.env.EARNALISM_ADMIN_TOKEN || "").trim();
    if (!token) {
      const email = String(process.env.ADMIN_EMAIL || "").trim();
      const password = String(process.env.ADMIN_PASSWORD || "").trim();
      if (!email || !password) {
        throw new Error("Missing ADMIN_EMAIL/ADMIN_PASSWORD or EARNALISM_ADMIN_TOKEN for admin API access.");
      }
      const data = await requestJson("POST", `${this.apiUrl}/auth/login`, {
        body: { email, password },
      });
      token = String(data.token || "").trim();
    }
    if (!token) throw new Error("Admin login did not return a token.");
    this.headers = { Authorization: `Bearer ${token}` };
  }

  summaries() {
    return requestJson("GET", `${this.apiUrl}/admin/books/summary`, { headers: this.headers });
  }

  book(slug) {
    return requestJson("GET", `${this.apiUrl}/admin/books/${encodeURIComponent(slug)}`, { headers: this.headers });
  }

  patchAudiobook(slug, payload) {
    return requestJson("PATCH", `${this.apiUrl}/admin/books/${encodeURIComponent(slug)}/audiobook`, {
      headers: this.headers,
      body: payload,
    });
  }
}

async function loadLexicon(lexiconPath) {
  const lexicon = { ...DEFAULT_LEXICON };
  if (!lexiconPath) return lexicon;
  const resolved = path.resolve(ROOT, lexiconPath);
  if (!fs.existsSync(resolved)) throw new Error(`Pronunciation lexicon not found: ${resolved}`);
  const raw = await fsp.readFile(resolved, "utf8");
  if (resolved.endsWith(".json")) {
    const parsed = JSON.parse(raw);
    for (const [key, value] of Object.entries(parsed)) {
      if (key && value) lexicon[key] = typeof value === "string" ? value : String(value.alias || value.pronunciation || value.ssml || "");
    }
    return lexicon;
  }
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const [key, ...rest] = trimmed.split("=");
    const value = rest.join("=").trim();
    if (key.trim() && value) lexicon[key.trim()] = value;
  }
  return lexicon;
}

function normalizeBengaliPunctuation(text) {
  return cleanText(text)
    .replace(/\s*([,;:])\s*/g, "$1 ")
    .replace(/\s*([?!])\s*/g, "$1 ")
    .replace(/\s*([।॥])\s*/g, "$1 ")
    .replace(/\.{3,}/g, "...")
    .replace(/[ \t]+([।?!,;:])/g, "$1")
    .replace(/([।?!])\s+/g, "$1 ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function bookNarrationText(book) {
  const chapters = [...(book.chapters || [])].sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
  const parts = [];
  const markers = [];
  for (const chapter of chapters) {
    const title = cleanText(chapter.title || "");
    const body = htmlToText(chapter.content || "");
    const chapterText = [title && title.toLowerCase() !== "full text" ? title : "", body].filter(Boolean).join("\n\n");
    if (!chapterText) continue;
    markers.push({ title: title || book.title || "Chapter", char_index: parts.join("\n\n").length });
    parts.push(chapterText);
  }
  const text = normalizeBengaliPunctuation(parts.join("\n\n"));
  return { text, markers };
}

function englishTokenMarkup(token, lexicon) {
  const alias = lexicon[token] || lexicon[token.toLowerCase()] || "";
  if (alias && alias !== token) return escapeXml(alias);
  if (/^[A-Z0-9.+#&-]{2,}$/.test(token)) {
    const rendered = token.replace(/([A-Z])/g, "$1 ").trim();
    return `<say-as interpret-as="characters">${escapeXml(rendered)}</say-as>`;
  }
  return `<lang xml:lang="en-US">${escapeXml(token)}</lang>`;
}

function breakTag(ms) {
  return `<break time="${Math.max(0, Math.round(Number(ms) || 0))}ms"/>`;
}

function collapseAdjacentBreaks(markup) {
  let output = String(markup || "");
  const adjacentBreaks = /<break time="(\d+)ms"\/>\s*<break time="(\d+)ms"\/>/;
  while (adjacentBreaks.test(output)) {
    output = output.replace(adjacentBreaks, (_match, left, right) => breakTag(Math.max(Number(left), Number(right))));
  }
  return output;
}

function applyPauseMarkupToEscapedText(value, options = {}) {
  const pauses = options.pauses || NATURAL_EXPRESSIVE_PAUSES;
  return String(value || "")
    .replace(TTS_PAUSE_TOKEN_RE, (_match, ms) => breakTag(Math.min(Number(ms), pauses.section)))
    .replace(/\.{3}|…/g, breakTag(pauses.ellipsis))
    .replace(/-{3,}/g, breakTag(pauses.repeatedDash))
    .replace(/-{2}/g, breakTag(pauses.repeatedDash))
    .replace(/[—–]/g, breakTag(pauses.dash))
    .replace(/[-−]/g, " ")
    .replace(/॥/g, `॥${breakTag(pauses.section)}`)
    .replace(/।/g, `।${breakTag(pauses.sentence)}`)
    .replace(/\.(?!\d)/g, `.${breakTag(pauses.sentence)}`)
    .replace(/\?/g, `?${breakTag(pauses.question)}`)
    .replace(/!/g, `!${breakTag(pauses.exclamation)}`)
    .replace(/[,،，]/g, `,${breakTag(pauses.comma)}`)
    .replace(/;/g, `;${breakTag(pauses.semicolon)}`)
    .replace(/:/g, `:${breakTag(pauses.colon)}`);
}

function renderTextFragment(rawText, lexicon, options = {}) {
  const raw = String(rawText || "");
  const parts = [];
  let cursor = 0;

  for (const match of raw.matchAll(ENGLISH_TOKEN_RE)) {
    const start = match.index || 0;
    if (start > cursor) {
      parts.push(applyPauseMarkupToEscapedText(escapeXml(raw.slice(cursor, start)), options));
    }
    parts.push(englishTokenMarkup(match[0], lexicon));
    cursor = start + match[0].length;
  }

  if (cursor < raw.length) {
    parts.push(applyPauseMarkupToEscapedText(escapeXml(raw.slice(cursor)), options));
  }
  return parts.join("");
}

function likelyChapterHeading(text) {
  const cleaned = stripTtsPauseTokens(text).trim();
  if (!cleaned || cleaned.length > 90) return false;
  if (/[।?!:;,.]$/.test(cleaned)) return false;
  return /^(chapter|অধ্যায়|পরিচ্ছেদ|খণ্ড|প্রস্তাবনা|উপক্রমণিকা|প্রথম|দ্বিতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম)\b/i.test(cleaned);
}

function sentenceProfile(text, fallback = "narration") {
  const cleaned = stripTtsPauseTokens(text).trim();
  if (!cleaned) return fallback;
  if (/["“”‘’]/.test(cleaned)) return "dialogue";
  if (/[?!]/.test(cleaned)) return "dialogue";
  if (/(\.\.\.|…|[—–])/.test(cleaned)) return "dramatic";
  return fallback;
}

function splitSentenceSegments(text, fallbackProfile = "narration") {
  const raw = String(text || "").trim();
  if (!raw) return [];
  if (fallbackProfile === "chapter") return [{ type: "text", profile: "chapter", text: raw }];
  const segments = [];
  const sentenceRegex = /[^।?!.!…]+(?:[।?!.!…]+|$)/g;
  for (const match of raw.matchAll(sentenceRegex)) {
    const value = match[0].trim();
    if (value) segments.push({ type: "text", profile: sentenceProfile(value, fallbackProfile), text: value });
  }
  return segments.length ? segments : [{ type: "text", profile: sentenceProfile(raw, fallbackProfile), text: raw }];
}

function splitDialogueSegments(text, fallbackProfile = "narration") {
  const raw = String(text || "");
  const quoteRegex = /(["“][^"“”]+["”]|['‘][^'‘’]+['’])/g;
  const segments = [];
  let cursor = 0;
  for (const match of raw.matchAll(quoteRegex)) {
    const start = match.index || 0;
    if (start > cursor) {
      segments.push(...splitSentenceSegments(raw.slice(cursor, start), fallbackProfile));
    }
    segments.push({ type: "text", profile: "dialogue", text: match[0].trim() });
    cursor = start + match[0].length;
  }
  if (cursor < raw.length) {
    segments.push(...splitSentenceSegments(raw.slice(cursor), fallbackProfile));
  }
  return segments;
}

function splitExpressiveSegments(text, options = {}) {
  const pauses = options.pauses || NATURAL_EXPRESSIVE_PAUSES;
  const tokens = String(text || "").split(/(\n{3,}|\n\s*\n|\n)/);
  const segments = [];
  let atBlockStart = true;

  for (const token of tokens) {
    if (!token) continue;
    if (/^\n{3,}$/.test(token)) {
      segments.push({ type: "break", ms: pauses.section });
      atBlockStart = true;
      continue;
    }
    if (/^\n\s*\n$/.test(token)) {
      segments.push({ type: "break", ms: pauses.paragraph });
      atBlockStart = true;
      continue;
    }
    if (/^\n$/.test(token)) {
      segments.push({ type: "break", ms: pauses.dialogueChange });
      atBlockStart = true;
      continue;
    }

    const trimmed = token.trim();
    if (!trimmed) continue;
    const fallbackProfile = atBlockStart && likelyChapterHeading(trimmed) ? "chapter" : "narration";
    segments.push(...splitDialogueSegments(trimmed, fallbackProfile));
    atBlockStart = false;
  }

  return segments;
}

function prosodyForProfile(profile, options = {}) {
  const baseRate = options.rate || process.env.BENGALI_TTS_RATE || process.env.BENGALI_TTS_SSML_RATE || DEFAULT_TTS_RATE;
  const basePitch = options.pitch || process.env.BENGALI_TTS_PITCH || process.env.BENGALI_TTS_SSML_PITCH || DEFAULT_TTS_PITCH;
  const profiles = {
    ...PROSODY_PROFILES,
    narration: { rate: baseRate, pitch: basePitch },
  };
  return profiles[profile] || profiles.narration;
}

function wrapProsody(profile, body, options = {}) {
  const prosody = prosodyForProfile(profile, options);
  return `<prosody rate="${escapeXml(prosody.rate)}" pitch="${escapeXml(prosody.pitch)}">${body}</prosody>`;
}

function stripSsmlTags(value) {
  return String(value || "").replace(/<[^>]+>/g, "");
}

function analyzeSsml(ssml, segments, options = {}) {
  const pauseDurations = Array.from(String(ssml || "").matchAll(/<break time="(\d+)ms"\/>/g))
    .map((match) => Number(match[1]) || 0);
  const totalPause = pauseDurations.reduce((sum, value) => sum + value, 0);
  const profileCounts = segments
    .filter((segment) => segment.type === "text")
    .reduce((counts, segment) => {
      counts[segment.profile] = (counts[segment.profile] || 0) + 1;
      return counts;
    }, {});
  const dialogueSegmentsDetected = profileCounts.dialogue || 0;
  const textOnly = stripSsmlTags(ssml);
  const rate = options.rate || process.env.BENGALI_TTS_RATE || process.env.BENGALI_TTS_SSML_RATE || DEFAULT_TTS_RATE;
  const pitch = options.pitch || process.env.BENGALI_TTS_PITCH || process.env.BENGALI_TTS_SSML_PITCH || DEFAULT_TTS_PITCH;
  const ratePercent = Number(String(rate).match(/[-+]?\d+(?:\.\d+)?/)?.[0] || 0);
  const estimatedWordsPerMinute = Math.round(135 * (1 + ratePercent / 100));
  const averagePauseMs = pauseDurations.length ? Math.round(totalPause / pauseDurations.length) : 0;
  const maxPauseMs = pauseDurations.length ? Math.max(...pauseDurations) : 0;
  const pausesOver650ms = pauseDurations.filter((value) => value > NATURAL_EXPRESSIVE_PAUSES.section).length;
  const unsafeHyphenDashRemaining = /[-–—−]/.test(textOnly);
  const slowGlobalRate = /^-/.test(String(rate).trim());
  const roboticFlatnessRisk = slowGlobalRate
    || averagePauseMs > 360
    || pausesOver650ms > 0
    || (dialogueSegmentsDetected > 0 && !profileCounts.dialogue)
    ? "high"
    : (dialogueSegmentsDetected === 0 && (profileCounts.dramatic || 0) === 0 ? "medium" : "low");

  return {
    ssmlProfileUsed: "azure-command-natural-expressive",
    rateUsed: rate,
    pitchUsed: pitch,
    pauseProfileUsed: options.pauseProfile || process.env.BENGALI_TTS_PAUSE_PROFILE || DEFAULT_PAUSE_PROFILE,
    mixedLanguageTermsLanguageMarked: (String(ssml || "").match(/<lang\s+xml:lang="en-US">/g) || []).length,
    averagePauseMs,
    maxPauseMs,
    pausesOver650ms,
    totalInsertedPauses: pauseDurations.length,
    estimatedWordsPerMinute,
    dialogueSegmentsDetected,
    unsafeHyphenDashRemaining,
    prosodyProfileCounts: profileCounts,
    roboticFlatnessRisk,
  };
}

function buildBengaliSsmlDocument(text, lexicon, options = {}) {
  const pauses = NATURAL_EXPRESSIVE_PAUSES;
  const segments = splitExpressiveSegments(text, { pauses });
  const pieces = [];
  let activeProfile = "";
  let activeParts = [];

  const flush = () => {
    if (!activeParts.length) return;
    pieces.push(wrapProsody(activeProfile || "narration", activeParts.join(" "), options));
    activeProfile = "";
    activeParts = [];
  };

  for (const segment of segments) {
    if (segment.type === "break") {
      flush();
      pieces.push(breakTag(segment.ms));
      continue;
    }
    const rendered = renderTextFragment(segment.text, lexicon, { pauses });
    if (!rendered.trim()) continue;
    if (activeProfile && activeProfile !== segment.profile) flush();
    activeProfile = segment.profile || "narration";
    activeParts.push(rendered);
  }
  flush();

  const body = collapseAdjacentBreaks(pieces.join(""));
  const ssml = `<speak>${body}</speak>`;
  return {
    ssml,
    stats: analyzeSsml(ssml, segments, {
      rate: options.rate,
      pitch: options.pitch,
      pauseProfile: options.pauseProfile,
    }),
  };
}

function buildBengaliSsml(text, lexicon, options = {}) {
  return buildBengaliSsmlDocument(text, lexicon, options).ssml;
}

function prepareNarration(book, lexicon, args = {}) {
  const { text: sourceText, markers } = bookNarrationText(book);
  const normalized = normalizeBengaliTtsText(sourceText, { lexicon });
  const text = normalized.text;
  const englishTerms = detectEnglishTerms(text);
  const coverage = lexiconCoverageStats(englishTerms, lexicon);
  const plainWithPauses = text
    .replace(TTS_PAUSE_TOKEN_RE, " ")
    .replace(/([।?!])\n/g, "$1  \n")
    .replace(/,/g, ", ")
    .replace(/\n\s*\n/g, "\n\n");
  const ssmlDocument = buildBengaliSsmlDocument(text, lexicon, {
    rate: args.ttsRate,
    pitch: args.ttsPitch,
    pauseProfile: args.pauseProfile,
  });
  const chunks = chunkText(text, args.chunkChars || DEFAULT_CHUNK_CHARS);
  return {
    plainText: plainWithPauses,
    normalizedText: text,
    ssml: ssmlDocument.ssml,
    ssmlStats: {
      ...ssmlDocument.stats,
      hyphenMinusNormalizationApplied: normalized.stats.hyphenMinusNormalizationApplied,
      hyphenMinusNormalizationCount: normalized.stats.hyphenMinusNormalizationCount,
      mixedLanguageTermsNormalized: normalized.stats.mixedLanguageTermsNormalized,
      lexiconReplacementCount: normalized.stats.lexiconReplacementCount,
      lexiconReplacementTerms: normalized.stats.lexiconReplacementTerms,
    },
    normalizationStats: normalized.stats,
    chunkStats: {
      chunkCount: chunks.length,
      averageChunkSize: chunks.length
        ? Math.round(chunks.reduce((sum, chunk) => sum + chunk.length, 0) / chunks.length)
        : 0,
      maxChunkSize: chunks.length ? Math.max(...chunks.map((chunk) => chunk.length)) : 0,
      minChunkSize: chunks.length ? Math.min(...chunks.map((chunk) => chunk.length)) : 0,
      targetChunkChars: args.chunkChars || DEFAULT_CHUNK_CHARS,
    },
    chapterMarkers: markers,
    wordCount: tokenizeWords(text).length,
    characterCount: text.length,
    englishTerms,
    coveredEnglishTerms: coverage.coveredTerms,
    lexiconCoverage: coverage.weightedCoverage,
    lexiconCoverageUnique: coverage.uniqueCoverage,
    lexiconOccurrences: {
      total: coverage.totalOccurrences,
      covered: coverage.coveredOccurrences,
    },
  };
}

function splitSentences(text) {
  const sentences = [];
  let cursor = "";
  for (const char of String(text || "")) {
    cursor += char;
    if (/[।?!.!…]/.test(char) && !hasOpenQuote(cursor)) {
      sentences.push(cursor.trim());
      cursor = "";
    }
  }
  if (cursor.trim()) sentences.push(cursor.trim());
  return sentences;
}

function hasOpenQuote(text) {
  const value = String(text || "");
  const asciiDouble = (value.match(/"/g) || []).length;
  const asciiSingle = (value.match(/'/g) || []).length;
  const curlyDoubleOpen = (value.match(/“/g) || []).length;
  const curlyDoubleClose = (value.match(/”/g) || []).length;
  const curlySingleOpen = (value.match(/‘/g) || []).length;
  const curlySingleClose = (value.match(/’/g) || []).length;
  return asciiDouble % 2 === 1
    || asciiSingle % 2 === 1
    || curlyDoubleOpen > curlyDoubleClose
    || curlySingleOpen > curlySingleClose;
}

function chunkText(text, maxChars) {
  const targetMax = Math.min(4000, Math.max(800, Number(maxChars) || DEFAULT_CHUNK_CHARS));
  const targetMin = Math.min(2500, Math.max(800, Math.round(targetMax * 0.72)));
  const paragraphs = String(text || "").split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
  const chunks = [];
  let current = "";

  const pushCurrent = () => {
    if (current.trim()) chunks.push(current.trim());
    current = "";
  };

  const addPiece = (piece) => {
    const candidate = current ? `${current}\n\n${piece}` : piece;
    if (candidate.length <= targetMax) {
      current = candidate;
      return;
    }
    pushCurrent();
    if (piece.length <= targetMax) {
      current = piece;
      return;
    }
    const sentences = splitSentences(piece);
    for (const sentence of sentences.length ? sentences : [piece]) {
      if (sentence.length <= targetMax) {
        addPiece(sentence);
        continue;
      }
      let fragment = "";
      for (const token of sentence.split(/(\s+)/)) {
        const next = `${fragment}${token}`;
        if (next.length > targetMax && fragment.trim()) {
          chunks.push(fragment.trim());
          fragment = token;
        } else {
          fragment = next;
        }
      }
      if (fragment.trim()) chunks.push(fragment.trim());
    }
  };

  for (const paragraph of paragraphs) addPiece(paragraph);
  pushCurrent();

  const merged = [];
  for (const chunk of chunks) {
    const previous = merged[merged.length - 1];
    if (previous && (chunk.length < targetMin || previous.length < targetMin) && `${previous}\n\n${chunk}`.length <= targetMax) {
      merged[merged.length - 1] = `${previous}\n\n${chunk}`;
    } else {
      merged.push(chunk);
    }
  }
  return merged;
}

async function auditCurrentAudio(book, apiUrl) {
  const audio = currentAudioInfo(book);
  const result = {
    has_audio: Boolean(audio.url),
    head_ok: false,
    head_status: "",
    content_length: audio.size,
    content_type: "",
    timestamps_ok: false,
    timestamps_status: "",
    timestamp_count: 0,
    timestamps_monotonic: false,
    duration_ms: audio.duration_ms,
    issues: [],
  };
  if (!audio.url) {
    result.issues.push("missing current audiobook URL");
    return result;
  }

  const resolvedAudioUrl = resolveAssetUrl(audio.url, apiUrl);
  try {
    const head = await fetchWithRetry(resolvedAudioUrl, { method: "HEAD" }, 2);
    result.head_ok = head.ok || [302, 307, 308].includes(head.status);
    result.head_status = String(head.status);
    result.content_length = Number(head.headers.get("content-length") || audio.size || 0);
    result.content_type = head.headers.get("content-type") || "";
    if (!result.head_ok) result.issues.push(`audio HEAD failed with HTTP ${head.status}`);
  } catch (error) {
    result.head_status = error.message;
    result.issues.push(`audio HEAD failed: ${error.message}`);
  }

  const timestampsUrl = resolveAssetUrl(audio.assets.timestamps || "", apiUrl);
  if (!timestampsUrl) {
    result.issues.push("missing timestamp sidecar");
    return result;
  }
  try {
    const response = await fetchWithRetry(timestampsUrl, { method: "GET" }, 2);
    result.timestamps_status = String(response.status);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const timestamps = await response.json();
    result.timestamps_ok = Array.isArray(timestamps) && timestamps.length > 0;
    result.timestamp_count = Array.isArray(timestamps) ? timestamps.length : 0;
    result.timestamps_monotonic = Array.isArray(timestamps) && timestamps.every((item, index) => {
      if (index === 0) return Number(item.start_ms || 0) <= Number(item.end_ms || 0);
      const previous = timestamps[index - 1];
      return Number(previous.end_ms || 0) <= Number(item.start_ms || 0)
        && Number(item.start_ms || 0) <= Number(item.end_ms || 0);
    });
    if (!result.timestamps_ok) result.issues.push("timestamp sidecar is empty or invalid");
    if (result.timestamps_ok && !result.timestamps_monotonic) result.issues.push("timestamps are not monotonic");
  } catch (error) {
    result.issues.push(`timestamp fetch/parse failed: ${error.message}`);
  }
  return result;
}

function clampScore(value) {
  return Math.max(0, Math.min(10, Number(value.toFixed(2))));
}

function providerProfile(provider, voice) {
  const identity = `${provider || ""} ${voice || ""}`.toLowerCase();
  if (identity.includes("sarvam")) return { clarity: 8.8, pronunciation: 8.7, expression: 8.9 };
  if (identity.includes("google")) return { clarity: 8.7, pronunciation: 8.8, expression: 8.2 };
  if (identity.includes("indic-parler")) return { clarity: 8.2, pronunciation: 8.0, expression: 8.6 };
  if (identity.includes("mms-tts")) return { clarity: 6.8, pronunciation: 6.5, expression: 5.8 };
  if (identity.includes("b2") || identity.includes("cloudinary")) return { clarity: 7.2, pronunciation: 6.8, expression: 6.6 };
  return { clarity: 6.4, pronunciation: 6.2, expression: 6.0 };
}

function preparedQualityIssues(prepared) {
  const stats = prepared.ssmlStats || {};
  const issues = [];
  if (stats.pausesOver650ms > 0) issues.push(`SSML has ${stats.pausesOver650ms} pauses above 650ms`);
  if (stats.averagePauseMs > 360) issues.push(`average inserted pause is high: ${stats.averagePauseMs}ms`);
  if (/^-/.test(String(stats.rateUsed || "").trim())) issues.push(`global TTS rate is slow: ${stats.rateUsed}`);
  if (stats.unsafeHyphenDashRemaining) issues.push("unsafe hyphen/dash/minus remains in final SSML text");
  if (stats.estimatedWordsPerMinute && stats.estimatedWordsPerMinute < 125) {
    issues.push(`estimated generated speaking rate is slow: ${stats.estimatedWordsPerMinute} wpm`);
  }
  if (stats.dialogueSegmentsDetected > 0 && !(stats.prosodyProfileCounts || {}).dialogue) {
    issues.push("dialogue exists but no dialogue prosody variation was applied");
  }
  if (stats.roboticFlatnessRisk === "high") issues.push("generated SSML has high robotic/flatness risk");
  return issues;
}

function mixedLanguageStats(prepared) {
  const occurrences = Number(prepared.lexiconOccurrences?.total || 0);
  const wordCount = Math.max(1, Number(prepared.wordCount || 0));
  const density = occurrences / wordCount;
  const coverage = Number(prepared.lexiconCoverage || 0);
  const replacementCount = Number(prepared.normalizationStats?.lexiconReplacementCount || 0);
  const languageMarkedCount = Number(prepared.ssmlStats?.mixedLanguageTermsLanguageMarked || 0);
  const handledOccurrences = Math.min(occurrences, replacementCount + languageMarkedCount);
  const handledCoverage = occurrences ? handledOccurrences / occurrences : 1;
  const isIncidental = occurrences <= 25 || density < 0.003;
  return {
    occurrences,
    density,
    replacementCount,
    languageMarkedCount,
    coverage: isIncidental ? Math.max(coverage, handledCoverage, 0.92) : Math.max(coverage, handledCoverage),
    isIncidental,
  };
}

function scoreRegenerationReadiness({ provider, prepared }) {
  const stats = prepared.ssmlStats || {};
  const mixedStats = mixedLanguageStats(prepared);
  const providerConfigured = Boolean(provider?.configured);
  const supportsSsml = Boolean(provider?.supportsSsml);
  const chunkStats = prepared.chunkStats || {};
  const chunkAverage = Number(chunkStats.averageChunkSize || 0);
  const chunkShapeOk = (Number(chunkStats.chunkCount || 0) <= 1 || chunkAverage >= 1800)
    && chunkAverage <= 3800
    && Number(chunkStats.maxChunkSize || 0) <= 4000;
  const pauseShapeOk = Number(stats.averagePauseMs || 0) > 0
    && Number(stats.averagePauseMs || 0) <= 280
    && Number(stats.maxPauseMs || 0) <= NATURAL_EXPRESSIVE_PAUSES.section
    && Number(stats.pausesOver650ms || 0) === 0;
  const expressionOk = Number(stats.dialogueSegmentsDetected || 0) === 0
    || Number(stats.prosodyProfileCounts?.dialogue || 0) > 0;
  const pacingOk = Number(stats.estimatedWordsPerMinute || 0) >= 130
    && Number(stats.estimatedWordsPerMinute || 0) <= 155;
  const mixedOk = mixedStats.isIncidental || mixedStats.coverage >= 0.86;

  const clarity = clampScore((providerConfigured ? 9.25 : 8.35) + (supportsSsml ? 0.35 : -0.25));
  const pronunciation = clampScore(9.05 + Math.min(0.45, mixedStats.coverage * 0.45) + (mixedOk ? 0.15 : -0.45));
  const expression = clampScore(9.15 + (expressionOk ? 0.35 : -0.65) - (stats.roboticFlatnessRisk === "low" ? 0 : 0.5));
  const pacing = clampScore(9.2 + (pacingOk ? 0.25 : -0.65) + (chunkShapeOk ? 0.15 : -0.35));
  const punctuation = clampScore(9.25 + (pauseShapeOk ? 0.35 : -0.8));
  const mixed = clampScore(mixedOk ? 9.35 : 8.15);
  const overall = clampScore(
    clarity * 0.18
    + pronunciation * 0.22
    + expression * 0.2
    + pacing * 0.16
    + punctuation * 0.14
    + mixed * 0.1,
  );

  const issues = [];
  if (!providerConfigured) issues.push("TTS command is not configured for commit mode");
  if (!supportsSsml) issues.push("TTS provider is not marked as SSML-capable");
  if (!chunkShapeOk) issues.push("chunk sizing is outside the preferred 2500-4000 character band");
  if (!pauseShapeOk) issues.push("pause profile is outside the natural-expressive target");
  if (!expressionOk) issues.push("dialogue exists but no dialogue prosody variation was detected");
  if (!pacingOk) issues.push(`estimated generated speaking rate is outside target: ${stats.estimatedWordsPerMinute || 0} wpm`);
  if (stats.unsafeHyphenDashRemaining) issues.push("unsafe hyphen/dash/minus remains in final SSML text");
  if (!mixedOk) issues.push("mixed-language pronunciation coverage needs lexicon additions");

  return {
    detected_issues: issues,
    clarity_score: clarity,
    pronunciation_score: pronunciation,
    expression_score: expression,
    pacing_score: pacing,
    punctuation_pause_score: punctuation,
    mixed_bengali_english_handling_score: mixed,
    overall_score: overall,
    provider_configured: providerConfigured,
    supports_ssml: supportsSsml,
    chunk_shape_ok: chunkShapeOk,
    pause_shape_ok: pauseShapeOk,
    expression_variation_ok: expressionOk,
    pacing_ok: pacingOk,
    mixed_language_ok: mixedOk,
    recommendation: overall >= 9 && !issues.some((issue) => /unsafe|outside|not marked/i.test(issue))
      ? "ready for commit"
      : "configure/review before commit",
  };
}

function scoreCurrentAudiobook(book, prepared, audit, threshold) {
  const current = currentAudioInfo(book);
  const issues = [...audit.issues, ...preparedQualityIssues(prepared)];
  const profile = providerProfile(current.provider, current.voice);
  const durationMinutes = (audit.duration_ms || current.duration_ms || 0) / 60000;
  const wordsPerMinute = durationMinutes > 0 ? prepared.wordCount / durationMinutes : 0;
  const punctuationCount = (prepared.normalizedText.match(/[।?!,;:]/g) || []).length;
  const punctuationDensity = prepared.wordCount ? punctuationCount / prepared.wordCount : 0;
  const mixedStats = mixedLanguageStats(prepared);
  const englishCoverage = mixedStats.coverage;

  if (current.provider.includes("mms-tts")) issues.push("current provider is fast/open-source TTS; likely less expressive for premium Bengali narration");
  if (prepared.englishTerms.length && !mixedStats.isIncidental && englishCoverage < 0.75) {
    issues.push("mixed Bengali-English terms need more pronunciation lexicon coverage");
  }
  if (!wordsPerMinute) issues.push("duration unavailable; pacing could not be verified");
  if (wordsPerMinute && (wordsPerMinute < 95 || wordsPerMinute > 190)) {
    issues.push(`pacing outside Bengali narration target: ${Math.round(wordsPerMinute)} wpm`);
  }

  const clarity = clampScore((audit.head_ok ? profile.clarity : 2.5) + (audit.content_length > 1024 * 1024 ? 0.3 : 0));
  const pronunciation = clampScore(profile.pronunciation - (1 - englishCoverage) * 1.8);
  const expression = clampScore(profile.expression + Math.min(0.4, punctuationDensity * 5));
  const pacing = clampScore(wordsPerMinute ? 9.2 - Math.min(3.2, Math.abs(wordsPerMinute - 135) / 22) : 6.0);
  const punctuation = clampScore((audit.timestamps_monotonic ? 8.5 : 5.2) + Math.min(0.9, punctuationDensity * 8));
  const mixed = clampScore(prepared.englishTerms.length ? 5.8 + englishCoverage * 3.5 : 9.0);
  const overall = clampScore(
    clarity * 0.18
    + pronunciation * 0.22
    + expression * 0.2
    + pacing * 0.16
    + punctuation * 0.14
    + mixed * 0.1,
  );
  let recommendation = "keep";
  if (!current.enabled || !audit.has_audio) recommendation = "regenerate";
  else if (overall < Math.min(8.6, threshold)) recommendation = "regenerate";
  else if (overall < threshold || issues.length) recommendation = "needs manual review";

  return {
    detected_issues: Array.from(new Set(issues)),
    clarity_score: clarity,
    pronunciation_score: pronunciation,
    expression_score: expression,
    pacing_score: pacing,
    punctuation_pause_score: punctuation,
    mixed_bengali_english_handling_score: mixed,
    overall_score: overall,
    words_per_minute: wordsPerMinute ? Number(wordsPerMinute.toFixed(1)) : 0,
    recommendation,
  };
}

function scoreGeneratedBundle({ provider, prepared, durationMs, timestamps, supportsSsml, humanReviewed, threshold }) {
  const wordsPerMinute = durationMs > 0 ? prepared.wordCount / (durationMs / 60000) : 0;
  const timestampCount = timestamps.length;
  const timestampRatio = prepared.wordCount ? timestampCount / prepared.wordCount : 0;
  const monotonic = timestamps.every((item, index) => index === 0 || Number(timestamps[index - 1].end_ms) <= Number(item.start_ms));
  const mixedStats = mixedLanguageStats(prepared);
  const englishCoverage = mixedStats.coverage;
  const providerConfigured = provider && provider.name !== "none";
  const ssmlStats = prepared.ssmlStats || {};
  const pausePenalty = Math.min(1.2, (ssmlStats.pausesOver650ms || 0) * 0.2 + Math.max(0, (ssmlStats.averagePauseMs || 0) - 260) / 220);
  const flatnessPenalty = ssmlStats.roboticFlatnessRisk === "high" ? 0.8 : ssmlStats.roboticFlatnessRisk === "medium" ? 0.25 : 0;
  const unsafeDashPenalty = ssmlStats.unsafeHyphenDashRemaining ? 1.0 : 0;
  const base = providerConfigured ? (supportsSsml ? 9.45 : 8.8) : 0;
  const clarity = clampScore(base + (durationMs > 0 ? 0.25 : -2));
  const pronunciation = clampScore(base + englishCoverage * 0.25 - (prepared.englishTerms.length && englishCoverage < 0.8 ? 0.7 : 0));
  const expression = clampScore((supportsSsml ? 9.55 : 8.4) + (humanReviewed ? 0.25 : 0) - flatnessPenalty);
  const pacing = clampScore(wordsPerMinute ? 9.5 - Math.min(2.8, Math.abs(wordsPerMinute - 140) / 30) - pausePenalty : 6.0);
  const punctuation = clampScore((supportsSsml ? 9.6 : 8.5) + (monotonic ? 0.1 : -2) - pausePenalty);
  const mixed = clampScore(prepared.englishTerms.length ? 6.0 + englishCoverage * 3.5 + (supportsSsml ? 0.35 : 0) : 9.4);
  let overall = clampScore(
    clarity * 0.18
    + pronunciation * 0.22
    + expression * 0.2
    + pacing * 0.16
    + punctuation * 0.14
    + mixed * 0.1
    - unsafeDashPenalty,
  );
  if (!humanReviewed) overall = Math.min(overall, 9.65);
  if (humanReviewed && overall >= 9.55 && threshold >= 9.9) overall = 9.9;

  const issues = preparedQualityIssues(prepared);
  if (!providerConfigured) issues.push("no TTS provider configured");
  if (!durationMs) issues.push("generated audio duration could not be measured");
  if (!monotonic) issues.push("generated synthetic timestamps are not monotonic");
  if (timestampRatio < 0.85) issues.push(`timestamp coverage is low: ${timestampRatio.toFixed(2)}`);
  if (!humanReviewed && threshold >= 9.9) issues.push("automated QA is capped below 9.9 until a human listening review is recorded");

  return {
    detected_issues: issues,
    clarity_score: clarity,
    pronunciation_score: pronunciation,
    expression_score: expression,
    pacing_score: pacing,
    punctuation_pause_score: punctuation,
    mixed_bengali_english_handling_score: mixed,
    overall_score: overall,
    words_per_minute: wordsPerMinute ? Number(wordsPerMinute.toFixed(1)) : 0,
    recommendation: overall >= threshold && !issues.length ? "keep" : "needs manual review",
  };
}

function commandExists(command) {
  return spawnSync("sh", ["-lc", `command -v ${shellQuote(command)} >/dev/null 2>&1`]).status === 0;
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

class TtsQuotaError extends Error {
  constructor(message) {
    super(message);
    this.name = "TtsQuotaError";
    this.isQuotaError = true;
  }
}

function isTtsQuotaError(error) {
  const message = String(error?.message || error || "");
  return Boolean(error?.isQuotaError) || /HTTP\s*429|Quota Exceeded|Too Many Requests|rate.?limit/i.test(message);
}

function isTransientNetworkError(error) {
  const code = String(error?.code || error?.name || error?.Code || "");
  const message = String(error?.message || error || "");
  return /ECONNRESET|EADDRNOTAVAIL|ETIMEDOUT|ECONNABORTED|EAI_AGAIN|ENETUNREACH|EHOSTUNREACH|ENOBUFS|EPIPE|ECONNREFUSED|socket hang up|fetch failed|network|timeout/i.test(`${code} ${message}`)
    || /HTTP\s*(408|429|500|502|503|504)\b/i.test(message);
}

function transientNetworkDelayMs(attempt) {
  const baseDelay = Number(process.env.AUDIOBOOK_POLISH_NETWORK_RETRY_BASE_DELAY_MS || DEFAULT_TRANSIENT_NETWORK_BASE_DELAY_MS);
  const maxDelay = Number(process.env.AUDIOBOOK_POLISH_NETWORK_RETRY_MAX_DELAY_MS || DEFAULT_TRANSIENT_NETWORK_MAX_DELAY_MS);
  const capped = Math.min(maxDelay, baseDelay * (2 ** Math.max(0, attempt - 1)));
  const jitterFloor = Math.floor(capped * 0.75);
  const jitterRange = Math.max(1, capped - jitterFloor);
  return jitterFloor + Math.floor(Math.random() * jitterRange);
}

async function withTransientNetworkRetry(label, operation) {
  const maxRetries = Math.max(0, Number(process.env.AUDIOBOOK_POLISH_NETWORK_MAX_RETRIES || DEFAULT_TRANSIENT_NETWORK_MAX_RETRIES));
  let lastError = null;
  for (let attempt = 1; attempt <= maxRetries + 1; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (!isTransientNetworkError(error) || attempt > maxRetries) throw error;
      const delay = transientNetworkDelayMs(attempt);
      process.stdout.write(`${label}: transient network retry ${attempt}/${maxRetries}; waiting ${Math.round(delay / 1000)}s\n`);
      await sleep(delay);
    }
  }
  throw lastError;
}

function retryAfterMs(error) {
  const message = String(error?.message || error || "");
  const match = message.match(/retry_after=([^;\s]+)/i);
  if (!match || !match[1] || match[1] === "not-provided") return 0;
  const value = match[1].trim();
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds > 0) return seconds * 1000;
  const dateMs = Date.parse(value);
  return Number.isFinite(dateMs) ? Math.max(0, dateMs - Date.now()) : 0;
}

function retryDelayMs(error, attempt, args) {
  const retryAfter = retryAfterMs(error);
  if (retryAfter > 0) return Math.min(retryAfter, args.ttsRetryMaxDelayMs);
  const exponential = args.ttsRetryBaseDelayMs * (2 ** Math.max(0, attempt - 1));
  const capped = Math.min(exponential, args.ttsRetryMaxDelayMs);
  if (!args.ttsRetryJitter) return capped;
  const jitterFloor = Math.floor(capped * 0.75);
  const jitterRange = Math.max(1, capped - jitterFloor);
  return jitterFloor + Math.floor(Math.random() * jitterRange);
}

function replaceCommandPlaceholder(command, name, value) {
  const quoted = shellQuote(value);
  return String(command || "")
    .replaceAll(`"{${name}}"`, quoted)
    .replaceAll(`'{${name}}'`, quoted)
    .replaceAll(`{${name}}`, quoted);
}

function interpolateTtsCommand(command, values) {
  let output = command;
  for (const [name, value] of Object.entries(values)) {
    output = replaceCommandPlaceholder(output, name, value);
  }
  return output;
}

function createTtsProvider(name) {
  const providerName = String(name || "none").toLowerCase();
  if (providerName === "none") {
    return {
      name: "none",
      configured: false,
      supportsSsml: false,
      voice: "",
      async synthesize() {
        throw new Error(
          "No Bengali TTS provider configured. Set BENGALI_TTS_PROVIDER=command and BENGALI_TTS_COMMAND, or run dry-run audit only.",
        );
      },
    };
  }
  if (providerName !== "command") {
    throw new Error(`Unsupported Bengali TTS provider adapter: ${providerName}. Supported adapter: command.`);
  }
  const command = String(process.env.BENGALI_TTS_COMMAND || "").trim();
  if (!command) {
    return {
      name: "command",
      configured: false,
      supportsSsml: false,
      voice: process.env.BENGALI_TTS_VOICE_ID || "",
      async synthesize() {
        throw new Error("BENGALI_TTS_COMMAND is required when BENGALI_TTS_PROVIDER=command.");
      },
    };
  }
  return {
    name: "command",
    configured: true,
    supportsSsml: /^true|1|yes$/i.test(String(process.env.BENGALI_TTS_SUPPORTS_SSML || "")),
    voice: process.env.BENGALI_TTS_VOICE_ID || "command",
    async synthesize({ inputText, ssml, outputPath, inputPath, index, slug }) {
      await fsp.writeFile(inputPath, this.supportsSsml ? ssml : inputText, "utf8");
      const commandText = interpolateTtsCommand(command, {
        input: inputPath,
        output: outputPath,
        ssml,
        slug,
        index: String(index),
      });
      const { stdout } = await runShell(commandText, {
        EARNALISM_TTS_INPUT: inputPath,
        EARNALISM_TTS_OUTPUT: outputPath,
        EARNALISM_TTS_SSML: ssml,
        EARNALISM_TTS_TEXT: inputText,
        EARNALISM_TTS_CHUNK_INDEX: String(index),
        EARNALISM_TTS_SLUG: slug,
      });
      const stat = await fsp.stat(outputPath).catch(() => null);
      if (!stat || stat.size === 0) throw new Error(`TTS command did not create audio: ${outputPath}`);
      const lines = String(stdout || "").trim().split(/\r?\n/).filter(Boolean);
      let ttsMeta = {};
      for (let lineIndex = lines.length - 1; lineIndex >= 0; lineIndex -= 1) {
        try {
          ttsMeta = JSON.parse(lines[lineIndex]);
          break;
        } catch (_error) {
          // Command adapters may print progress before their final JSON metadata.
        }
      }
      return { voice: ttsMeta.voice || this.voice, outputPath, ttsMeta };
    },
  };
}

function runShell(command, extraEnv = {}) {
  const timeoutMs = Number(process.env.BENGALI_TTS_COMMAND_TIMEOUT_MS || DEFAULT_TTS_COMMAND_TIMEOUT_MS);
  return new Promise((resolve, reject) => {
    const child = spawn(command, {
      shell: true,
      cwd: ROOT,
      env: { ...process.env, ...extraEnv },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`TTS command timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(stderr.trim() || stdout.trim() || `Command failed with exit code ${code}`));
    });
  });
}

async function synthesizeWithRetry(provider, payload, args) {
  let lastError = null;
  const maxRetries = Math.max(0, Number(args.ttsMaxRetries ?? DEFAULT_TTS_MAX_RETRIES));
  const maxAttempts = maxRetries + 1;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    if (payload.onAttempt) await payload.onAttempt(attempt);
    try {
      const result = await provider.synthesize(payload);
      if (payload.onSuccess) await payload.onSuccess(attempt);
      return result;
    } catch (error) {
      lastError = error;
      if (isTtsQuotaError(error)) {
        const retryAttempt = Math.min(attempt, maxRetries);
        const shouldRetry = attempt <= maxRetries;
        const delay = shouldRetry ? retryDelayMs(error, retryAttempt || 1, args) : 0;
        if (payload.onRetry) await payload.onRetry({ attempt, retryAttempt, delayMs: delay, error });
        if (!shouldRetry) {
          const quota = new TtsQuotaError(error.message || "Azure Bengali TTS quota exceeded");
          quota.chunk_index = payload.index;
          quota.retry_attempts = maxRetries;
          quota.retry_delay_ms = delay;
          throw quota;
        }
        process.stdout.write(`${payload.slug || "tts"}: Azure 429/quota retry ${retryAttempt}/${maxRetries}; waiting ${Math.round(delay / 1000)}s\n`);
        await sleep(delay);
        continue;
      }
      if (payload.onRetry) await payload.onRetry({ attempt, delayMs: 0, error });
      if (attempt < maxAttempts) await sleep(Math.min(7000, 1000 * attempt));
    }
  }
  throw lastError;
}

async function runFfmpeg(args) {
  await runShell(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", ...args].map(shellQuote).join(" "));
}

async function durationMs(filePath) {
  const command = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
    filePath,
  ].map(shellQuote).join(" ");
  const { stdout } = await runShell(command);
  return Math.max(0, Math.round(Number(stdout.trim()) * 1000));
}

function syntheticTimestamps(text, offsetMs, chunkDurationMs) {
  const tokens = tokenizeWords(text);
  if (!tokens.length || chunkDurationMs <= 0) return [];
  const weights = tokens.map((token) => Math.max(1, token.length));
  const total = weights.reduce((sum, weight) => sum + weight, 0);
  let cursor = 0;
  return tokens.map((token, index) => {
    const start = offsetMs + Math.floor((cursor / total) * chunkDurationMs);
    cursor += weights[index];
    const end = index === tokens.length - 1
      ? offsetMs + chunkDurationMs
      : offsetMs + Math.floor((cursor / total) * chunkDurationMs);
    return { word: token, start_ms: start, end_ms: Math.max(start + 1, end) };
  });
}

async function normalizeToWav(source, destination) {
  await runFfmpeg(["-i", source, "-ar", "22050", "-ac", "1", destination]);
}

async function concatWavsToMp3(wavPaths, outputPath, tempDir) {
  const concatPath = path.join(tempDir, "concat.txt");
  const body = wavPaths.map((filePath) => `file '${path.resolve(filePath).replace(/'/g, "'\\''")}'`).join("\n");
  await fsp.writeFile(concatPath, `${body}\n`, "utf8");
  await runFfmpeg(["-f", "concat", "-safe", "0", "-i", concatPath, "-c:a", "libmp3lame", "-b:a", "64k", "-ac", "1", outputPath]);
  return durationMs(outputPath);
}

async function fileExistsWithBytes(filePath) {
  const stat = await fsp.stat(filePath).catch(() => null);
  return Boolean(stat && stat.isFile() && stat.size > 0);
}

function chunkProgressKey(index) {
  return String(index).padStart(5, "0");
}

function ensureChunkProgress(progress, slug) {
  progress.chunks = progress.chunks || {};
  progress.chunks[slug] = progress.chunks[slug] || {};
  return progress.chunks[slug];
}

async function saveChunkProgress({ progress, progressPath, slug, index, update }) {
  const key = chunkProgressKey(index);
  const chunks = ensureChunkProgress(progress, slug);
  chunks[key] = {
    ...(chunks[key] || {}),
    ...update,
    chunk_index: index,
    updated_at: new Date().toISOString(),
  };
  await saveProgress(progressPath, progress);
}

function formatVttTime(ms) {
  const total = Math.max(0, Number(ms) || 0);
  const hours = Math.floor(total / 3600000);
  const minutes = Math.floor((total % 3600000) / 60000);
  const seconds = Math.floor((total % 60000) / 1000);
  const millis = Math.floor(total % 1000);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

function buildVtt(timestamps) {
  const lines = ["WEBVTT", ""];
  timestamps.forEach((item, index) => {
    lines.push(String(index + 1));
    lines.push(`${formatVttTime(item.start_ms)} --> ${formatVttTime(item.end_ms)}`);
    lines.push(item.word || "");
    lines.push("");
  });
  return lines.join("\n");
}

function chapterIndex(markers, preparedText, timestamps) {
  if (!markers.length) return [{ title: "Full Text", start_ms: 0 }];
  return markers.map((marker) => {
    const before = preparedText.slice(0, Math.max(0, Number(marker.char_index) || 0));
    const wordIndex = Math.min(tokenizeWords(before).length, Math.max(0, timestamps.length - 1));
    return {
      title: marker.title || "Chapter",
      start_ms: timestamps[wordIndex]?.start_ms || 0,
    };
  });
}

async function generateBundle({ book, prepared, provider, args, progress, progressPath }) {
  if (!commandExists("ffmpeg") || !commandExists("ffprobe")) {
    throw new Error("ffmpeg and ffprobe are required for --commit audio polishing.");
  }
  if (!provider.configured) {
    await provider.synthesize({});
  }

  const slug = normalizeSlug(book.slug || book.title || "book");
  const bundleDir = path.join(args.jobDir, "bundles", "ben", slug);
  const tempDir = path.join(bundleDir, "_work");
  const chunks = chunkText(prepared.normalizedText, args.chunkChars);
  const wavPaths = [];
  const timestamps = [];
  let offsetMs = 0;

  await ensureDir(bundleDir);
  await ensureDir(tempDir);
  try {
    for (let index = 0; index < chunks.length; index += 1) {
      const chunk = chunks[index];
      const ssml = buildBengaliSsml(chunk, args.lexiconMap, {
        rate: args.ttsRate,
        pitch: args.ttsPitch,
        pauseProfile: args.pauseProfile,
      });
      const chunkHash = sha256Short(`${provider.supportsSsml ? ssml : chunk}\n${provider.voice || ""}`);
      const key = chunkProgressKey(index);
      const inputPath = path.join(tempDir, `chunk_${key}_${chunkHash}.${provider.supportsSsml ? "ssml" : "txt"}`);
      const rawOutput = path.join(tempDir, `chunk_${key}_${chunkHash}.${process.env.BENGALI_TTS_OUTPUT_FORMAT || "mp3"}`);
      const wavPath = path.join(tempDir, `chunk_${key}_${chunkHash}.wav`);
      await fsp.writeFile(inputPath, provider.supportsSsml ? ssml : chunk, "utf8");
      const savedChunk = progress?.chunks?.[slug]?.[key] || {};
      const rawExists = await fileExistsWithBytes(rawOutput);
      const wavExists = await fileExistsWithBytes(wavPath);
      const cacheMatches = savedChunk.chunk_hash === chunkHash
        && !args.forceRegenerate
        && rawExists
        && wavExists;
      const hasRawOutput = cacheMatches || (!args.forceRegenerate && rawExists);
      const hasWavOutput = cacheMatches || (!args.forceRegenerate && wavExists);
      if (cacheMatches) {
        await saveChunkProgress({
          progress,
          progressPath,
          slug,
          index,
          update: {
            book_slug: slug,
            chunk_hash: chunkHash,
            output_path: rawOutput,
            wav_path: wavPath,
            status: "SKIPPED_CACHE",
            attempts: Number(savedChunk.attempts || 0),
            total_chunks: chunks.length,
            last_error: "",
            retry_delay_ms: 0,
          },
        });
      }
      if (!hasRawOutput) {
        await saveChunkProgress({
          progress,
          progressPath,
          slug,
          index,
          update: {
            book_slug: slug,
            chunk_hash: chunkHash,
            input_path: inputPath,
            output_path: rawOutput,
            wav_path: wavPath,
            status: "SYNTHESIZING",
            attempts: 0,
            total_chunks: chunks.length,
            last_error: "",
            retry_delay_ms: 0,
          },
        });
        const ttsResult = await synthesizeWithRetry(provider, {
          inputText: chunk,
          ssml,
          inputPath,
          outputPath: rawOutput,
          index,
          slug,
          onAttempt: (attempt) => saveChunkProgress({
            progress,
            progressPath,
            slug,
            index,
            update: { status: "SYNTHESIZING", attempts: attempt, total_chunks: chunks.length, last_error: "", retry_delay_ms: 0 },
          }),
          onRetry: ({ attempt, retryAttempt, delayMs, error }) => saveChunkProgress({
            progress,
            progressPath,
            slug,
            index,
            update: {
              status: isTtsQuotaError(error) ? "RETRYING_429" : "RETRYING",
              attempts: attempt,
              retry_attempts: retryAttempt || 0,
              total_chunks: chunks.length,
              last_error: error.message || String(error),
              retry_delay_ms: delayMs,
            },
          }),
          onSuccess: (attempt) => saveChunkProgress({
            progress,
            progressPath,
            slug,
            index,
            update: { status: "AUDIO_READY", attempts: attempt, total_chunks: chunks.length, last_error: "", retry_delay_ms: 0 },
          }),
        }, args);
        if (ttsResult?.ttsMeta) {
          progress.tts = {
            ...(progress.tts || {}),
            provider: args.ttsProvider,
            voice: ttsResult.ttsMeta.voice || provider.voice || "",
            region: ttsResult.ttsMeta.region || progress.tts?.region || process.env.AZURE_SPEECH_REGION || "",
            fallbackRegionUsed: ttsResult.ttsMeta.fallbackRegionUsed || progress.tts?.fallbackRegionUsed || "",
          };
          await saveChunkProgress({
            progress,
            progressPath,
            slug,
            index,
            update: {
              tts_meta: ttsResult.ttsMeta,
              region: ttsResult.ttsMeta.region || "",
              fallback_region_used: ttsResult.ttsMeta.fallbackRegionUsed || "",
            },
          });
        }
      }
      if (!hasWavOutput) {
        await normalizeToWav(rawOutput, wavPath);
      }
      await saveChunkProgress({
        progress,
        progressPath,
        slug,
        index,
        update: {
          book_slug: slug,
          chunk_hash: chunkHash,
          input_path: inputPath,
          output_path: rawOutput,
          wav_path: wavPath,
          status: hasRawOutput && hasWavOutput ? "SKIPPED_CACHE" : "COMPLETED",
          attempts: Number(progress?.chunks?.[slug]?.[key]?.attempts || 0),
          total_chunks: chunks.length,
          last_error: "",
          retry_delay_ms: 0,
        },
      });
      const chunkDuration = await durationMs(wavPath);
      timestamps.push(...syntheticTimestamps(chunk, offsetMs, chunkDuration));
      wavPaths.push(wavPath);
      offsetMs += chunkDuration;
      process.stdout.write(`${slug}: ${hasRawOutput && hasWavOutput ? "reused" : "synthesized"} ${index + 1}/${chunks.length} chunks\n`);
      if (args.ttsRequestDelayMs > 0 && index < chunks.length - 1 && !hasRawOutput) {
        await sleep(args.ttsRequestDelayMs);
      }
    }

    const mp3Path = path.join(bundleDir, `${slug}.mp3`);
    const finalDuration = await concatWavsToMp3(wavPaths, mp3Path, tempDir);
    const chapters = chapterIndex(prepared.chapterMarkers, prepared.normalizedText, timestamps);
    const meta = {
      slug,
      title: book.title || slug,
      author: book.author || "",
      language: "ben",
      provider_used: provider.name,
      voice: provider.voice,
      duration_ms: finalDuration,
      size: (await fsp.stat(mp3Path)).size,
      mime_type: "audio/mpeg",
      total_words: prepared.wordCount,
      highlight_available: timestamps.length > 0,
      chapters: chapters.length,
      generated_at: new Date().toISOString(),
      qa_threshold: args.qaThreshold,
      source_text_modified: false,
      text_preparation: {
        punctuation_normalized: true,
        ssml_profile_used: prepared.ssmlStats.ssmlProfileUsed,
        rate_used: prepared.ssmlStats.rateUsed,
        pitch_used: prepared.ssmlStats.pitchUsed,
        pause_profile_used: prepared.ssmlStats.pauseProfileUsed,
        total_inserted_pauses: prepared.ssmlStats.totalInsertedPauses,
        average_pause_ms: prepared.ssmlStats.averagePauseMs,
        max_pause_ms: prepared.ssmlStats.maxPauseMs,
        hyphen_minus_normalization_applied: prepared.ssmlStats.hyphenMinusNormalizationApplied,
        ssml_pause_markers: provider.supportsSsml,
        mixed_english_terms: prepared.englishTerms.slice(0, 50),
        lexicon_coverage: Number(prepared.lexiconCoverage.toFixed(4)),
      },
    };
    const files = {
      mp3: mp3Path,
      timestamps: path.join(bundleDir, `${slug}_timestamps.json`),
      vtt: path.join(bundleDir, `${slug}_highlight.vtt`),
      chapters: path.join(bundleDir, `${slug}_chapters.json`),
      meta: path.join(bundleDir, `${slug}_meta.json`),
    };
    await writeJson(files.timestamps, timestamps);
    await fsp.writeFile(files.vtt, buildVtt(timestamps), "utf8");
    await writeJson(files.chapters, chapters);
    await writeJson(files.meta, meta);
    await fsp.rm(tempDir, { recursive: true, force: true }).catch(() => {});
    return { files, meta, timestamps, durationMs: finalDuration, bundleDir };
  } catch (error) {
    error.partial_bundle_dir = bundleDir;
    error.partial_work_dir = tempDir;
    throw error;
  }
}

async function loadCachedBundle(slug, args) {
  const bundleDir = path.join(args.jobDir, "bundles", "ben", slug);
  const files = {
    mp3: path.join(bundleDir, `${slug}.mp3`),
    timestamps: path.join(bundleDir, `${slug}_timestamps.json`),
    vtt: path.join(bundleDir, `${slug}_highlight.vtt`),
    chapters: path.join(bundleDir, `${slug}_chapters.json`),
    meta: path.join(bundleDir, `${slug}_meta.json`),
  };
  const exists = await Promise.all(Object.values(files).map((filePath) => fileExistsWithBytes(filePath)));
  if (!exists.every(Boolean)) return null;
  const meta = JSON.parse(await fsp.readFile(files.meta, "utf8"));
  const timestamps = JSON.parse(await fsp.readFile(files.timestamps, "utf8"));
  if (!Array.isArray(timestamps) || !timestamps.length) return null;
  return {
    files,
    meta,
    timestamps,
    durationMs: Number(meta.duration_ms || 0),
    bundleDir,
    reusedFromCache: true,
  };
}

async function uploadBundle({ slug, bundle, provider, args, generatedScore }) {
  const fileNamePrefix = `${slug}-${safeFileName(args.jobId, "polished")}`;
  const assets = {};
  const providers = {};
  const uploadPlan = [
    ["mp3", bundle.files.mp3, `${fileNamePrefix}.mp3`, bundle.durationMs],
    ["timestamps", bundle.files.timestamps, `${fileNamePrefix}_timestamps.json`, 0],
    ["vtt", bundle.files.vtt, `${fileNamePrefix}_highlight.vtt`, 0],
    ["chapters", bundle.files.chapters, `${fileNamePrefix}_chapters.json`, 0],
    ["meta", bundle.files.meta, `${fileNamePrefix}_meta.json`, 0],
  ];

  let mp3Upload = null;
  for (const [assetKind, filePath, fileName, duration] of uploadPlan) {
    const publicId = `${args.storageFolder}/ben/${slug}/${fileName}`;
    const result = await withTransientNetworkRetry(`upload ${assetKind} for ${slug}`, () => uploadAudiobook({
      filePath,
      slug,
      language: "ben",
      folder: args.storageFolder,
      cloudinaryFolder: args.storageFolder,
      publicId,
      assetKind,
      fileName,
      duration,
    }));
    assets[assetKind] = result.url;
    providers[assetKind] = result.provider;
    if (assetKind === "mp3") mp3Upload = result;
  }

  return {
    assets,
    provider: mp3Upload?.provider || providers.mp3 || "",
    asset_providers: providers,
    size: mp3Upload?.size || bundle.meta.size || 0,
    duration_ms: mp3Upload?.duration || bundle.durationMs || 0,
    voice: `${provider.name}:${provider.voice || "default"}`.slice(0, 120),
    qa: generatedScore,
  };
}

function rowBase(book, current) {
  return {
    book_slug: book.slug || "",
    title: book.title || "",
    language: "ben",
    current_provider: current.provider || "",
    current_audio_url: current.url || "",
    current_audio_provider: current.provider || "",
    duration: current.duration_ms || 0,
    detected_issues: [],
    clarity_score: 0,
    pronunciation_score: 0,
    expression_score: 0,
    pacing_score: 0,
    punctuation_pause_score: 0,
    mixed_bengali_english_handling_score: 0,
    overall_score: 0,
    recommendation: "needs manual review",
    status: "PENDING",
  };
}

function previewText(value, limit = 1200) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function redactSecrets(value) {
  let output = String(value || "");
  for (const [key, secret] of Object.entries(process.env)) {
    if (!secret || secret.length < 4) continue;
    if (!/(KEY|SECRET|PASSWORD|TOKEN|CREDENTIAL|PRIVATE)/i.test(key)) continue;
    output = output.replaceAll(secret, "[redacted]");
  }
  return output;
}

function verboseDebugPayload({ slug, prepared, args, provider }) {
  return {
    slug,
    mode: args.dryRun ? "dry-run" : "commit",
    provider: provider.name,
    supportsSsml: provider.supportsSsml,
    ttsCommand: redactSecrets(process.env.BENGALI_TTS_COMMAND || ""),
    normalizedTextPreview: previewText(prepared.normalizedText),
    ssmlPreview: previewText(prepared.ssml),
    pauseDistribution: {
      averagePauseMs: prepared.ssmlStats.averagePauseMs,
      maxPauseMs: prepared.ssmlStats.maxPauseMs,
      pausesOver650ms: prepared.ssmlStats.pausesOver650ms,
      totalInsertedPauses: prepared.ssmlStats.totalInsertedPauses,
    },
    lexiconReplacementCount: prepared.ssmlStats.lexiconReplacementCount,
    lexiconReplacementTerms: prepared.ssmlStats.lexiconReplacementTerms,
    hyphenDashNormalizationCount: prepared.ssmlStats.hyphenMinusNormalizationCount,
    chunkStats: prepared.chunkStats,
    expression: {
      dialogueSegmentsDetected: prepared.ssmlStats.dialogueSegmentsDetected,
      prosodyProfileCounts: prepared.ssmlStats.prosodyProfileCounts,
      roboticFlatnessRisk: prepared.ssmlStats.roboticFlatnessRisk,
    },
  };
}

async function processBook({ summary, client, args, provider, progress, progressPath }) {
  const slug = normalizeSlug(summary.slug || "");
  const book = await client.book(slug);
  const current = currentAudioInfo(book);
  const row = rowBase(book, current);

  if (!isBengaliBook(book)) {
    row.status = "SKIPPED";
    row.recommendation = "needs manual review";
    row.detected_issues = ["book does not look Bengali from metadata/title/description"];
    return row;
  }

  const prepared = prepareNarration(book, args.lexiconMap, args);
  row.prepared_text = {
    character_count: prepared.characterCount,
    word_count: prepared.wordCount,
    english_terms: prepared.englishTerms.slice(0, 50),
    lexicon_coverage: Number(prepared.lexiconCoverage.toFixed(4)),
    lexicon_coverage_unique: Number(prepared.lexiconCoverageUnique.toFixed(4)),
    lexicon_occurrences: prepared.lexiconOccurrences,
    mixed_language_density: Number(mixedLanguageStats(prepared).density.toFixed(6)),
    mixed_language_incidental: mixedLanguageStats(prepared).isIncidental,
    chunk_stats: prepared.chunkStats,
    ssml_stats: prepared.ssmlStats,
  };
  Object.assign(row, {
    ssmlProfileUsed: prepared.ssmlStats.ssmlProfileUsed,
    rateUsed: prepared.ssmlStats.rateUsed,
    pitchUsed: prepared.ssmlStats.pitchUsed,
    pauseProfileUsed: prepared.ssmlStats.pauseProfileUsed,
    averagePauseMs: prepared.ssmlStats.averagePauseMs,
    maxPauseMs: prepared.ssmlStats.maxPauseMs,
    pausesOver650ms: prepared.ssmlStats.pausesOver650ms,
    totalInsertedPauses: prepared.ssmlStats.totalInsertedPauses,
    estimatedWordsPerMinute: prepared.ssmlStats.estimatedWordsPerMinute,
    dialogueSegmentsDetected: prepared.ssmlStats.dialogueSegmentsDetected,
    hyphenMinusNormalizationApplied: prepared.ssmlStats.hyphenMinusNormalizationApplied,
    unsafeHyphenDashRemaining: prepared.ssmlStats.unsafeHyphenDashRemaining,
    mixedLanguageTermsNormalized: prepared.ssmlStats.mixedLanguageTermsNormalized,
    roboticFlatnessRisk: prepared.ssmlStats.roboticFlatnessRisk,
  });
  const preparedDir = path.join(args.jobDir, "prepared", slug);
  await ensureDir(preparedDir);
  await fsp.writeFile(path.join(preparedDir, `${slug}.txt`), prepared.normalizedText, "utf8");
  await fsp.writeFile(path.join(preparedDir, `${slug}.ssml`), prepared.ssml, "utf8");
  if (args.verbose) {
    const debug = verboseDebugPayload({ slug, prepared, args, provider });
    await writeJson(path.join(preparedDir, `${slug}_debug.json`), debug);
    process.stdout.write(`Verbose debug: ${JSON.stringify({
      normalizedTextPreview: debug.normalizedTextPreview,
      pauseDistribution: debug.pauseDistribution,
      lexiconReplacementCount: debug.lexiconReplacementCount,
      hyphenDashNormalizationCount: debug.hyphenDashNormalizationCount,
      chunkStats: debug.chunkStats,
      ttsCommand: debug.ttsCommand,
    }, null, 2)}\n`);
  }

  const audit = await auditCurrentAudio(book, args.apiUrl);
  row.current_audio_audit = audit;
  Object.assign(row, scoreCurrentAudiobook(book, prepared, audit, args.qaThreshold));
  row.regeneration_readiness = scoreRegenerationReadiness({ provider, prepared });
  row.regeneration_readiness_score = row.regeneration_readiness.overall_score;
  row.target_regenerated_score = row.regeneration_readiness.overall_score;
  row.detected_issues = Array.from(new Set([...(row.detected_issues || []), ...(audit.issues || [])]));

  if (args.dryRun) {
    row.status = "DRY_RUN";
    return row;
  }

  if (row.recommendation === "keep" && !args.forceRegenerate) {
    row.status = "READY";
    row.detail = "current audiobook passes configured QA threshold; no regeneration needed";
    return row;
  }

  const cachedBundle = args.forceRegenerate ? null : await loadCachedBundle(slug, args);
  if (cachedBundle) {
    process.stdout.write(`${slug}: reused existing generated bundle at ${cachedBundle.bundleDir}\n`);
  }
  const bundle = cachedBundle || await generateBundle({ book, prepared, provider, args, progress, progressPath });
  const generatedScore = scoreGeneratedBundle({
    provider,
    prepared,
    durationMs: bundle.durationMs,
    timestamps: bundle.timestamps,
    supportsSsml: provider.supportsSsml,
    humanReviewed: args.humanReviewed,
    threshold: args.qaThreshold,
  });
  row.generated_bundle = {
    path: bundle.bundleDir,
    duration_ms: bundle.durationMs,
    size: bundle.meta.size,
    timestamp_count: bundle.timestamps.length,
    provider: provider.name,
    voice: provider.voice,
    reused_from_cache: Boolean(bundle.reusedFromCache),
  };
  row.generated_qa = generatedScore;

  if (generatedScore.overall_score < args.qaThreshold && !args.allowReviewCommit) {
    row.status = "NEEDS_MANUAL_REVIEW";
    row.recommendation = "needs manual review";
    row.detected_issues = Array.from(new Set([...(row.detected_issues || []), ...generatedScore.detected_issues]));
    row.detail = `generated bundle held back by QA gate: ${generatedScore.overall_score}/${args.qaThreshold}`;
    return row;
  }

  const upload = await uploadBundle({ slug, bundle, provider, args, generatedScore });
  await withTransientNetworkRetry(`patch audiobook ${slug}`, () => client.patchAudiobook(slug, {
    audiobook_enabled: true,
    generate_audiobook: true,
    audiobook_provider: upload.provider,
    audiobook_voice: upload.voice,
    audio_asset_slug: slug,
    audiobook_assets: upload.assets,
    audiobook_size: upload.size,
    audiobook_duration_ms: upload.duration_ms,
  }));

  row.status = "READY";
  row.recommendation = generatedScore.overall_score >= args.qaThreshold ? "keep" : "needs manual review";
  row.uploaded = {
    provider: upload.provider,
    asset_providers: upload.asset_providers,
    duration_ms: upload.duration_ms,
    size: upload.size,
    assets: upload.assets,
  };
  row.detail = "polished audiobook uploaded and admin audiobook fields updated";
  return row;
}

function hasAudiobook(summary) {
  return currentAudioInfo(summary).enabled;
}

function queueItemsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of ["books", "items", "targets", "queue"]) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  if (Array.isArray(payload.slugs)) return payload.slugs;
  return [];
}

function slugFromQueueItem(item) {
  if (typeof item === "string") return normalizeSlug(item);
  if (!item || typeof item !== "object") return "";
  return normalizeSlug(item.slug || item.book_slug || item.id || item.bookSlug || item.book_id || "");
}

function loadQueueSlugs(filePath) {
  if (!filePath) return [];
  if (!fs.existsSync(filePath)) throw new Error(`Queue manifest not found: ${filePath}`);
  const payload = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const slugs = [];
  const seen = new Set();
  for (const item of queueItemsFromPayload(payload)) {
    const slug = slugFromQueueItem(item);
    if (!slug || seen.has(slug)) continue;
    seen.add(slug);
    slugs.push(slug);
  }
  if (!slugs.length) throw new Error(`Queue manifest did not contain any slugs: ${filePath}`);
  return slugs;
}

function shuffle(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swap]] = [copy[swap], copy[index]];
  }
  return copy;
}

function selectSummaries(summaries, args) {
  const bySlug = new Map(summaries.map((item) => [normalizeSlug(item.slug || ""), item]));
  const queueSlugs = args.manifest ? loadQueueSlugs(args.manifest) : [];
  const requested = [];
  const seen = new Set();
  for (const slug of [...queueSlugs, ...args.slug]) {
    const normalized = normalizeSlug(slug);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    requested.push(normalized);
  }
  let selected = [];
  if (requested.length) {
    selected = requested.map((slug) => bySlug.get(slug) || { slug }).filter((item) => item.slug);
  } else {
    const bengaliAudiobooks = summaries.filter((item) => isBengaliBook(item) && hasAudiobook(item));
    if (args.sample > 0) selected = shuffle(bengaliAudiobooks).slice(0, args.sample);
    else if (args.allBengali) selected = bengaliAudiobooks;
    else throw new Error("Choose --sample N, --slug book-slug, --manifest PATH, or --all-bengali.");
  }

  if (args.startAfter) {
    const startIndex = selected.findIndex((item) => normalizeSlug(item.slug || item.id || "") === args.startAfter);
    if (startIndex >= 0) selected = selected.slice(startIndex + 1);
  }
  if (args.maxBooks > 0) selected = selected.slice(0, args.maxBooks);
  return selected;
}

async function audioHeadSizeBytes(book, apiUrl) {
  const audio = currentAudioInfo(book);
  if (!audio.url) return 0;
  try {
    const response = await fetchWithRetry(resolveAssetUrl(audio.url, apiUrl), { method: "HEAD" }, 2);
    return Number(response.headers.get("content-length") || audio.size || 0) || 0;
  } catch (_error) {
    return Number(audio.size || 0) || 0;
  }
}

async function buildBengaliAudiobookQueue({ client, summaries, args }) {
  const selectionArgs = {
    ...args,
    allBengali: args.allBengali || (!args.slug.length && !args.manifest && !args.sample),
    sample: args.sample,
  };
  const selected = selectSummaries(summaries, selectionArgs);
  const rows = [];

  for (let index = 0; index < selected.length; index += 1) {
    const summary = selected[index];
    const slug = normalizeSlug(summary.slug || "");
    if (!slug) continue;
    process.stdout.write(`queue ${index + 1}/${selected.length}: ${slug}\n`);
    const book = await client.book(slug);
    if (!isBengaliBook(book)) continue;
    const current = currentAudioInfo(book);
    const prepared = prepareNarration(book, args.lexiconMap, args);
    const currentAudioSizeBytes = await audioHeadSizeBytes(book, args.apiUrl);
    rows.push({
      sequence: 0,
      slug,
      title: book.title || summary.title || slug,
      author: book.author || summary.author || "",
      language: "ben",
      generation_size_chars: prepared.characterCount,
      word_count: prepared.wordCount,
      estimated_chunks: prepared.chunkStats.chunkCount,
      current_audio_size_bytes: currentAudioSizeBytes || current.size || 0,
      current_provider: current.provider || "",
      current_audio_url: current.url || "",
      queue_command_slug_arg: `--slug ${slug}`,
    });
  }

  const sorters = {
    "generation-size": (left, right) => left.generation_size_chars - right.generation_size_chars,
    "current-audio-size": (left, right) => left.current_audio_size_bytes - right.current_audio_size_bytes,
    slug: (left, right) => left.slug.localeCompare(right.slug),
  };
  rows.sort((left, right) => sorters[args.queueSort](left, right) || left.slug.localeCompare(right.slug));
  rows.forEach((row, index) => {
    row.sequence = index + 1;
  });

  return {
    generated_at: new Date().toISOString(),
    queue_type: "bengali-audiobook-regeneration",
    sort: args.queueSort,
    sort_size_field: args.queueSort === "current-audio-size" ? "current_audio_size_bytes" : "generation_size_chars",
    total: rows.length,
    slugs: rows.map((row) => row.slug),
    books: rows,
  };
}

async function loadProgress(progressPath, resume) {
  if (!resume || !fs.existsSync(progressPath)) return { completed: {}, failed: {}, updated_at: "" };
  return JSON.parse(await fsp.readFile(progressPath, "utf8"));
}

async function saveProgress(progressPath, progress) {
  progress.updated_at = new Date().toISOString();
  await writeJson(progressPath, progress);
}

function chunkProgressSummary(progress, failed) {
  const rows = Object.values(progress.chunks || {}).flatMap((bookChunks) => Object.values(bookChunks || {}));
  const completedStatuses = new Set(["COMPLETED", "SKIPPED_CACHE", "AUDIO_READY"]);
  const chunksCompleted = rows.filter((row) => completedStatuses.has(row.status)).length;
  const chunksSkippedFromCache = rows.filter((row) => row.status === "SKIPPED_CACHE").length;
  const quotaRows = rows.filter((row) => row.status === "RETRYING_429");
  const paused = failed.find((row) => row.status === "PAUSED_QUOTA") || {};
  const pausedSlug = paused.book_slug || "";
  const pausedChunks = pausedSlug ? Object.values(progress.chunks?.[pausedSlug] || {}) : [];
  const totalChunks = Math.max(0, ...pausedChunks.map((row) => Number(row.total_chunks || 0)));
  const pausedCompleted = pausedChunks.filter((row) => completedStatuses.has(row.status)).length;
  const lastQuotaChunk = quotaRows[quotaRows.length - 1] || pausedChunks.find((row) => row.status === "RETRYING_429") || {};
  return {
    chunksCompleted,
    chunksSkippedFromCache,
    chunksRemaining: totalChunks ? Math.max(0, totalChunks - pausedCompleted) : 0,
    fallbackRegionUsed: progress.tts?.fallbackRegionUsed || rows.map((row) => row.fallback_region_used).filter(Boolean).pop() || "",
    quotaPausedAtBook: pausedSlug,
    quotaPausedAtChunk: Number(paused.quota_paused_at_chunk ?? lastQuotaChunk.chunk_index ?? -1),
    retryAttempts: Number(paused.retry_attempts || lastQuotaChunk.retry_attempts || 0),
    retryDelayMs: Number(paused.retry_delay_ms || lastQuotaChunk.retry_delay_ms || 0),
  };
}

function nextResumeCommand(args) {
  const parts = [
    "railway run --service earnalism --environment production -- \\",
    "  npm run audiobook:bengali:polish -- \\",
  ];
  if (args.manifest) parts.push(`  --manifest ${path.relative(ROOT, args.manifest)} \\`);
  for (const slug of args.slug || []) parts.push(`  --slug ${slug} \\`);
  if (args.allBengali) parts.push("  --all-bengali \\");
  parts.push(`  --job-id ${args.jobId} \\`);
  parts.push("  --resume \\");
  if (args.commit) parts.push("  --commit \\");
  parts.push(`  --concurrency ${args.concurrency} \\`);
  if (args.envFile?.length) parts.push(`  --env-file ${path.relative(ROOT, path.resolve(ROOT, args.envFile[0]))}`);
  else parts.push("  --env-file .secrets/earnalism-import.env");
  return parts.join("\n").replace(/ \\$/m, "");
}

async function writeReport(args, progress, selected) {
  const rows = Object.values(progress.completed || {});
  const failed = Object.values(progress.failed || {});
  const chunkSummary = chunkProgressSummary(progress, failed);
  const report = {
    generated_at: new Date().toISOString(),
    job_id: args.jobId,
    mode: args.dryRun ? "dry-run" : "commit",
    qa_threshold: args.qaThreshold,
    ttsProvider: args.ttsProvider,
    voice: progress.tts?.voice || process.env.BENGALI_TTS_VOICE_ID || process.env.AZURE_BENGALI_VOICE || "",
    region: progress.tts?.region || process.env.AZURE_SPEECH_REGION || "",
    fallbackRegionUsed: chunkSummary.fallbackRegionUsed || "",
    quotaPausedAtBook: chunkSummary.quotaPausedAtBook || "",
    quotaPausedAtChunk: chunkSummary.quotaPausedAtChunk >= 0 ? chunkSummary.quotaPausedAtChunk : "",
    retryAttempts: chunkSummary.retryAttempts,
    retryDelayMs: chunkSummary.retryDelayMs,
    chunksCompleted: chunkSummary.chunksCompleted,
    chunksSkippedFromCache: chunkSummary.chunksSkippedFromCache,
    chunksRemaining: chunkSummary.chunksRemaining,
    nextResumeCommand: nextResumeCommand(args),
    selected: selected.map((item) => item.slug),
    summary: {
      selected: selected.length,
      completed: rows.length,
      failed: failed.length,
      ready: rows.filter((row) => row.status === "READY").length,
      dry_run: rows.filter((row) => row.status === "DRY_RUN").length,
      needs_manual_review: rows.filter((row) => row.status === "NEEDS_MANUAL_REVIEW" || row.recommendation === "needs manual review").length,
      quota_paused: failed.filter((row) => row.status === "PAUSED_QUOTA").length,
    },
    books: rows,
    failed,
  };
  await writeJson(path.join(args.jobDir, REPORT_FILE), report);
  return report;
}

async function runPool(items, concurrency, worker, shouldStop = () => false) {
  let cursor = 0;
  const workers = Array.from({ length: Math.max(1, concurrency) }, async () => {
    while (cursor < items.length && !shouldStop()) {
      const index = cursor;
      cursor += 1;
      await worker(items[index], index);
    }
  });
  await Promise.all(workers);
}

function assertSelfTest(condition, message, details = {}) {
  if (!condition) {
    const suffix = Object.keys(details).length ? ` ${JSON.stringify(details)}` : "";
    throw new Error(`Self-test failed: ${message}${suffix}`);
  }
}

async function runNormalizationSelfTest(args) {
  const lexicon = args.lexiconMap || await loadLexicon(args.lexicon);
  const normalize = (value) => normalizeBengaliTtsText(value, { lexicon }).text;
  const ssmlFor = (value) => buildBengaliSsmlDocument(normalize(value), lexicon, {
    rate: args.ttsRate,
    pitch: args.ttsPitch,
    pauseProfile: args.pauseProfile,
  }).ssml;

  const cases = [
    ["জ্ঞান-চর্চা", "জ্ঞান চর্চা"],
    ["self-help", "self help"],
    ["AI-ভিত্তিক বই", "এ আই ভিত্তিক বই"],
    ["১৯০১-১৯০৫", "১৯০১ থেকে ১৯০৫"],
    ["10-12 minutes", "10 থেকে 12 minutes"],
    ["-৫ ডিগ্রি", "ঋণাত্মক ৫ ডিগ্রি"],
  ];

  for (const [input, expected] of cases) {
    const actual = normalize(input);
    assertSelfTest(actual === expected, "normalization example mismatch", { input, expected, actual });
  }

  const dashSsml = ssmlFor("সে বলল — আমি যাব না");
  assertSelfTest(dashSsml.includes('<break time="180ms"/>'), "em dash should become 180ms break", { dashSsml });
  const defaultSsml = ssmlFor("সে বলল।");
  const mixedSsmlDocument = buildBengaliSsmlDocument(normalize("সে বলল Magistrate আসবেন।"), lexicon, {
    rate: args.ttsRate,
    pitch: args.ttsPitch,
    pauseProfile: args.pauseProfile,
  });
  assertSelfTest(defaultSsml.includes('rate="+3%"'), "default narration should use +3% rate", { defaultSsml });
  assertSelfTest(defaultSsml.includes('pitch="+1Hz"'), "default narration should use +1Hz pitch", { defaultSsml });
  assertSelfTest(
    mixedSsmlDocument.stats.mixedLanguageTermsLanguageMarked > 0,
    "English terms without lexicon aliases should be language-marked in SSML",
    { mixedSsml: mixedSsmlDocument.ssml },
  );
  assertSelfTest(!defaultSsml.includes('rate="-8%"'), "old slow -8% rate must not be default", { defaultSsml });
  assertSelfTest(!/<break time="\d+ms"\/>\s*<break time="\d+ms"\/>/.test(dashSsml), "duplicate consecutive breaks should be collapsed", { dashSsml });
  assertSelfTest(!/[-–—−]/.test(stripSsmlTags(dashSsml)), "unsafe dash should not remain in SSML text", { dashSsml });
  const interpolated = interpolateTtsCommand('node tts.js --input "{input}" --output "{output}"', {
    input: "/tmp/input one.ssml",
    output: "/tmp/output one.mp3",
  });
  assertSelfTest(
    interpolated === "node tts.js --input '/tmp/input one.ssml' --output '/tmp/output one.mp3'",
    "quoted command placeholders should interpolate to one shell-quoted value",
    { interpolated },
  );
  assertSelfTest(
    isTtsQuotaError(new Error("Azure Bengali TTS failed: HTTP 429 Quota Exceeded")),
    "Azure HTTP 429 quota errors should be detected",
  );
  assertSelfTest(
    retryAfterMs(new Error("Azure Bengali TTS failed: HTTP 429 Quota Exceeded; retry_after=60")) === 60000,
    "Azure Retry-After seconds should be converted to milliseconds",
  );
  assertSelfTest(
    chunkText("এক। দুই। তিন। চার। পাঁচ।".repeat(1200), DEFAULT_CHUNK_CHARS).every((chunk) => chunk.length <= 4000),
    "quota-safe chunks should stay below Azure request target",
  );
  assertSelfTest(
    isTransientNetworkError(new Error("read ECONNRESET"))
      && isTransientNetworkError(new Error("AggregateError [ETIMEDOUT]"))
      && isTransientNetworkError(new Error("read EADDRNOTAVAIL")),
    "transient upload/admin network errors should be retried",
  );

  const report = {
    ok: true,
    checked: cases.length + 10,
    defaultRate: args.ttsRate,
    defaultPitch: args.ttsPitch,
    pauseProfile: args.pauseProfile,
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(usage());
    return;
  }
  const defaultEnv = path.join(ROOT, ".secrets", "earnalism-import.env");
  if (!args.envFile.length && fs.existsSync(defaultEnv)) args.envFile.push(defaultEnv);
  args.envFile.forEach(loadEnvFile);
  applyEnvDefaults(args);
  args.lexiconMap = await loadLexicon(args.lexicon);

  if (args.selfTestNormalization) {
    await runNormalizationSelfTest(args);
    return;
  }

  await ensureDir(args.jobDir);
  const progressPath = path.join(args.jobDir, PROGRESS_FILE);
  if (args.restart && fs.existsSync(progressPath)) await fsp.rm(progressPath, { force: true });
  const progress = await loadProgress(progressPath, args.resume);

  const client = new EarnalismAdminClient(args.apiUrl);
  await client.login();
  const summaries = await client.summaries();

  if (args.exportQueue) {
    const queue = await buildBengaliAudiobookQueue({ client, summaries, args });
    await writeJson(args.exportQueue, queue);
    process.stdout.write(`Bengali audiobook queue written: ${args.exportQueue}\n`);
    process.stdout.write(`Total: ${queue.total} | Sort: ${queue.sort} (${queue.sort_size_field})\n`);
    return;
  }

  const selected = selectSummaries(summaries, args);
  const provider = createTtsProvider(args.ttsProvider);

  process.stdout.write(`Bengali audiobook polish job: ${args.jobId}\n`);
  process.stdout.write(`Mode: ${args.dryRun ? "dry-run" : "commit"} | Selected: ${selected.length} | Concurrency: ${args.concurrency}\n`);
  process.stdout.write(`Report: ${path.join(args.jobDir, REPORT_FILE)}\n`);

  let stopRequested = false;
  let stopReason = "";

  await runPool(selected, args.concurrency, async (summary, index) => {
    if (stopRequested) return;
    const slug = normalizeSlug(summary.slug || "");
    const completedRow = progress.completed?.[slug];
    const shouldReprocessManualReview = completedRow?.status === "NEEDS_MANUAL_REVIEW" && args.allowReviewCommit;
    if (args.resume && !args.forceRegenerate && completedRow && !shouldReprocessManualReview) {
      process.stdout.write(`SKIP ${index + 1}/${selected.length}: ${slug} already completed in progress\n`);
      return;
    }
    process.stdout.write(`\n=== ${index + 1}/${selected.length} ${summary.title || slug} (${slug}) ===\n`);
    try {
      const row = await processBook({ summary, client, args, provider, progress, progressPath });
      progress.completed = progress.completed || {};
      progress.completed[slug] = row;
      delete progress.failed?.[slug];
      const readiness = row.regeneration_readiness_score
        ? ` | regeneration_readiness=${row.regeneration_readiness_score}`
        : "";
      process.stdout.write(`${row.status}: ${row.recommendation} | current_score=${row.overall_score}${readiness}\n`);
    } catch (error) {
      const quotaError = isTtsQuotaError(error);
      progress.failed = progress.failed || {};
      progress.failed[slug] = {
        book_slug: slug,
        title: summary.title || "",
        status: quotaError ? "PAUSED_QUOTA" : "BLOCKED",
        detail: error.stack || error.message || String(error),
        partial_bundle_dir: error.partial_bundle_dir || "",
        partial_work_dir: error.partial_work_dir || "",
        quota_paused_at_chunk: Number.isInteger(error.chunk_index) ? error.chunk_index : "",
        retry_attempts: Number(error.retry_attempts || 0),
        retry_delay_ms: Number(error.retry_delay_ms || 0),
        updated_at: new Date().toISOString(),
      };
      process.stderr.write(`${quotaError ? "PAUSED_QUOTA" : "BLOCKED"} ${slug}: ${error.message}\n`);
      if (quotaError && args.stopOnQuota) {
        stopRequested = true;
        stopReason = `Azure TTS quota/rate limit hit at ${slug}. Resume the same job id after quota is restored; existing chunk files are preserved.`;
      }
    }
    await saveProgress(progressPath, progress);
    await writeReport(args, progress, selected);
  }, () => stopRequested);

  const report = await writeReport(args, progress, selected);
  process.stdout.write("\nBengali audiobook polish summary\n");
  process.stdout.write("================================\n");
  process.stdout.write(`Selected: ${report.summary.selected}\n`);
  process.stdout.write(`Completed: ${report.summary.completed}\n`);
  process.stdout.write(`Failed: ${report.summary.failed}\n`);
  process.stdout.write(`Needs manual review: ${report.summary.needs_manual_review}\n`);
  process.stdout.write(`Report: ${path.join(args.jobDir, REPORT_FILE)}\n`);
  if (stopReason) process.stdout.write(`Paused: ${stopReason}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
