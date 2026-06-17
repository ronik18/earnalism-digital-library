#!/usr/bin/env node

const fs = require("fs/promises");
const path = require("path");

const DEFAULT_LOCALE = "bn-IN";
const DEFAULT_VOICE = "bn-IN-TanishaaNeural";
const DEFAULT_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3";
const DEFAULT_TIMEOUT_MS = 120000;

function usage() {
  return `
Usage:
  node scripts/audio/tts/azureBengaliTts.js --input chunk.ssml --output chunk.mp3

Required env:
  AZURE_SPEECH_KEY
  AZURE_SPEECH_REGION

Optional env:
  BENGALI_TTS_VOICE_ID=bn-IN-TanishaaNeural
  AZURE_BENGALI_VOICE=bn-IN-TanishaaNeural
  AZURE_SPEECH_OUTPUT_FORMAT=audio-24khz-48kbitrate-mono-mp3
  AZURE_SPEECH_FALLBACK_REGIONS=eastus,uksouth
  AZURE_SPEECH_KEY_EASTUS=...

The polish pipeline also passes:
  EARNALISM_TTS_INPUT
  EARNALISM_TTS_OUTPUT
`;
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === "--help" || token === "-h") args.help = true;
    else if (token.startsWith("--")) {
      const key = token.slice(2).replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase());
      if (!next || next.startsWith("--")) args[key] = true;
      else {
        args[key] = next;
        index += 1;
      }
    }
  }
  return args;
}

function envValue(...names) {
  for (const name of names) {
    const value = String(process.env[name] || "").trim();
    if (value) return value;
  }
  return "";
}

function regionEnvSuffix(region) {
  return String(region || "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_");
}

function fallbackRegions(primaryRegion) {
  const primary = String(primaryRegion || "").trim().toLowerCase();
  return String(process.env.AZURE_SPEECH_FALLBACK_REGIONS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, items) => item.toLowerCase() !== primary && items.findIndex((other) => other.toLowerCase() === item.toLowerCase()) === index);
}

function keyForFallbackRegion(region) {
  const suffix = regionEnvSuffix(region);
  if (!suffix) return "";
  return envValue(`AZURE_SPEECH_KEY_${suffix}`, `SPEECH_KEY_${suffix}`);
}

function escapeXml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function stripSpeakRoot(value) {
  const text = String(value || "").trim().replace(/^<\?xml[^>]*>\s*/i, "");
  const open = text.match(/^<speak\b[^>]*>/i);
  if (!open) return text;
  return text
    .slice(open[0].length)
    .replace(/<\/speak>\s*$/i, "")
    .trim();
}

function azureSsml(input, { locale, voice }) {
  const raw = String(input || "").trim();
  const body = /^<speak\b/i.test(raw) ? stripSpeakRoot(raw) : escapeXml(raw);
  if (/<voice\b/i.test(body)) {
    return [
      `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${escapeXml(locale)}">`,
      body,
      "</speak>",
    ].join("");
  }
  return [
    `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${escapeXml(locale)}">`,
    `<voice name="${escapeXml(voice)}">`,
    body,
    "</voice>",
    "</speak>",
  ].join("");
}

function ssmlPreview(value) {
  return String(value || "").replace(/\s+/g, " ").slice(0, 500);
}

function assertSafeAzureSsml(ssml) {
  const malformed = String(ssml || "").match(/<[^>]*<break\b[^>]*>/i);
  if (malformed) {
    throw new Error(`Azure SSML is malformed before request near: ${ssmlPreview(malformed[0])}`);
  }
}

function isFallbackEligibleError(error) {
  const status = Number(error?.status || 0);
  return status === 408 || status === 429 || status >= 500;
}

async function synthesizeOnce({ inputPath, outputPath, key, region, locale, voice, outputFormat }) {
  const input = await fs.readFile(inputPath, "utf8");
  const ssml = azureSsml(input, { locale, voice });
  assertSafeAzureSsml(ssml);
  const endpoint = `https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(process.env.AZURE_TTS_TIMEOUT_MS || DEFAULT_TIMEOUT_MS));

  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": outputFormat,
        "User-Agent": "EarnalismBengaliAudiobookPolish",
      },
      body: ssml,
    });
  } finally {
    clearTimeout(timeout);
  }

  const body = Buffer.from(await response.arrayBuffer());
  if (!response.ok) {
    const detail = body.toString("utf8").slice(0, 1000);
    const retryAfter = response.headers.get("retry-after") || response.headers.get("Retry-After") || "";
    const error = new Error(
      `Azure Bengali TTS failed: HTTP ${response.status} ${detail}; voice=${voice}; region=${region}; retry_after=${retryAfter || "not-provided"}; ssml_preview=${ssmlPreview(ssml)}`,
    );
    error.status = response.status;
    error.retryAfter = retryAfter;
    error.region = region;
    throw error;
  }
  if (!body.length) throw new Error("Azure Bengali TTS returned an empty audio response");
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, body);
  return {
    outputPath,
    locale,
    voice,
    outputFormat,
    region,
    fallbackRegionUsed: "",
  };
}

async function synthesize({ inputPath, outputPath, key, region, locale, voice, outputFormat }) {
  const candidates = [{ region, key, fallback: false }];
  for (const fallbackRegion of fallbackRegions(region)) {
    const fallbackKey = keyForFallbackRegion(fallbackRegion);
    if (fallbackKey) candidates.push({ region: fallbackRegion, key: fallbackKey, fallback: true });
  }

  let lastError = null;
  for (let index = 0; index < candidates.length; index += 1) {
    const candidate = candidates[index];
    try {
      const result = await synthesizeOnce({
        inputPath,
        outputPath,
        key: candidate.key,
        region: candidate.region,
        locale,
        voice,
        outputFormat,
      });
      return {
        ...result,
        fallbackRegionUsed: candidate.fallback ? candidate.region : "",
      };
    } catch (error) {
      lastError = error;
      const hasNext = index < candidates.length - 1;
      if (!hasNext || !isFallbackEligibleError(error)) throw error;
      await fs.rm(outputPath, { force: true }).catch(() => {});
    }
  }
  throw lastError || new Error("Azure Bengali TTS failed before any region was attempted");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(usage());
    return;
  }

  const inputPath = args.input || envValue("EARNALISM_TTS_INPUT");
  const outputPath = args.output || envValue("EARNALISM_TTS_OUTPUT");
  const key = args.key || envValue("AZURE_SPEECH_KEY", "SPEECH_KEY");
  const region = args.region || envValue("AZURE_SPEECH_REGION", "SPEECH_REGION");
  const locale = args.locale || envValue("AZURE_BENGALI_LOCALE", "BENGALI_TTS_LOCALE") || DEFAULT_LOCALE;
  const voice = args.voice || envValue("AZURE_BENGALI_VOICE", "BENGALI_TTS_VOICE_ID") || DEFAULT_VOICE;
  const outputFormat = args.outputFormat || envValue("AZURE_SPEECH_OUTPUT_FORMAT", "BENGALI_TTS_AZURE_OUTPUT_FORMAT") || DEFAULT_OUTPUT_FORMAT;

  const missing = [];
  if (!inputPath) missing.push("--input or EARNALISM_TTS_INPUT");
  if (!outputPath) missing.push("--output or EARNALISM_TTS_OUTPUT");
  if (!key) missing.push("AZURE_SPEECH_KEY");
  if (!region) missing.push("AZURE_SPEECH_REGION");
  if (missing.length) throw new Error(`Missing required Azure Bengali TTS config: ${missing.join(", ")}`);

  const result = await synthesize({ inputPath, outputPath, key, region, locale, voice, outputFormat });
  process.stdout.write(JSON.stringify(result) + "\n");
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
