#!/usr/bin/env python3

from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

VALID_EXACT_ROUTES = {
    "/",
    "/library",
    "/pricing",
    "/journal",
    "/contact",
    "/about",
    "/login",
    "/signup",
    "/account",
}

VALID_PREFIX_ROUTES = (
    "/book/",
    "/reader/",
    "/journal/",
)

TOMBSTONE_ROUTES = {
    "/product/patterned-wrap-dress",
}


class Handler(SimpleHTTPRequestHandler):
    build_directory: Path

    def log_message(self, format_string, *args):
        print(
            "%s - - [%s] %s"
            % (
                self.address_string(),
                self.log_date_time_string(),
                format_string % args,
            ),
            flush=True,
        )

    def _request_path(self) -> str:
        path = unquote(urlsplit(self.path).path)
        if not path.startswith("/"):
            path = "/" + path
        return path

    def _safe_file(self, request_path: str) -> Path | None:
        relative = request_path.lstrip("/")
        candidate = (
            self.build_directory / relative
        ).resolve()

        try:
            candidate.relative_to(
                self.build_directory.resolve()
            )
        except ValueError:
            return None

        return candidate if candidate.is_file() else None

    def _is_valid_spa_route(self, path: str) -> bool:
        if path in VALID_EXACT_ROUTES:
            return True

        return any(
            path.startswith(prefix)
            and len(path) > len(prefix)
            for prefix in VALID_PREFIX_ROUTES
        )

    def _send_bytes(
        self,
        status: int,
        payload: bytes,
        content_type: str,
        *,
        noindex: bool = False,
        head_only: bool = False,
        no_store: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Content-Length",
            str(len(payload)),
        )

        if noindex:
            self.send_header(
                "X-Robots-Tag",
                "noindex, nofollow, noarchive",
            )

        if no_store:
            self.send_header(
                "Cache-Control",
                "no-store",
            )

        self.end_headers()

        if not head_only:
            self.wfile.write(payload)

    def _send_file(
        self,
        path: Path,
        *,
        status: int = 200,
        head_only: bool = False,
        no_store: bool = False,
    ) -> None:
        payload = path.read_bytes()

        content_type = (
            mimetypes.guess_type(str(path))[0]
            or "application/octet-stream"
        )

        self._send_bytes(
            status,
            payload,
            content_type,
            head_only=head_only,
            no_store=no_store,
        )

    def _send_error_document(
        self,
        status: int,
        title: str,
        *,
        head_only: bool = False,
    ) -> None:
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>{title}</title>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>This route is not available.</p>
  </main>
</body>
</html>
"""
        self._send_bytes(
            status,
            html.encode("utf-8"),
            "text/html; charset=utf-8",
            noindex=True,
            head_only=head_only,
            no_store=True,
        )

    def _handle(self, *, head_only: bool) -> None:
        path = self._request_path()

        if path in TOMBSTONE_ROUTES:
            self._send_error_document(
                410,
                "Content removed",
                head_only=head_only,
            )
            return

        static_file = self._safe_file(path)

        if static_file:
            self._send_file(
                static_file,
                head_only=head_only,
            )
            return

        if self._is_valid_spa_route(path):
            index_path = (
                self.build_directory / "index.html"
            )

            self._send_file(
                index_path,
                status=200,
                head_only=head_only,
                no_store=True,
            )
            return

        self._send_error_document(
            404,
            "Page not found",
            head_only=head_only,
        )

    def do_GET(self):
        self._handle(head_only=False)

    def do_HEAD(self):
        self._handle(head_only=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    build_directory = Path(
        args.directory
    ).resolve()

    index_path = build_directory / "index.html"

    if not index_path.is_file():
        raise SystemExit(
            f"Build index is missing: {index_path}"
        )

    Handler.build_directory = build_directory

    server = ThreadingHTTPServer(
        (args.host, args.port),
        Handler,
    )

    print(
        f"UAT frontend serving "
        f"http://{args.host}:{args.port}",
        flush=True,
    )

    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
