"""Private-safe stdio test bridge to the REAL lease service and in-memory DB.

No network listener, credentials, production database or imported HTTP server.
Used only by scripts/test_reader_preparation_browser.mjs.
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone

from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
import backend.reading_pass_service as module
from backend.tests.test_reading_pass_service_concurrency import Database, Client


async def main():
    db = Database(balance=600)
    origin = datetime.now(timezone.utc)
    current = origin
    module._now = lambda: current
    slug = "reader-preparation-fixture"
    db.reader_segment_activation_state.rows.append({"book_slug": slug, "active_segmentation_version": "fixture-v1", "generation": 1})
    db.reader_segment_manifests.rows.append({"book_slug": slug, "segmentation_version": "fixture-v1", "version": "fixture-manifest-v1", "status": "active"})
    service = module.ReadingPassService(db=db, client=Client(), config=ReadingPassConfig(), token_secret="isolated-synthetic-secret")
    print(json.dumps({"ready": True, "epoch_ms": origin.timestamp() * 1000}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        try:
            action = request["action"]
            args = request.get("args", {})
            if action == "clock":
                current = origin + timedelta(seconds=float(args["seconds"]))
                result = {"seconds": args["seconds"]}
            elif action == "start":
                result = await service.start_session(user_id="user-1", auth_session_id="auth-1", device_id="fixture-device", device_label="Synthetic browser", content_type="text", content_id=slug,
                    scope={"canonical_page_index": 75, "segmentation_version": "fixture-v1", "manifest_version": "fixture-manifest-v1", "authority_activation_generation": 1}, prepare_text=True)
            elif action == "renew":
                result = await service.renew_lease(user_id="user-1", auth_session_id="auth-1", **args)
            elif action == "authorize":
                await service.authorize(user_id="user-1", auth_session_id="auth-1", content_type="text", content_id=slug, **args)
                result = {"authorized": True}
            elif action == "end":
                result = await service.end_session(user_id="user-1", auth_session_id="auth-1", **args)
            elif action == "state":
                result = {"session_id": db.reading_pass_sessions.rows[0]["id"] if db.reading_pass_sessions.rows else None,
                    "balance": db.users.rows[0]["reading_seconds_balance"], "debit": sum(row["debit"] for row in db.wallet_ledger.rows),
                    "sessions": [{key: row.get(key) for key in ("status", "text_phase", "billing_active", "seconds_consumed", "ended_reason")} for row in db.reading_pass_sessions.rows]}
            else:
                raise ValueError("Unknown synthetic fixture action")
            print(json.dumps({"id": request["id"], "result": result}, default=str), flush=True)
        except ReadingPassError as error:
            print(json.dumps({"id": request["id"], "error": {"code": error.code, "status": error.status_code, "message": str(error)}}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
