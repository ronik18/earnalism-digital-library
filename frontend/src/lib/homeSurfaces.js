import { API } from "./api";
import {
  getHomeCurationSnapshot,
  normalizeHomeCuration,
} from "./homeCuration";

const HERO_SCHEMA_VERSION = "home-hero-v1";
const LISTENING_SCHEMA_VERSION = "home-listening-v1";
const HERO_CACHE_KEY = "earnalism_home_hero:v1";
const LISTENING_CACHE_KEY = "earnalism_home_listening:v1";
const HERO_CACHE_TTL_MS = 60 * 60 * 1000;
const LISTENING_CACHE_TTL_MS = 5 * 60 * 1000;

const memoryCache = new Map();

function storage() {
  return typeof window === "undefined" ? null : window.localStorage;
}

function readCache(key, ttlMs) {
  const memory = memoryCache.get(key);
  if (memory && Date.now() - memory.cachedAt <= ttlMs) return memory.payload;
  try {
    const raw = storage()?.getItem(key);
    const record = raw ? JSON.parse(raw) : null;
    if (!record || !Number.isFinite(record.cachedAt) || Date.now() - record.cachedAt > ttlMs) return null;
    memoryCache.set(key, record);
    return record.payload;
  } catch {
    return null;
  }
}

function writeCache(key, payload) {
  const record = { cachedAt: Date.now(), payload };
  memoryCache.set(key, record);
  try {
    storage()?.setItem(key, JSON.stringify(record));
  } catch {
    // Private browsing and storage quotas must never block Home rendering.
  }
  return payload;
}

async function fetchPublicSurface(path, signal) {
  const response = await fetch(`${API}${path}`, {
    method: "GET",
    credentials: "omit",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(`Home surface request failed with ${response.status}`);
  return response.json();
}

export function normalizeHomeHeroContract(payload = {}) {
  if (payload.schema_version !== HERO_SCHEMA_VERSION || !payload.hero) {
    throw new Error("Unsupported Home hero contract");
  }
  return normalizeHomeCuration({
    hero: payload.hero,
    source: {
      ...(payload.source || {}),
      contract_revision: payload.revision || "",
    },
  });
}

export function normalizeHomeListeningContract(payload = {}) {
  if (payload.schema_version !== LISTENING_SCHEMA_VERSION || !Array.isArray(payload.items)) {
    throw new Error("Unsupported Home listening contract");
  }
  return normalizeHomeCuration({
    listening_rooms: {
      total_approved: Number(payload.total || payload.items.length),
      items: payload.items,
      reserve_items: [],
    },
    selected_audiobooks: payload.items,
    source: {
      ...(payload.source || {}),
      contract_revision: payload.revision || "",
    },
  });
}

export function getHomeHeroSnapshot() {
  const snapshot = getHomeCurationSnapshot();
  return { hero: snapshot.hero, source: snapshot.source };
}

export function getHomeListeningSnapshot() {
  const snapshot = getHomeCurationSnapshot();
  const items = snapshot.listening_rooms?.items || snapshot.selected_audiobooks || [];
  return {
    listening_rooms: { items, reserve_items: [] },
    selected_audiobooks: items,
    source: snapshot.source,
  };
}

export function getHomeHeroCache() {
  return readCache(HERO_CACHE_KEY, HERO_CACHE_TTL_MS);
}

export function getHomeListeningCache() {
  return readCache(LISTENING_CACHE_KEY, LISTENING_CACHE_TTL_MS);
}

export async function fetchHomeHero(signal) {
  const payload = await fetchPublicSurface("/home/hero", signal);
  return writeCache(HERO_CACHE_KEY, normalizeHomeHeroContract(payload));
}

export async function fetchHomeListening(signal, limit = 3) {
  const boundedLimit = Math.min(6, Math.max(1, Number(limit) || 3));
  const payload = await fetchPublicSurface(`/home/listening?limit=${boundedLimit}`, signal);
  return writeCache(LISTENING_CACHE_KEY, normalizeHomeListeningContract(payload));
}

export function clearHomeSurfaceCaches() {
  memoryCache.clear();
  try {
    storage()?.removeItem(HERO_CACHE_KEY);
    storage()?.removeItem(LISTENING_CACHE_KEY);
  } catch {
    // Storage cleanup is best-effort for tests and schema migrations.
  }
}

export const HOME_SURFACE_CACHE_KEYS = Object.freeze({
  hero: HERO_CACHE_KEY,
  listening: LISTENING_CACHE_KEY,
});
