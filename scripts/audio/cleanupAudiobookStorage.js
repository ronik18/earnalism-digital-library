#!/usr/bin/env node

const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");
const cloudinary = require("cloudinary").v2;
const {
  DeleteObjectCommand,
  ListObjectsV2Command,
  S3Client,
} = require("@aws-sdk/client-s3");

const ROOT = path.resolve(__dirname, "../..");
const DEFAULT_API_URL = "https://api.theearnalism.com/api";
const DEFAULT_OUTPUT_ROOT = path.join(ROOT, "output", "audiobook_storage_cleanup");
const DEFAULT_PREFIXES = ["earnalism/audiobooks/", "earnalism/audiobooks-polished/"];
const DEFAULT_MIN_AGE_DAYS = 2;
const DEFAULT_DELETE_LIMIT = 100;
const AUDIOBOOK_EXTENSIONS = new Set([".mp3", ".m4a", ".ogg", ".wav", ".json", ".vtt"]);

function usage() {
  return `
Usage:
  node scripts/audio/cleanupAudiobookStorage.js
  node scripts/audio/cleanupAudiobookStorage.js --provider b2 --dry-run
  node scripts/audio/cleanupAudiobookStorage.js --commit-delete --min-age-days 7

Safety:
  --dry-run                  Report only; default
  --commit-delete            Delete orphaned storage objects
  --delete-limit N           Max objects to delete in one commit run; default ${DEFAULT_DELETE_LIMIT}
  --min-age-days N           Protect recent orphan uploads; default ${DEFAULT_MIN_AGE_DAYS}

Scope:
  --provider all|cloudinary|b2
  --prefix PREFIX            Storage prefix to scan; repeatable
  --job-id ID                Stable report folder
  --env-file PATH            Load local env file; repeatable
  --api-url URL              Backend API URL
`;
}

function parseArgs(argv) {
  const args = {
    apiUrl: process.env.EARNALISM_API_URL || DEFAULT_API_URL,
    envFile: [],
    outputDir: DEFAULT_OUTPUT_ROOT,
    jobId: "",
    provider: "all",
    prefixes: parsePrefixes(process.env.AUDIOBOOK_CLEANUP_PREFIXES || ""),
    dryRun: false,
    commitDelete: false,
    minAgeDays: Number(process.env.AUDIOBOOK_CLEANUP_MIN_AGE_DAYS || DEFAULT_MIN_AGE_DAYS),
    deleteLimit: Number(process.env.AUDIOBOOK_CLEANUP_DELETE_LIMIT || DEFAULT_DELETE_LIMIT),
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
    } else if (token === "--api-url") {
      args.apiUrl = readValue(token);
      args.explicit.apiUrl = true;
    } else if (token === "--env-file") {
      args.envFile.push(readValue(token));
    } else if (token === "--output-dir") {
      args.outputDir = path.resolve(readValue(token));
    } else if (token === "--job-id") {
      args.jobId = safeSegment(readValue(token), "cleanup");
    } else if (token === "--provider") {
      args.provider = readValue(token).toLowerCase();
    } else if (token === "--prefix") {
      args.prefixes.push(normalizePrefix(readValue(token)));
      args.explicit.prefixes = true;
    } else if (token === "--dry-run") {
      args.dryRun = true;
    } else if (token === "--commit-delete") {
      args.commitDelete = true;
    } else if (token === "--min-age-days") {
      args.minAgeDays = Math.max(0, Number(readValue(token)) || 0);
      args.explicit.minAgeDays = true;
    } else if (token === "--delete-limit") {
      args.deleteLimit = Math.max(1, Number.parseInt(readValue(token), 10) || DEFAULT_DELETE_LIMIT);
      args.explicit.deleteLimit = true;
    } else {
      throw new Error(`Unknown option: ${token}`);
    }
  }

  if (!["all", "cloudinary", "b2"].includes(args.provider)) {
    throw new Error("--provider must be one of: all, cloudinary, b2");
  }
  if (args.commitDelete && args.dryRun) {
    throw new Error("Use either --dry-run or --commit-delete, not both.");
  }
  args.dryRun = !args.commitDelete;
  args.prefixes = unique((args.explicit.prefixes ? args.prefixes : (args.prefixes.length ? args.prefixes : DEFAULT_PREFIXES)).map(normalizePrefix));
  args.apiUrl = normalizeApiUrl(args.apiUrl);
  args.jobId = args.jobId || new Date().toISOString().replace(/[:.]/g, "-");
  args.jobDir = path.join(args.outputDir, args.jobId);
  return args;
}

function applyEnvDefaults(args) {
  if (!args.explicit.apiUrl && process.env.EARNALISM_API_URL) {
    args.apiUrl = process.env.EARNALISM_API_URL;
  }
  if (!args.explicit.prefixes && process.env.AUDIOBOOK_CLEANUP_PREFIXES) {
    args.prefixes = parsePrefixes(process.env.AUDIOBOOK_CLEANUP_PREFIXES);
  }
  if (!args.explicit.minAgeDays && process.env.AUDIOBOOK_CLEANUP_MIN_AGE_DAYS) {
    args.minAgeDays = Math.max(0, Number(process.env.AUDIOBOOK_CLEANUP_MIN_AGE_DAYS) || args.minAgeDays);
  }
  if (!args.explicit.deleteLimit && process.env.AUDIOBOOK_CLEANUP_DELETE_LIMIT) {
    args.deleteLimit = Math.max(1, Number.parseInt(process.env.AUDIOBOOK_CLEANUP_DELETE_LIMIT, 10) || args.deleteLimit);
  }
  args.apiUrl = normalizeApiUrl(args.apiUrl);
  args.prefixes = unique((args.prefixes.length ? args.prefixes : DEFAULT_PREFIXES).map(normalizePrefix));
}

function parsePrefixes(value) {
  return String(value || "")
    .split(",")
    .map((item) => normalizePrefix(item))
    .filter(Boolean);
}

function normalizePrefix(value) {
  const prefix = String(value || "").trim().replace(/^\/+|\/+$/g, "");
  return prefix ? `${prefix}/` : "";
}

function unique(items) {
  return Array.from(new Set(items.filter(Boolean)));
}

function safeSegment(value, fallback) {
  const segment = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return segment || fallback;
}

function normalizeApiUrl(value) {
  const trimmed = String(value || DEFAULT_API_URL).replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

function loadEnvFile(filePath) {
  const resolved = path.resolve(ROOT, filePath);
  if (!fs.existsSync(resolved)) return;
  for (const raw of fs.readFileSync(resolved, "utf8").split(/\r?\n/)) {
    let line = raw.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    if (line.startsWith("export ")) line = line.slice("export ".length).trim();
    const separator = line.indexOf("=");
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
    if (key && process.env[key] === undefined) process.env[key] = value;
  }
}

async function ensureDir(dir) {
  await fsp.mkdir(dir, { recursive: true });
}

async function writeJson(filePath, data) {
  await ensureDir(path.dirname(filePath));
  await fsp.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function envValue(primary, aliases = []) {
  for (const name of [primary, ...aliases]) {
    const value = String(process.env[name] || "").trim();
    if (value) return value;
  }
  return "";
}

async function requestJson(method, url, { headers = {}, body } = {}) {
  const response = await fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${method} ${url} failed: HTTP ${response.status} ${text.slice(0, 300)}`);
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
      const data = await requestJson("POST", `${this.apiUrl}/auth/login`, { body: { email, password } });
      token = String(data.token || "").trim();
    }
    if (!token) throw new Error("Admin login did not return a token.");
    this.headers = { Authorization: `Bearer ${token}` };
  }

  summaries() {
    return requestJson("GET", `${this.apiUrl}/admin/books/summary`, { headers: this.headers });
  }
}

function normalizeUrl(url) {
  const value = String(url || "").trim();
  if (!value || value.startsWith("/")) return value;
  try {
    const parsed = new URL(value);
    parsed.hash = "";
    parsed.search = "";
    return parsed.href;
  } catch {
    return value;
  }
}

function valuesFromObject(value) {
  if (!value || typeof value !== "object") return [];
  return Object.values(value).flatMap((item) => {
    if (typeof item === "string") return [item];
    if (item && typeof item === "object") return valuesFromObject(item);
    return [];
  });
}

function collectReferencedAssets(books) {
  const urls = new Set();
  const b2Keys = new Set();
  const cloudinary = new Set();
  const byBook = [];

  for (const book of books) {
    const nested = book.audiobook && typeof book.audiobook === "object" ? book.audiobook : {};
    const values = [
      ...valuesFromObject(book.audiobook_assets),
      ...valuesFromObject(nested.assets),
      nested.url,
    ].filter(Boolean);
    const normalizedValues = [];
    for (const raw of values) {
      const url = normalizeUrl(raw);
      if (!url || url.startsWith("/")) continue;
      urls.add(url);
      normalizedValues.push(url);
      const b2Key = b2KeyFromUrl(url);
      if (b2Key) b2Keys.add(b2Key);
      const cloudinaryIdentity = cloudinaryIdentityFromUrl(url);
      if (cloudinaryIdentity) cloudinary.add(cloudinaryIdentity.key);
    }
    byBook.push({
      slug: book.slug || "",
      title: book.title || "",
      is_published: book.is_published !== false,
      referenced_urls: normalizedValues,
    });
  }

  return { urls, b2Keys, cloudinary, byBook };
}

function b2KeyFromUrl(url) {
  const bucket = envValue("B2_BUCKET");
  if (!bucket) return "";
  try {
    const parsed = new URL(url);
    if (!/backblazeb2\.com$/i.test(parsed.hostname) && !parsed.hostname.includes("backblazeb2.com")) return "";
    const parts = parsed.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    if (!parts.length) return "";
    if (parsed.hostname.startsWith(`${bucket}.`)) return parts.join("/");
    if (parts[0] === bucket) return parts.slice(1).join("/");
    return parts.join("/");
  } catch {
    return "";
  }
}

function cloudinaryIdentityFromUrl(url) {
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.includes("res.cloudinary.com")) return null;
    const parts = parsed.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    const uploadIndex = parts.indexOf("upload");
    if (uploadIndex < 2) return null;
    const resourceType = parts[uploadIndex - 1];
    let publicParts = parts.slice(uploadIndex + 1);
    if (publicParts[0] && /^v\d+$/.test(publicParts[0])) publicParts = publicParts.slice(1);
    if (!publicParts.length) return null;
    let publicId = publicParts.join("/");
    if (resourceType !== "raw") publicId = publicId.replace(/\.[a-z0-9]+$/i, "");
    return { resourceType, publicId, key: `${resourceType}:${publicId}` };
  } catch {
    return null;
  }
}

function isAllowedAudiobookObject(name) {
  const extension = path.extname(String(name || "").split("?")[0]).toLowerCase();
  return AUDIOBOOK_EXTENSIONS.has(extension);
}

function isOlderThan(value, minAgeDays) {
  if (minAgeDays <= 0) return true;
  const timestamp = new Date(value || 0).getTime();
  if (!timestamp) return false;
  const ageMs = Date.now() - timestamp;
  return ageMs >= minAgeDays * 24 * 60 * 60 * 1000;
}

function configureCloudinary() {
  const missing = ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"].filter((name) => !process.env[name]);
  if (missing.length) throw new Error(`Missing Cloudinary env: ${missing.join(", ")}`);
  cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET,
    secure: true,
  });
}

async function listCloudinaryResources(prefixes) {
  configureCloudinary();
  const rows = [];
  for (const resourceType of ["video", "raw"]) {
    for (const prefix of prefixes) {
      let nextCursor = undefined;
      do {
        const payload = await cloudinary.api.resources({
          type: "upload",
          resource_type: resourceType,
          prefix,
          max_results: 500,
          next_cursor: nextCursor,
        });
        for (const resource of payload.resources || []) {
          if (!resource.public_id || !resource.public_id.startsWith(prefix)) continue;
          const publicIdForPath = resourceType === "raw" ? resource.public_id : `${resource.public_id}.${resource.format || ""}`;
          if (!isAllowedAudiobookObject(publicIdForPath)) continue;
          rows.push({
            provider: "cloudinary",
            resource_type: resourceType,
            public_id: resource.public_id,
            identity_key: `${resourceType}:${resource.public_id}`,
            url: normalizeUrl(resource.secure_url || resource.url || ""),
            size_bytes: Number(resource.bytes || 0),
            last_modified: resource.created_at || "",
            prefix,
          });
        }
        nextCursor = payload.next_cursor;
      } while (nextCursor);
    }
  }
  return rows;
}

function b2Client() {
  const endpoint = envValue("B2_S3_ENDPOINT", ["B2_ENDPOINT"]);
  const region = envValue("B2_REGION");
  const bucket = envValue("B2_BUCKET");
  const accessKeyId = envValue("B2_ACCESS_KEY_ID", ["B2_KEY_ID"]);
  const secretAccessKey = envValue("B2_SECRET_ACCESS_KEY", ["B2_APP_KEY"]);
  const missing = [];
  if (!endpoint) missing.push("B2_S3_ENDPOINT");
  if (!region) missing.push("B2_REGION");
  if (!bucket) missing.push("B2_BUCKET");
  if (!accessKeyId) missing.push("B2_ACCESS_KEY_ID");
  if (!secretAccessKey) missing.push("B2_SECRET_ACCESS_KEY");
  if (missing.length) throw new Error(`Missing B2 env: ${missing.join(", ")}`);
  return {
    bucket,
    endpoint,
    client: new S3Client({
      endpoint,
      region,
      forcePathStyle: true,
      credentials: { accessKeyId, secretAccessKey },
    }),
  };
}

async function listB2Objects(prefixes) {
  const { client, bucket, endpoint } = b2Client();
  const rows = [];
  for (const prefix of prefixes) {
    let ContinuationToken = undefined;
    do {
      const payload = await client.send(new ListObjectsV2Command({
        Bucket: bucket,
        Prefix: prefix,
        ContinuationToken,
      }));
      for (const object of payload.Contents || []) {
        const key = object.Key || "";
        if (!key || !isAllowedAudiobookObject(key)) continue;
        rows.push({
          provider: "b2",
          key,
          identity_key: key,
          url: `${String(endpoint).replace(/\/+$/, "")}/${encodeURIComponent(bucket)}/${key.split("/").map(encodeURIComponent).join("/")}`,
          size_bytes: Number(object.Size || 0),
          last_modified: object.LastModified ? new Date(object.LastModified).toISOString() : "",
          prefix,
        });
      }
      ContinuationToken = payload.NextContinuationToken;
    } while (ContinuationToken);
  }
  return rows;
}

function orphanStatus(object, references, minAgeDays) {
  const normalizedUrl = normalizeUrl(object.url || "");
  const referenced = references.urls.has(normalizedUrl)
    || (object.provider === "b2" && references.b2Keys.has(object.key))
    || (object.provider === "cloudinary" && references.cloudinary.has(object.identity_key));
  if (referenced) return { candidate: false, reason: "referenced by live admin book metadata" };
  if (!isOlderThan(object.last_modified, minAgeDays)) return { candidate: false, reason: `protected by min-age-days=${minAgeDays}` };
  return { candidate: true, reason: "not referenced by any admin book audiobook fields" };
}

async function deleteCloudinary(object) {
  configureCloudinary();
  return cloudinary.uploader.destroy(object.public_id, {
    resource_type: object.resource_type,
    invalidate: true,
  });
}

async function deleteB2(object) {
  const { client, bucket } = b2Client();
  return client.send(new DeleteObjectCommand({ Bucket: bucket, Key: object.key }));
}

async function deleteObject(object) {
  if (object.provider === "cloudinary") return deleteCloudinary(object);
  if (object.provider === "b2") return deleteB2(object);
  throw new Error(`Unsupported provider for delete: ${object.provider}`);
}

function summarize(rows) {
  const totals = {
    scanned_objects: rows.length,
    referenced_objects: rows.filter((row) => row.status === "referenced").length,
    protected_recent_objects: rows.filter((row) => row.status === "protected_recent").length,
    orphan_candidates: rows.filter((row) => row.status === "orphan_candidate").length,
    deleted: rows.filter((row) => row.action === "deleted").length,
    errors: rows.filter((row) => row.action === "delete_error").length,
    reclaimable_bytes: rows.filter((row) => row.status === "orphan_candidate").reduce((sum, row) => sum + Number(row.size_bytes || 0), 0),
    deleted_bytes: rows.filter((row) => row.action === "deleted").reduce((sum, row) => sum + Number(row.size_bytes || 0), 0),
  };
  return {
    ...totals,
    reclaimable_gb: Number((totals.reclaimable_bytes / 1024 / 1024 / 1024).toFixed(4)),
    deleted_gb: Number((totals.deleted_bytes / 1024 / 1024 / 1024).toFixed(4)),
  };
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
  await ensureDir(args.jobDir);

  const client = new EarnalismAdminClient(args.apiUrl);
  await client.login();
  const books = await client.summaries();
  const references = collectReferencedAssets(books);
  const scanErrors = [];
  const storageObjects = [];

  process.stdout.write(`Audiobook storage cleanup job: ${args.jobId}\n`);
  process.stdout.write(`Mode: ${args.dryRun ? "dry-run" : "commit-delete"} | Provider: ${args.provider} | Prefixes: ${args.prefixes.join(", ")}\n`);

  if (args.provider === "all" || args.provider === "cloudinary") {
    try {
      storageObjects.push(...await listCloudinaryResources(args.prefixes));
    } catch (error) {
      scanErrors.push({ provider: "cloudinary", error: error.message });
    }
  }
  if (args.provider === "all" || args.provider === "b2") {
    try {
      storageObjects.push(...await listB2Objects(args.prefixes));
    } catch (error) {
      scanErrors.push({ provider: "b2", error: error.message });
    }
  }

  const rows = storageObjects.map((object) => {
    const status = orphanStatus(object, references, args.minAgeDays);
    return {
      ...object,
      status: status.candidate ? "orphan_candidate" : status.reason.startsWith("protected") ? "protected_recent" : "referenced",
      reason: status.reason,
      action: args.dryRun || !status.candidate ? "none" : "pending_delete",
    };
  });

  const candidates = rows.filter((row) => row.status === "orphan_candidate");
  if (args.commitDelete && candidates.length > args.deleteLimit) {
    process.stdout.write(`Delete candidate count ${candidates.length} exceeds --delete-limit ${args.deleteLimit}; deleting first ${args.deleteLimit} only.\n`);
  }
  const deleteTargets = args.commitDelete ? candidates.slice(0, args.deleteLimit) : [];
  for (const row of deleteTargets) {
    try {
      row.delete_result = await deleteObject(row);
      row.action = "deleted";
      process.stdout.write(`DELETED ${row.provider} ${row.key || row.public_id}\n`);
    } catch (error) {
      row.action = "delete_error";
      row.delete_error = error.message;
      process.stderr.write(`DELETE FAILED ${row.provider} ${row.key || row.public_id}: ${error.message}\n`);
    }
  }

  const report = {
    generated_at: new Date().toISOString(),
    job_id: args.jobId,
    mode: args.dryRun ? "dry-run" : "commit-delete",
    provider: args.provider,
    prefixes: args.prefixes,
    min_age_days: args.minAgeDays,
    delete_limit: args.deleteLimit,
    referenced_books: references.byBook.length,
    referenced_url_count: references.urls.size,
    scan_errors: scanErrors,
    summary: summarize(rows),
    objects: rows.sort((a, b) => {
      if (a.status !== b.status) return a.status.localeCompare(b.status);
      return String(a.provider).localeCompare(String(b.provider)) || String(a.key || a.public_id).localeCompare(String(b.key || b.public_id));
    }),
  };
  const reportPath = path.join(args.jobDir, "audiobook_storage_cleanup_report.json");
  await writeJson(reportPath, report);

  process.stdout.write("\nAudiobook storage cleanup summary\n");
  process.stdout.write("=================================\n");
  process.stdout.write(`Scanned objects: ${report.summary.scanned_objects}\n`);
  process.stdout.write(`Orphan candidates: ${report.summary.orphan_candidates}\n`);
  process.stdout.write(`Reclaimable GB: ${report.summary.reclaimable_gb}\n`);
  process.stdout.write(`Deleted: ${report.summary.deleted}\n`);
  process.stdout.write(`Errors: ${report.summary.errors + scanErrors.length}\n`);
  process.stdout.write(`Report: ${reportPath}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
