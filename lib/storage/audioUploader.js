const fs = require("fs");
const path = require("path");
const { S3Client } = require("@aws-sdk/client-s3");
const { Upload } = require("@aws-sdk/lib-storage");
const cloudinary = require("cloudinary").v2;

const AUDIO_B2_THRESHOLD_BYTES = 100 * 1024 * 1024;
const DIRECT_CLOUDINARY_UPLOAD_LIMIT_BYTES = Number.parseInt(
  process.env.CLOUDINARY_DIRECT_UPLOAD_LIMIT_BYTES || `${95 * 1024 * 1024}`,
  10,
);
const CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES = Number.parseInt(
  process.env.CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES || `${10 * 1024 * 1024}`,
  10,
);
const CLOUDINARY_LARGE_UPLOAD_CHUNK_BYTES = Number.parseInt(
  process.env.CLOUDINARY_LARGE_UPLOAD_CHUNK_BYTES || `${20 * 1024 * 1024}`,
  10,
);
const B2_MULTIPART_PART_SIZE = 10 * 1024 * 1024;
const B2_MULTIPART_QUEUE_SIZE = 4;
const ASSET_CONFIG = {
  mp3: { contentType: "audio/mpeg", resourceType: "video", cloudinaryLimit: AUDIO_B2_THRESHOLD_BYTES },
  timestamps: { contentType: "application/json", resourceType: "raw", cloudinaryLimit: CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES },
  vtt: { contentType: "text/vtt", resourceType: "raw", cloudinaryLimit: CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES },
  chapters: { contentType: "application/json", resourceType: "raw", cloudinaryLimit: CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES },
  meta: { contentType: "application/json", resourceType: "raw", cloudinaryLimit: CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES },
  manifest: { contentType: "application/json", resourceType: "raw", cloudinaryLimit: CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES },
};

function requireEnv(names) {
  const missing = names.filter((name) => !process.env[name]);
  if (missing.length) {
    throw new Error(`Missing required environment variable(s): ${missing.join(", ")}`);
  }
}

function envValue(primary, aliases = []) {
  for (const name of [primary, ...aliases]) {
    const value = String(process.env[name] || "").trim();
    if (value) return value;
  }
  return "";
}

function normalizeAwsError(error) {
  const code = error?.name || error?.Code || error?.code || "";
  const message = error?.message || String(error || "");
  if (code === "InvalidAccessKeyId" && /malformed/i.test(message)) {
    return new Error(
      "Backblaze B2 rejected B2_ACCESS_KEY_ID as malformed for the S3-compatible API. "
      + "Use a standard app key created from Backblaze App Keys, not the master application key/account key. "
      + "Set B2_ACCESS_KEY_ID to the new Application Key ID and B2_SECRET_ACCESS_KEY to the matching Application Key.",
    );
  }
  return error;
}

function normalizeFolder(value) {
  return String(value || "earnalism/audiobooks").trim().replace(/^\/+|\/+$/g, "");
}

function sanitizeSegment(value, fallback) {
  const normalized = String(value || fallback || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || fallback;
}

function encodeKeyPath(key) {
  return String(key)
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

function buildB2ObjectUrl(endpoint, bucket, key) {
  const base = String(endpoint || "").replace(/\/+$/g, "");
  return `${base}/${encodeURIComponent(bucket)}/${encodeKeyPath(key)}`;
}

function configureCloudinary() {
  requireEnv(["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"]);
  cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET,
    secure: true,
  });
}

function buildCloudinaryOptions({ publicId, slug, language, assetKind }) {
  const config = ASSET_CONFIG[assetKind] || ASSET_CONFIG.mp3;
  return {
    resource_type: config.resourceType,
    public_id: publicId,
    overwrite: true,
    invalidate: true,
    tags: ["earnalism", "audiobook", language, slug].filter(Boolean),
    context: {
      slug,
      language,
      asset_kind: assetKind || "mp3",
      generated_by: "open_source_audiobook_onboarding",
    },
  };
}

async function uploadToCloudinary({ filePath, size, duration, publicId, slug, language, assetKind }) {
  configureCloudinary();
  const options = buildCloudinaryOptions({ publicId, slug, language, assetKind });
  const result = size > DIRECT_CLOUDINARY_UPLOAD_LIMIT_BYTES && options.resource_type !== "raw"
    ? await cloudinary.uploader.upload_large(filePath, {
      chunk_size: CLOUDINARY_LARGE_UPLOAD_CHUNK_BYTES,
      ...options,
    })
    : await cloudinary.uploader.upload(filePath, options);
  const url = result.secure_url || result.url;
  if (!url) throw new Error("Cloudinary upload did not return a URL");
  return {
    url,
    provider: "cloudinary",
    size,
    duration,
  };
}

function b2Client() {
  requireEnv(["B2_S3_ENDPOINT", "B2_REGION", "B2_BUCKET"]);
  const accessKeyId = envValue("B2_ACCESS_KEY_ID", ["B2_KEY_ID"]);
  const secretAccessKey = envValue("B2_SECRET_ACCESS_KEY", ["B2_APP_KEY"]);
  if (!accessKeyId || !secretAccessKey) {
    throw new Error("Missing B2 S3 credentials: set B2_ACCESS_KEY_ID/B2_SECRET_ACCESS_KEY or B2_KEY_ID/B2_APP_KEY");
  }
  return new S3Client({
    endpoint: envValue("B2_S3_ENDPOINT", ["B2_ENDPOINT"]),
    region: process.env.B2_REGION,
    forcePathStyle: true,
    credentials: {
      accessKeyId,
      secretAccessKey,
    },
  });
}

async function uploadToB2({ filePath, size, duration, slug, language, folder, fileName, assetKind }) {
  const bucket = process.env.B2_BUCKET;
  const config = ASSET_CONFIG[assetKind] || ASSET_CONFIG.mp3;
  const safeLanguage = sanitizeSegment(language, "en");
  const safeSlug = sanitizeSegment(slug || path.basename(filePath, path.extname(filePath)), "audiobook");
  const safeFileName = sanitizeSegment(fileName || path.basename(filePath), `${safeSlug}.mp3`);
  const key = `${normalizeFolder(folder)}/${safeLanguage}/${safeSlug}/${safeFileName}`;
  const upload = new Upload({
    client: b2Client(),
    params: {
      Bucket: bucket,
      Key: key,
      Body: fs.createReadStream(filePath),
      ContentLength: size,
      ContentType: config.contentType,
      Metadata: {
        slug: safeSlug,
        language: safeLanguage,
        asset_kind: assetKind || "mp3",
        generated_by: "open_source_audiobook_onboarding",
      },
    },
    partSize: B2_MULTIPART_PART_SIZE,
    queueSize: B2_MULTIPART_QUEUE_SIZE,
  });
  try {
    await upload.done();
  } catch (error) {
    throw normalizeAwsError(error);
  }
  return {
    url: buildB2ObjectUrl(process.env.B2_S3_ENDPOINT, bucket, key),
    provider: "b2",
    size,
    duration,
  };
}

async function uploadAudiobook({
  filePath,
  slug,
  language = "en",
  publicId,
  folder = "earnalism/audiobooks",
  cloudinaryFolder,
  duration = 0,
  assetKind = "mp3",
  fileName,
}) {
  if (!filePath) throw new Error("filePath is required");
  const stat = fs.statSync(filePath);
  if (!stat.isFile()) throw new Error(`Audiobook file not found: ${filePath}`);
  const size = stat.size;
  const normalizedDuration = Number.parseInt(duration || 0, 10) || 0;
  const normalizedSlug = sanitizeSegment(slug || path.basename(filePath, path.extname(filePath)), "audiobook");
  const normalizedLanguage = sanitizeSegment(language, "en");
  const targetFolder = cloudinaryFolder || folder;
  const cloudinaryPublicId = publicId || `${normalizeFolder(targetFolder)}/${normalizedLanguage}/${normalizedSlug}/${normalizedSlug}`;
  const normalizedAssetKind = sanitizeSegment(assetKind, "mp3");
  const config = ASSET_CONFIG[normalizedAssetKind] || ASSET_CONFIG.mp3;

  if (size <= config.cloudinaryLimit) {
    return uploadToCloudinary({
      filePath,
      size,
      duration: normalizedDuration,
      publicId: cloudinaryPublicId,
      slug: normalizedSlug,
      language: normalizedLanguage,
      assetKind: normalizedAssetKind,
    });
  }
  return uploadToB2({
    filePath,
    size,
    duration: normalizedDuration,
    slug: normalizedSlug,
    language: normalizedLanguage,
    folder: targetFolder,
    fileName: fileName || path.basename(filePath),
    assetKind: normalizedAssetKind,
  });
}

function parseCliArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2).replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase());
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      index += 1;
    }
  }
  return args;
}

if (require.main === module) {
  uploadAudiobook(parseCliArgs(process.argv.slice(2)))
    .then((result) => {
      process.stdout.write(`${JSON.stringify(result)}\n`);
    })
    .catch((error) => {
      process.stderr.write(`${error.stack || error.message || error}\n`);
      process.exitCode = 1;
    });
}

module.exports = {
  AUDIO_B2_THRESHOLD_BYTES,
  B2_MULTIPART_PART_SIZE,
  B2_MULTIPART_QUEUE_SIZE,
  CLOUDINARY_RAW_UPLOAD_LIMIT_BYTES,
  uploadAudiobook,
};
