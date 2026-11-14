#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const https = require("node:https");
const url = require("node:url");

const {
  isKnownSpaPath,
  isStaticAssetPath,
  removedRouteResult,
  normalizePath,
} = require("./uat_route_policy");

const FRONTEND_BUILD_DIR = path.resolve(__dirname, "../frontend/build");
const HOST = process.env.HOST || "127.0.0.1";
const PORT = parseInt(process.env.FRONTEND_PORT || "3000", 10);
const LISTEN_HOST = process.env.FRONTEND_HOST || HOST;
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const backendUrl = url.parse(BACKEND_URL);

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const map = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
  };
  return map[ext] || "application/octet-stream";
}

function resolveBuildPath(requestPath) {
  const normalized = path.posix.normalize(`.${normalizePath(requestPath)}`);
  return path.join(FRONTEND_BUILD_DIR, normalized);
}

function sendFile(response, filePath, statusCode = 200, extraHeaders = {}) {
  const headers = {
    "Cache-Control": "public, max-age=300",
    "Content-Type": contentType(filePath),
    ...extraHeaders,
  };
  const stream = fs.createReadStream(filePath);
  response.writeHead(statusCode, headers);
  stream.pipe(response);
  stream.on("error", () => {
    response.writeHead(500);
    response.end("Failed to read static file.");
  });
}

function sendText(response, statusCode, text, extraHeaders = {}) {
  const headers = {
    "Content-Type": "text/plain; charset=utf-8",
    ...extraHeaders,
  };
  response.writeHead(statusCode, headers);
  response.end(text);
}

function proxyApiRequest(request, response) {
  const parsedRequest = url.parse(request.url || "", true);
  const targetUrl = `${backendUrl.protocol || "http:"}//${backendUrl.host}${parsedRequest.path}`;
  const headers = { ...request.headers };
  delete headers.host;
  const transport = backendUrl.protocol === "https:" ? https : http;
  const proxyReq = transport.request(
    targetUrl,
    {
      method: request.method,
      headers,
    },
    (proxyRes) => {
      response.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(response);
    },
  );
  proxyReq.on("error", () => {
    sendText(response, 502, "Upstream API unavailable");
  });
  request.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
  const pathname = (url.parse(req.url || "").pathname || "/").replace(/\/$/, "");
  if (pathname.startsWith("/api/")) {
    return proxyApiRequest(req, res);
  }

  if (isStaticAssetPath(pathname)) {
    const staticPath = resolveBuildPath(pathname);
    if (fs.existsSync(staticPath) && fs.statSync(staticPath).isFile()) {
      return sendFile(res, staticPath);
    }
  }

  const removalCode = removedRouteResult(pathname);
  if (removalCode !== 404 && !isKnownSpaPath(pathname) && !isStaticAssetPath(pathname)) {
    if (removalCode === 410) {
      return sendText(
        res,
        410,
        "Removed content",
        {
          "X-Robots-Tag": "noindex, nofollow, noarchive",
          "Cache-Control": "public, max-age=3600, s-maxage=86400",
        },
      );
    }
    return sendText(
      res,
      404,
      "Not Found",
      {
        "X-Robots-Tag": "noindex, nofollow, noarchive",
        "Cache-Control": "no-cache",
      },
    );
  }

  if (isKnownSpaPath(pathname) || req.url?.endsWith("/")) {
    const indexPath = path.join(FRONTEND_BUILD_DIR, "index.html");
    return sendFile(res, indexPath);
  }

  const removed = removedRouteResult(pathname);
  if (removed === 410) {
    return sendText(
      res,
      410,
      "Removed content",
      {
        "X-Robots-Tag": "noindex, nofollow, noarchive",
        "Cache-Control": "public, max-age=3600, s-maxage=86400",
      },
    );
  }

  return sendText(
    res,
    404,
    "Not Found",
    {
      "X-Robots-Tag": "noindex, nofollow, noarchive",
      "Cache-Control": "no-cache",
    },
  );
});

server.listen(PORT, LISTEN_HOST, () => {
  process.stdout.write(`Frontend static server running at http://${LISTEN_HOST}:${PORT}\n`);
});

server.on("error", (error) => {
  console.error(error.message);
  process.exit(1);
});
