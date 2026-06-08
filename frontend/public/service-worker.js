const CACHE_VERSION = "earnalism-v1";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const APP_SHELL = ["/", "/index.html", "/favicon.png", "/apple-touch-icon.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => !key.startsWith(CACHE_VERSION)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.origin === self.location.origin && (
    url.pathname.startsWith("/static/") ||
    url.pathname.startsWith("/assets/") ||
    url.pathname.startsWith("/audio/") ||
    /\.(?:png|jpg|jpeg|webp|gif|svg|ico|css|js|woff2?)$/i.test(url.pathname)
  );
}

function isReaderAudioAsset(request) {
  const url = new URL(request.url);
  return url.origin === self.location.origin
    && url.pathname.startsWith("/audio/")
    && /\.(?:mp3|m4a|ogg|opus|wav|json|vtt|m3u8|ts)$/i.test(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || request.headers.has("authorization")) return;
  if (request.headers.has("range")) return;

  if (isStaticAsset(request) || isReaderAudioAsset(request)) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return response;
      }),
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/index.html")),
    );
  }
});
