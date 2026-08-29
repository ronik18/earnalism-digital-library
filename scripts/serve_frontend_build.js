#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const root = path.resolve(__dirname, "..", "frontend", "build");
const host = process.argv.includes("--host") ? process.argv[process.argv.indexOf("--host") + 1] : "127.0.0.1";
const port = Number(process.argv.includes("--port") ? process.argv[process.argv.indexOf("--port") + 1] : 3000);
if (host !== "127.0.0.1" || !Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("Local UAT server requires an unprivileged 127.0.0.1 port.");
const mime = { ".css": "text/css", ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".xml": "application/xml" };
const exactRoutes = new Set(["/", "/library", "/journal", "/about", "/about-legacy", "/contact", "/pricing", "/micro-story", "/login", "/signup", "/signin", "/account", "/my-library", "/publishing", "/admin", "/admin/login", "/admin/launch-monitor"]);
const routePrefixes = ["/book/", "/journal/", "/reader/", "/reader-legacy/", "/listener/", "/listener-legacy/", "/publishing/", "/admin/"];
const removedRoutes = new Set(["/product/patterned-wrap-dress"]);
const securityHeaders = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "X-Frame-Options": "DENY",
};
const noIndexHeaders = { ...securityHeaders, "Content-Type": "text/plain", "X-Robots-Tag": "noindex, nofollow, noarchive" };

function isSpaRoute(pathname) {
  return exactRoutes.has(pathname) || routePrefixes.some((prefix) => pathname.startsWith(prefix));
}

if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) {
  throw new Error("frontend/build is required; run npm --prefix frontend run build first.");
}

http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, `http://${host}`).pathname);
  const candidate = path.resolve(root, `.${pathname}`);
  const safe = candidate === root || candidate.startsWith(`${root}${path.sep}`);
  const candidateStat = safe ? fs.statSync(candidate, { throwIfNoEntry: false }) : null;
  const directoryIndex = candidateStat?.isDirectory() ? path.join(candidate, "index.html") : null;
  const staticFile = candidateStat?.isFile() ? candidate : (directoryIndex && fs.statSync(directoryIndex, { throwIfNoEntry: false })?.isFile() ? directoryIndex : null);
  if (!safe) {
    response.writeHead(400, noIndexHeaders).end("Invalid path");
    return;
  }
  if (!staticFile && removedRoutes.has(pathname)) {
    response.writeHead(410, noIndexHeaders).end("Gone");
    return;
  }
  if (!staticFile && !isSpaRoute(pathname)) {
    response.writeHead(404, noIndexHeaders).end("Not found");
    return;
  }
  const file = staticFile || path.join(root, "index.html");
  response.writeHead(200, { ...securityHeaders, "Content-Type": mime[path.extname(file)] || "application/octet-stream", "Cache-Control": file.endsWith("index.html") ? "no-store" : "public, max-age=300" });
  fs.createReadStream(file).pipe(response);
}).listen(port, host, () => console.log(`Earnalism local UAT frontend: http://${host}:${port}`));
