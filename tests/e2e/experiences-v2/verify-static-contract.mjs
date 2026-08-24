import fs from "node:fs";
import path from "node:path";

const frontend = path.resolve(process.argv[2] || "frontend");
const read = (relativePath) => fs.readFileSync(path.join(frontend, "src", "experiences-v2", relativePath), "utf8");
const assert = (condition, message) => { if (!condition) throw new Error(message); };

const reader = read("reader/ReaderExperienceV2.jsx");
const listener = read("listener/ListenerExperienceV2.jsx");
const about = read("about/AboutExperienceV2.jsx");
const shared = read("shared/experiences-v2.css");
const readerRoute = read("reader/ReaderExperienceV2Route.jsx");
const listenerRoute = read("listener/ListenerExperienceV2Route.jsx");

assert(!/fetch\(|axios|prefetch|localStorage/.test(reader), "Reader v2 must not create a client fetch or prefetch path.");
assert((listener.match(/<audio/g) || []).length === 1, "Listener v2 must define one audio controller.");
assert(listener.includes('preload="metadata"'), "Listener v2 must preload metadata only.");
assert(!/download=|autoplay|background.play/i.test(listener), "Listener v2 must not advertise unsupported audio behavior.");
assert(!/fetch\(|axios/.test(about), "About v2 must make zero data API calls.");
assert(shared.includes("prefers-reduced-motion") && shared.includes("max-width: 767px"), "Scoped CSS must include reduced-motion and mobile rules.");
assert(readerRoute.includes("canonicalPage > 3 && !lease"), "Reader route must not request protected pages before a lease exists.");
assert(listenerRoute.includes("startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 180 })"), "Listener must authorize protected continuation explicitly.");
console.log("RLA_V2_STATIC_CONTRACT=passed");
