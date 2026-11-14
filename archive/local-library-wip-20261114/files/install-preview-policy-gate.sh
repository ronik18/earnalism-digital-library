#!/usr/bin/env bash

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
BACKUP_DIR="$ROOT/uat/backups/preview-policy-gate-$STAMP"

SERVER_FILE="$ROOT/backend/server.py"
MIDDLEWARE_FILE="$ROOT/backend/preview_policy_gate.py"
POLICY_DIR="$ROOT/backend/data/controlled_publications/dracula"
POLICY_FILE="$POLICY_DIR/preview_policy.json"

mkdir -p "$BACKUP_DIR" "$POLICY_DIR"

[[ -f "$SERVER_FILE" ]] || {
  echo "ERROR: Missing backend/server.py" >&2
  exit 1
}

cp "$SERVER_FILE" "$BACKUP_DIR/server.py"

if [[ -f "$MIDDLEWARE_FILE" ]]; then
  cp "$MIDDLEWARE_FILE" \
    "$BACKUP_DIR/preview_policy_gate.py"
fi

if [[ -f "$POLICY_FILE" ]]; then
  cp "$POLICY_FILE" \
    "$BACKUP_DIR/preview_policy.json"
fi

###############################################################################
# Generic preview-policy middleware
###############################################################################

cat > "$MIDDLEWARE_FILE" <<'PY'
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_MANIFEST_ROUTE = re.compile(
    r"^/api/reader/book/(?P<slug>[a-z0-9-]+)/manifest/?$"
)

_BOOK_DETAIL_ROUTE = re.compile(
    r"^/api/books/(?P<slug>[a-z0-9-]+)/?$"
)

_BOOK_LIST_ROUTE = re.compile(
    r"^/api/books/?$"
)

_READER_CONTENT_ROUTE = re.compile(
    r"^/api/reader/book/(?P<slug>[a-z0-9-]+)/"
    r"(?P<resource>(?!manifest/?$|audiobook/?$).+)$"
)


class PreviewPolicyGate:
    """
    Final server-side guard for controlled publication preview policy.

    This middleware is generic. It activates only when a title has:

        data/controlled_publications/<slug>/preview_policy.json

    Until canonical-page generation and authorization are ready, the policy
    fails closed even if a database, publication conveyor, or legacy manifest
    marks chapters as previewable.
    """

    def __init__(
        self,
        app,
        *,
        policy_root: str,
    ) -> None:
        self.app = app
        self.policy_root = Path(policy_root).resolve()

    def _classify(
        self,
        path: str,
    ) -> tuple[str, str] | None:
        match = _MANIFEST_ROUTE.match(path)
        if match:
            return "manifest", match.group("slug")

        match = _BOOK_DETAIL_ROUTE.match(path)
        if match:
            return "book_detail", match.group("slug")

        if _BOOK_LIST_ROUTE.match(path):
            return "book_list", ""

        match = _READER_CONTENT_ROUTE.match(path)
        if match:
            return "reader_content", match.group("slug")

        return None

    def _policy_path(
        self,
        slug: str,
    ) -> Path:
        return (
            self.policy_root
            / slug
            / "preview_policy.json"
        )

    def _load_policy(
        self,
        slug: str,
    ) -> dict[str, Any] | None:
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            return None

        path = self._policy_path(slug)

        if not path.is_file():
            return None

        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            # An unreadable controlled policy must fail closed.
            return {
                "schema_version": "canonical-page-preview-v1",
                "unit": "canonical_page",
                "configured_public_limit": 3,
                "public_limit": 3,
                "enforced_by": "server",
                "ready": False,
                "status": "INVALID_PREVIEW_POLICY",
            }

        if not isinstance(payload, dict):
            return None

        return payload

    @staticmethod
    def _public_policy(
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        raw_limit = policy.get(
            "public_limit",
            policy.get("configured_public_limit", 3),
        )

        try:
            public_limit = int(raw_limit)
        except (TypeError, ValueError):
            public_limit = 3

        return {
            "schema_version": str(
                policy.get(
                    "schema_version",
                    "canonical-page-preview-v1",
                )
            ),
            "unit": "canonical_page",
            "configured_public_limit": public_limit,
            "public_limit": public_limit,
            "enforced_by": "server",
            "ready": policy.get("ready") is True,
            "status": str(
                policy.get(
                    "status",
                    (
                        "READY"
                        if policy.get("ready") is True
                        else
                        "BLOCKED_PENDING_CANONICAL_PAGE_GENERATION"
                    ),
                )
            ),
        }

    @staticmethod
    def _strip_chapter_preview(
        chapter: Any,
    ) -> Any:
        if not isinstance(chapter, dict):
            return chapter

        sanitized = dict(chapter)

        sanitized["is_preview"] = False
        sanitized["is_free_preview"] = False
        sanitized["preview_enabled"] = False

        for key in (
            "preview_content",
            "preview_text",
            "preview_html",
            "preview_url",
            "public_content",
        ):
            sanitized.pop(key, None)

        return sanitized

    def _apply_manifest_policy(
        self,
        payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(payload)
        public_policy = self._public_policy(policy)
        ready = public_policy["ready"]

        result["preview_policy"] = public_policy
        result["preview_page_limit"] = (
            public_policy["public_limit"]
            if ready
            else None
        )

        access = result.get("access")
        if not isinstance(access, dict):
            access = {}
        else:
            access = dict(access)

        access.update(
            {
                "public_preview_enabled": ready,
                "preview_unit": "canonical_page",
                "configured_public_limit": (
                    public_policy["public_limit"]
                ),
                "preview_policy_status": (
                    public_policy["status"]
                ),
            }
        )

        result["access"] = access

        book = result.get("book")
        if not isinstance(book, dict):
            book = {}
        else:
            book = dict(book)

        book.update(
            {
                "preview_enabled": ready,
                "preview_page_limit": (
                    public_policy["public_limit"]
                    if ready
                    else None
                ),
                "preview_policy": public_policy,
                "preview_policy_status": (
                    public_policy["status"]
                ),
            }
        )

        if not ready:
            book["preview_url"] = ""

        result["book"] = book

        chapters = result.get("chapters")
        if isinstance(chapters, list):
            result["chapters"] = [
                self._strip_chapter_preview(chapter)
                for chapter in chapters
            ]

        return result

    def _apply_book_policy(
        self,
        payload: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(payload)
        public_policy = self._public_policy(policy)
        ready = public_policy["ready"]

        result.update(
            {
                "preview_enabled": ready,
                "preview_page_limit": (
                    public_policy["public_limit"]
                    if ready
                    else None
                ),
                "preview_policy": public_policy,
            }
        )

        if not ready:
            result["preview_url"] = ""

        chapters = result.get("chapters")
        if isinstance(chapters, list):
            result["chapters"] = [
                self._strip_chapter_preview(chapter)
                for chapter in chapters
            ]

        return result

    def _rewrite_payload(
        self,
        kind: str,
        slug: str,
        payload: Any,
        policy: dict[str, Any] | None,
    ) -> Any:
        if kind == "manifest":
            if not isinstance(payload, dict) or policy is None:
                return payload

            return self._apply_manifest_policy(
                payload,
                policy,
            )

        if kind == "book_detail":
            if not isinstance(payload, dict) or policy is None:
                return payload

            return self._apply_book_policy(
                payload,
                policy,
            )

        if kind == "book_list":
            if isinstance(payload, list):
                rewritten = []

                for item in payload:
                    if not isinstance(item, dict):
                        rewritten.append(item)
                        continue

                    item_slug = str(item.get("slug") or "")
                    item_policy = self._load_policy(item_slug)

                    rewritten.append(
                        self._apply_book_policy(
                            item,
                            item_policy,
                        )
                        if item_policy is not None
                        else item
                    )

                return rewritten

            if (
                isinstance(payload, dict)
                and isinstance(payload.get("books"), list)
            ):
                result = dict(payload)
                result["books"] = self._rewrite_payload(
                    "book_list",
                    "",
                    result["books"],
                    None,
                )
                return result

        return payload

    @staticmethod
    async def _send_json(
        send,
        *,
        status: int,
        payload: dict[str, Any],
    ) -> None:
        body = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")

        headers = [
            (b"content-type", b"application/json"),
            (
                b"content-length",
                str(len(body)).encode("ascii"),
            ),
            (b"cache-control", b"no-store"),
        ]

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )

    async def __call__(
        self,
        scope,
        receive,
        send,
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method") not in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        classified = self._classify(path)

        if classified is None:
            await self.app(scope, receive, send)
            return

        kind, slug = classified
        policy = (
            self._load_policy(slug)
            if slug
            else None
        )

        if (
            kind == "reader_content"
            and policy is not None
            and policy.get("ready") is not True
        ):
            await self._send_json(
                send,
                status=503,
                payload={
                    "detail": "PREVIEW_NOT_READY",
                    "preview_policy": self._public_policy(
                        policy
                    ),
                },
            )
            return

        # Prevent inner gzip middleware from obscuring JSON before this
        # security boundary evaluates it.
        downstream_scope = dict(scope)
        downstream_scope["headers"] = [
            (name, value)
            for name, value in scope.get("headers", [])
            if name.lower() != b"accept-encoding"
        ]

        captured: list[dict[str, Any]] = []

        async def capture(message):
            captured.append(message)

        await self.app(
            downstream_scope,
            receive,
            capture,
        )

        start_message = next(
            (
                message
                for message in captured
                if message.get("type")
                == "http.response.start"
            ),
            None,
        )

        body_messages = [
            message
            for message in captured
            if message.get("type")
            == "http.response.body"
        ]

        if start_message is None:
            for message in captured:
                await send(message)
            return

        status = int(start_message.get("status", 500))

        headers = list(
            start_message.get("headers", [])
        )

        content_type = ""

        for name, value in headers:
            if name.lower() == b"content-type":
                content_type = value.decode(
                    "latin-1"
                ).lower()

        body = b"".join(
            message.get("body", b"")
            for message in body_messages
        )

        should_rewrite = (
            status == 200
            and "application/json" in content_type
            and bool(body)
            and (
                policy is not None
                or kind == "book_list"
            )
        )

        if not should_rewrite:
            for message in captured:
                await send(message)
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            for message in captured:
                await send(message)
            return

        rewritten = self._rewrite_payload(
            kind,
            slug,
            payload,
            policy,
        )

        rewritten_body = json.dumps(
            rewritten,
            separators=(",", ":"),
        ).encode("utf-8")

        filtered_headers = [
            (name, value)
            for name, value in headers
            if name.lower()
            not in {
                b"content-length",
                b"content-encoding",
                b"etag",
            }
        ]

        filtered_headers.append(
            (
                b"content-length",
                str(len(rewritten_body)).encode("ascii"),
            )
        )

        filtered_headers.append(
            (b"cache-control", b"no-store")
        )

        await send(
            {
                **start_message,
                "headers": filtered_headers,
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": (
                    b""
                    if scope.get("method") == "HEAD"
                    else rewritten_body
                ),
                "more_body": False,
            }
        )
PY

###############################################################################
# Controlled policy: three canonical pages configured, not yet ready.
###############################################################################

cat > "$POLICY_FILE" <<'JSON'
{
  "schema_version": "canonical-page-preview-v1",
  "unit": "canonical_page",
  "configured_public_limit": 3,
  "public_limit": 3,
  "enforced_by": "server",
  "ready": false,
  "status": "BLOCKED_PENDING_CANONICAL_PAGE_GENERATION"
}
JSON

###############################################################################
# Register middleware after app creation.
###############################################################################

SERVER_FILE="$SERVER_FILE" python3 <<'PY'
from pathlib import Path
import os
import re

path = Path(os.environ["SERVER_FILE"])
text = path.read_text(encoding="utf-8")

if not re.search(r"\bapp\s*=", text):
    raise SystemExit(
        "ERROR: Could not find the FastAPI app object in backend/server.py"
    )

start_marker = "# BEGIN PREVIEW POLICY GATE"
end_marker = "# END PREVIEW POLICY GATE"

block = r'''
# BEGIN PREVIEW POLICY GATE
from pathlib import Path as _PreviewPolicyPath

try:
    from .preview_policy_gate import PreviewPolicyGate
except ImportError:
    from preview_policy_gate import PreviewPolicyGate

app.add_middleware(
    PreviewPolicyGate,
    policy_root=str(
        _PreviewPolicyPath(__file__).resolve().parent
        / "data"
        / "controlled_publications"
    ),
)
# END PREVIEW POLICY GATE
'''

if start_marker in text and end_marker in text:
    start = text.index(start_marker)
    line_start = text.rfind("\n", 0, start) + 1
    end = text.index(end_marker, start) + len(end_marker)

    text = (
        text[:line_start]
        + block.lstrip("\n")
        + text[end:]
    )
else:
    text = text.rstrip() + "\n\n" + block.lstrip("\n")

path.write_text(text, encoding="utf-8")
print("Registered PreviewPolicyGate in backend/server.py")
PY

###############################################################################
# Validation
###############################################################################

python3 -m py_compile \
  "$SERVER_FILE" \
  "$MIDDLEWARE_FILE"

python3 -m json.tool "$POLICY_FILE" >/dev/null

echo
echo "PREVIEW_POLICY_GATE_INSTALLED"
echo "Policy: $POLICY_FILE"
echo "Backups: $BACKUP_DIR"
