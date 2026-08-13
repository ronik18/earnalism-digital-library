"""MongoDB-backed Reading Pass ledger and lease service.

Every balance mutation and lease transition is committed in one MongoDB
transaction.  The service stores only a keyed fingerprint of the opaque lease
token and treats MongoDB uniqueness constraints as the cross-instance lock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
import uuid
from typing import Any, Mapping, Optional

try:  # package import
    from .domain.reading_pass import (
        ReadingPassConfig,
        ReadingPassError,
        ensure_utc,
        lease_expiry,
        safe_seconds,
        server_billable_seconds,
        token_fingerprint,
    )
except ImportError:  # production-style import from backend cwd
    from domain.reading_pass import (  # type: ignore
        ReadingPassConfig,
        ReadingPassError,
        ensure_utc,
        lease_expiry,
        safe_seconds,
        server_billable_seconds,
        token_fingerprint,
    )


ACTIVE_SESSION_STATUSES = {"active", "paused"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return ensure_utc(value).isoformat()


class ReadingPassService:
    def __init__(self, *, db, client, config: ReadingPassConfig, token_secret: str) -> None:
        self.db = db
        self.client = client
        self.config = config
        self.token_secret = token_secret

    async def _transaction(self, operation):
        """Run an operation with bounded retry for transient transaction errors."""

        last_error: Optional[BaseException] = None
        for attempt in range(3):
            mongo_session = await self.client.start_session()
            async with mongo_session:
                # Lightweight test doubles use the transaction context directly.
                # Production sessions expose explicit commit/abort methods, which
                # let UnknownTransactionCommitResult retry the same commit instead
                # of replaying a transaction that may already have committed.
                if not hasattr(mongo_session, "commit_transaction"):
                    async with mongo_session.start_transaction():
                        return await operation(mongo_session)
                mongo_session.start_transaction()
                try:
                    result = await operation(mongo_session)
                except Exception as exc:
                    last_error = exc
                    if getattr(mongo_session, "in_transaction", False):
                        await mongo_session.abort_transaction()
                    if (
                        attempt < 2
                        and getattr(exc, "has_error_label", lambda _label: False)("TransientTransactionError")
                    ):
                        continue
                    raise
                for commit_attempt in range(3):
                    try:
                        await mongo_session.commit_transaction()
                        return result
                    except Exception as exc:
                        last_error = exc
                        unknown_commit = getattr(exc, "has_error_label", lambda _label: False)(
                            "UnknownTransactionCommitResult"
                        )
                        if unknown_commit and commit_attempt < 2:
                            continue
                        transient = getattr(exc, "has_error_label", lambda _label: False)(
                            "TransientTransactionError"
                        )
                        if transient and attempt < 2:
                            break
                        raise
        assert last_error is not None
        raise last_error

    async def wallet_state(self, user_id: str) -> dict[str, Any]:
        user = await self.db.users.find_one(
            {"id": user_id, "role": "user"},
            {"_id": 0, "reading_seconds_balance": 1, "wallet_seconds": 1, "status": 1},
        )
        if not user:
            raise ReadingPassError("AUTH_REQUIRED", 401, "A member account is required.")
        balance = safe_seconds(int(user.get("reading_seconds_balance", user.get("wallet_seconds", 0)) or 0))
        active = await self.db.reading_pass_sessions.find_one(
            {"user_id": user_id, "status": {"$in": list(ACTIVE_SESSION_STATUSES)}},
            {"_id": 0, "lease_token_hash": 0},
        )
        return {
            "balance_seconds": balance,
            "status": user.get("status", "active"),
            "active_session": self._public_session(active) if active else None,
        }

    @staticmethod
    def _public_session(session: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
        if not session:
            return None
        return {
            "session_id": session.get("id", ""),
            "device_id": session.get("device_id", ""),
            "device_label": session.get("device_label", ""),
            "content_type": session.get("content_type", ""),
            "content_id": session.get("content_id", ""),
            "status": session.get("status", "ended"),
            "lease_version": int(session.get("lease_version", 0) or 0),
            "lease_expires_at": _iso(session["lease_expires_at"]) if session.get("lease_expires_at") else None,
            "last_sequence": int(session.get("last_sequence", 0) or 0),
        }

    async def _audit(self, event: str, *, session, document: Mapping[str, Any]) -> None:
        await self.db.reading_pass_audit.insert_one(
            {
                "id": str(uuid.uuid4()),
                "event": event,
                "created_at": _now(),
                **dict(document),
            },
            session=session,
        )

    async def _settle_terminal_session(
        self,
        *,
        mongo_session,
        session_doc: Mapping[str, Any],
        now: datetime,
        terminal_status: str,
        reason: str,
    ) -> tuple[int, int]:
        """Settle the final server-timed interval and release the account lock."""

        user_id = str(session_doc.get("user_id") or "")
        session_id = str(session_doc.get("id") or "")
        current_version = int(session_doc.get("lease_version", 0) or 0)
        billable = server_billable_seconds(
            last_billed_at=session_doc.get("last_billed_at") or session_doc.get("lease_issued_at") or now,
            lease_expires_at=session_doc.get("lease_expires_at") or now,
            now=now,
            active=bool(session_doc.get("billing_active", session_doc.get("status") == "active")),
            config=self.config,
        )
        balance = await self._balance(user_id, mongo_session)
        debit = min(balance, billable)
        balance_after = balance - debit
        if debit:
            updated_user = await self.db.users.update_one(
                {"id": user_id, "role": "user", "reading_seconds_balance": {"$gte": debit}},
                {"$inc": {"reading_seconds_balance": -debit, "wallet_seconds": -debit}},
                session=mongo_session,
            )
            if updated_user.modified_count != 1:
                raise ReadingPassError("BALANCE_EXHAUSTED", 403, "Reading Pass time is exhausted.", balance_seconds=0)
            await self._append_time_debit(
                mongo_session=mongo_session,
                user_id=user_id,
                session_id=session_id,
                seconds=debit,
                balance_after=balance_after,
                idempotency_key=f"terminal:{session_id}:{current_version}:{terminal_status}",
                content_type=str(session_doc.get("content_type") or ""),
                content_id=str(session_doc.get("content_id") or ""),
            )
        updated_session = await self.db.reading_pass_sessions.update_one(
            {
                "id": session_id,
                "lease_version": current_version,
                "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
            },
            {
                "$set": {
                    "status": terminal_status,
                    "ended_at": now,
                    "ended_reason": reason,
                    "lease_expires_at": now,
                    "last_billed_at": now,
                    "billing_active": False,
                    "updated_at": now,
                },
                "$inc": {"seconds_consumed": debit},
                "$unset": {"active_lock": ""},
            },
            session=mongo_session,
        )
        if updated_session.modified_count != 1:
            raise ReadingPassError("LEASE_EXPIRED", 409, "The Reading Pass lease changed concurrently.")
        return debit, balance_after

    async def start_session(
        self,
        *,
        user_id: str,
        auth_session_id: str,
        device_id: str,
        device_label: str,
        content_type: str,
        content_id: str,
        scope: Mapping[str, Any],
        transfer: bool = False,
    ) -> dict[str, Any]:
        content_kind = str(content_type or "").lower()
        if content_kind not in {"text", "audio"}:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 403, "Unsupported protected content type.")
        token = secrets.token_urlsafe(32)
        token_hash = token_fingerprint(token, self.token_secret)
        now = _now()

        async def operation(mongo_session):
            user = await self.db.users.find_one(
                {"id": user_id, "role": "user"},
                {"_id": 0, "reading_seconds_balance": 1, "wallet_seconds": 1, "status": 1},
                session=mongo_session,
            )
            if not user or user.get("status") == "blocked":
                raise ReadingPassError("AUTH_REQUIRED", 401, "A valid member session is required.")
            balance = safe_seconds(int(user.get("reading_seconds_balance", user.get("wallet_seconds", 0)) or 0))
            if balance <= 0:
                raise ReadingPassError("PASS_REQUIRED", 403, "A positive Reading Pass balance is required.", balance_seconds=0)

            active = await self.db.reading_pass_sessions.find_one(
                {"user_id": user_id, "status": {"$in": list(ACTIVE_SESSION_STATUSES)}},
                {"_id": 0},
                session=mongo_session,
            )
            if active and now > ensure_utc(active.get("lease_expires_at", now)) + timedelta(
                seconds=self.config.reconnect_grace_seconds
            ):
                await self._settle_terminal_session(
                    mongo_session=mongo_session,
                    session_doc=active,
                    now=now,
                    terminal_status="expired",
                    reason="lease_timeout_before_new_session",
                )
                await self._audit(
                    "session_expired",
                    session=mongo_session,
                    document={"user_id": user_id, "session_id": active["id"]},
                )
                active = None
            if active and not transfer:
                raise ReadingPassError(
                    "SESSION_ACTIVE_ELSEWHERE",
                    409,
                    "Reading Pass time is active on another device or tab.",
                    active_session=self._public_session(active),
                )
            if active:
                await self._settle_terminal_session(
                    mongo_session=mongo_session,
                    session_doc=active,
                    now=now,
                    terminal_status="transferred",
                    reason="controlled_transfer",
                )
                await self._audit(
                    "device_transfer",
                    session=mongo_session,
                    document={"user_id": user_id, "old_session_id": active["id"], "device_id": device_id},
                )

            balance = await self._balance(user_id, mongo_session)
            if balance <= 0:
                # Commit the old session's final debit and lock release, then
                # surface the denial outside the transaction.
                return {"terminal_only": True, "balance_seconds": 0}

            session_id = str(uuid.uuid4())
            expires_at = lease_expiry(now, balance, self.config)
            document = {
                "id": session_id,
                "user_id": user_id,
                "auth_session_id": auth_session_id,
                "device_id": device_id,
                "device_label": device_label[:120],
                "content_type": content_kind,
                "content_id": str(content_id)[:200],
                "scope": dict(scope),
                "status": "active",
                "active_lock": user_id,
                "billing_active": content_kind == "text",
                "lease_token_hash": token_hash,
                "lease_version": 1,
                "lease_issued_at": now,
                "lease_expires_at": expires_at,
                "last_billed_at": now,
                "last_heartbeat_at": now,
                "last_sequence": 0,
                "seconds_consumed": 0,
                "created_at": now,
                "updated_at": now,
            }
            await self.db.reading_pass_sessions.insert_one(document, session=mongo_session)
            await self.db.reading_pass_devices.update_one(
                {"user_id": user_id, "device_id": device_id},
                {
                    "$set": {
                        "device_label": device_label[:120],
                        "auth_session_id": auth_session_id,
                        "last_seen_at": now,
                        "revoked_at": None,
                    },
                    "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now},
                },
                upsert=True,
                session=mongo_session,
            )
            await self._audit(
                "metered_session_started",
                session=mongo_session,
                document={
                    "user_id": user_id,
                    "session_id": session_id,
                    "device_id": device_id,
                    "content_type": content_kind,
                    "content_id": str(content_id)[:200],
                },
            )
            return {
                "session_id": session_id,
                "lease_token": token,
                "content_type": content_kind,
                "content_id": str(content_id)[:200],
                "lease_version": 1,
                "lease_expires_at": _iso(expires_at),
                "heartbeat_seconds": self.config.heartbeat_seconds,
                "maximum_lease_seconds": self.config.maximum_lease_seconds,
                "balance_seconds": balance,
                "status": "Running",
            }

        result = await self._transaction(operation)
        if result.get("terminal_only"):
            raise ReadingPassError(
                "PASS_REQUIRED",
                403,
                "A positive Reading Pass balance is required.",
                balance_seconds=0,
            )
        return result

    async def renew_lease(
        self,
        *,
        user_id: str,
        auth_session_id: str,
        session_id: str,
        lease_token: str,
        lease_version: int,
        sequence: int,
        idempotency_key: str,
        active: bool,
        playback_state: str = "",
    ) -> dict[str, Any]:
        if not idempotency_key or len(idempotency_key) > 160:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A bounded idempotency key is required.")
        if sequence < 1:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "Heartbeat sequence must be positive.")
        token_hash = token_fingerprint(lease_token, self.token_secret)
        existing = await self.db.reading_pass_heartbeats.find_one(
            {"session_id": session_id, "user_id": user_id, "idempotency_key": idempotency_key},
            {"_id": 0, "response": 1},
        )
        if existing:
            return {**existing.get("response", {}), "lease_token": lease_token, "duplicate": True}
        now = _now()

        async def operation(mongo_session):
            session_doc = await self.db.reading_pass_sessions.find_one(
                {"id": session_id, "user_id": user_id}, {"_id": 0}, session=mongo_session
            )
            if not session_doc or session_doc.get("status") not in ACTIVE_SESSION_STATUSES:
                raise ReadingPassError("LEASE_EXPIRED", 403, "The Reading Pass lease is no longer active.")
            if session_doc.get("auth_session_id") != auth_session_id:
                raise ReadingPassError("LEASE_EXPIRED", 403, "The authenticated session no longer owns this lease.")
            if not hmac_compare(session_doc.get("lease_token_hash", ""), token_hash):
                await self._audit(
                    "suspected_replay",
                    session=mongo_session,
                    document={"user_id": user_id, "session_id": session_id, "reason": "lease_token_mismatch"},
                )
                raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 403, "The Reading Pass lease is invalid.")
            current_version = int(session_doc.get("lease_version", 0) or 0)
            last_sequence = int(session_doc.get("last_sequence", 0) or 0)
            if lease_version != current_version or sequence <= last_sequence:
                return {
                    "session_id": session_id,
                    "lease_token": lease_token,
                    "lease_version": current_version,
                    "lease_expires_at": _iso(session_doc["lease_expires_at"]),
                    "balance_seconds": await self._balance(user_id, mongo_session),
                    "deducted_seconds": 0,
                    "status": "Stale",
                    "stale": True,
                }
            grace_deadline = ensure_utc(session_doc["lease_expires_at"]) + timedelta(seconds=self.config.reconnect_grace_seconds)
            if now > grace_deadline:
                await self.db.reading_pass_sessions.update_one(
                    {"id": session_id, "lease_version": current_version},
                    {
                        "$set": {"status": "expired", "ended_at": now, "ended_reason": "lease_timeout"},
                        "$unset": {"active_lock": ""},
                    },
                    session=mongo_session,
                )
                await self._audit(
                    "session_expired",
                    session=mongo_session,
                    document={"user_id": user_id, "session_id": session_id},
                )
                raise ReadingPassError("LEASE_EXPIRED", 403, "The Reading Pass lease expired.")

            genuinely_active = bool(active)
            if session_doc.get("content_type") == "audio":
                genuinely_active = genuinely_active and str(playback_state or "").lower() == "playing"
            previously_active = bool(
                session_doc.get("billing_active", session_doc.get("status") == "active")
            )
            billable = server_billable_seconds(
                last_billed_at=session_doc.get("last_billed_at") or session_doc["lease_issued_at"],
                lease_expires_at=session_doc["lease_expires_at"],
                now=now,
                active=previously_active,
                config=self.config,
            )
            balance = await self._balance(user_id, mongo_session)
            debit = min(balance, billable)
            balance_after = balance - debit
            next_version = current_version + 1
            buffering = (
                session_doc.get("content_type") == "audio"
                and str(playback_state or "").lower() == "buffering"
            )
            next_status = (
                "exhausted"
                if balance_after <= 0
                else "active"
                if genuinely_active or buffering
                else "paused"
            )
            next_expiry = lease_expiry(now, balance_after, self.config) if next_status == "active" else now

            if debit:
                updated = await self.db.users.update_one(
                    {"id": user_id, "role": "user", "reading_seconds_balance": {"$gte": debit}},
                    {"$inc": {"reading_seconds_balance": -debit, "wallet_seconds": -debit}},
                    session=mongo_session,
                )
                if updated.modified_count != 1:
                    raise ReadingPassError("BALANCE_EXHAUSTED", 403, "Reading Pass time is exhausted.", balance_seconds=0)
                await self._append_time_debit(
                    mongo_session=mongo_session,
                    user_id=user_id,
                    session_id=session_id,
                    seconds=debit,
                    balance_after=balance_after,
                    idempotency_key=f"heartbeat:{session_id}:{sequence}",
                    content_type=str(session_doc.get("content_type") or ""),
                    content_id=str(session_doc.get("content_id") or ""),
                )

            session_update: dict[str, Any] = {
                "$set": {
                    "status": next_status,
                    "lease_version": next_version,
                    "lease_issued_at": now,
                    "lease_expires_at": next_expiry,
                    "last_billed_at": now,
                    "last_heartbeat_at": now,
                    "last_sequence": sequence,
                    "updated_at": now,
                    "billing_active": genuinely_active and balance_after > 0,
                },
                "$inc": {"seconds_consumed": debit},
            }
            if next_status in ACTIVE_SESSION_STATUSES:
                session_update["$set"]["active_lock"] = user_id
            else:
                session_update["$unset"] = {"active_lock": ""}
            updated_session = await self.db.reading_pass_sessions.update_one(
                {
                    "id": session_id,
                    "lease_version": current_version,
                    "last_sequence": last_sequence,
                    "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
                },
                session_update,
                session=mongo_session,
            )
            if updated_session.modified_count != 1:
                raise ReadingPassError("LEASE_EXPIRED", 409, "The Reading Pass lease changed concurrently.")

            public_status = (
                "Exhausted"
                if next_status == "exhausted"
                else "Connecting"
                if buffering
                else "Running"
                if next_status == "active"
                else "Paused"
            )
            response = {
                "session_id": session_id,
                "content_type": str(session_doc.get("content_type") or ""),
                "content_id": str(session_doc.get("content_id") or ""),
                "lease_version": next_version,
                "lease_expires_at": _iso(next_expiry),
                "balance_seconds": balance_after,
                "deducted_seconds": debit,
                "status": public_status,
            }
            await self.db.reading_pass_heartbeats.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user_id,
                    "idempotency_key": idempotency_key,
                    "sequence": sequence,
                    "lease_version": lease_version,
                    "response": response,
                    "created_at": now,
                },
                session=mongo_session,
            )
            await self._audit(
                "session_buffering" if buffering else "lease_renewed" if next_status == "active" else "session_paused",
                session=mongo_session,
                document={
                    "user_id": user_id,
                    "session_id": session_id,
                    "deducted_seconds": debit,
                    "balance_seconds": balance_after,
                },
            )
            return {**response, "lease_token": lease_token}

        return await self._transaction(operation)

    async def _balance(self, user_id: str, mongo_session) -> int:
        user = await self.db.users.find_one(
            {"id": user_id, "role": "user"},
            {"_id": 0, "reading_seconds_balance": 1, "wallet_seconds": 1},
            session=mongo_session,
        )
        if not user:
            raise ReadingPassError("AUTH_REQUIRED", 401, "A member account is required.")
        return safe_seconds(int(user.get("reading_seconds_balance", user.get("wallet_seconds", 0)) or 0))

    async def _append_time_debit(
        self,
        *,
        mongo_session,
        user_id: str,
        session_id: str,
        seconds: int,
        balance_after: int,
        idempotency_key: str,
        content_type: str,
        content_id: str,
    ) -> None:
        now = _now()
        transaction_id = str(uuid.uuid4())
        await self.db.wallet_transactions.insert_one(
            {
                "id": transaction_id,
                "user_id": user_id,
                "type": "consume",
                "seconds": -int(seconds),
                "reason": f"Reading Pass {content_type} consumption",
                "created_at": _iso(now),
                "actor": "reading-pass-v2",
                "session_id": session_id,
            },
            session=mongo_session,
        )
        await self.db.wallet_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "action": "time_debit",
                "event_type": "TIME_DEBIT",
                "signed_seconds": -int(seconds),
                "debit": int(seconds),
                "credit": 0,
                "timestamp": _iso(now),
                "reason": f"Protected {content_type} lease consumption",
                "actor": "reading-pass-v2",
                "creating_service": "earnalism-api",
                "balance_after": int(balance_after),
                "source_transaction_id": transaction_id,
                "idempotency_key": idempotency_key,
                "metadata": {"content_type": content_type, "content_id": content_id[:200]},
            },
            session=mongo_session,
        )

    async def authorize(
        self,
        *,
        user_id: str,
        auth_session_id: str,
        session_id: str,
        lease_token: str,
        content_type: str,
        content_id: str,
    ) -> dict[str, Any]:
        session_doc = await self.db.reading_pass_sessions.find_one(
            {"id": session_id, "user_id": user_id}, {"_id": 0}
        )
        now = _now()
        if (
            not session_doc
            or session_doc.get("status") != "active"
            or session_doc.get("auth_session_id") != auth_session_id
            or session_doc.get("content_type") != content_type
            or session_doc.get("content_id") != content_id
            or not hmac_compare(session_doc.get("lease_token_hash", ""), token_fingerprint(lease_token, self.token_secret))
            or ensure_utc(session_doc.get("lease_expires_at", now)) <= now
        ):
            raise ReadingPassError("LEASE_EXPIRED", 403, "A current Reading Pass lease is required.")
        return session_doc

    async def authorize_media_credential(
        self,
        *,
        session_id: str,
        lease_token: str,
        content_type: str,
        content_id: str,
    ) -> dict[str, Any]:
        """Authorize a short-lived HttpOnly media credential.

        Native media elements cannot attach an Authorization header.  The
        opaque lease cookie is therefore re-bound here to the still-active
        account login and to the exact content identifier before any protected
        byte is served.
        """

        now = _now()
        session_doc = await self.db.reading_pass_sessions.find_one(
            {"id": session_id}, {"_id": 0}
        )
        if (
            not session_doc
            or session_doc.get("status") != "active"
            or session_doc.get("content_type") != content_type
            or session_doc.get("content_id") != content_id
            or not hmac_compare(
                session_doc.get("lease_token_hash", ""),
                token_fingerprint(lease_token, self.token_secret),
            )
            or ensure_utc(session_doc.get("lease_expires_at", now)) <= now
        ):
            raise ReadingPassError("LEASE_EXPIRED", 403, "A current Reading Pass lease is required.")
        auth_session = await self.db.user_sessions.find_one(
            {
                "id": session_doc.get("auth_session_id"),
                "user_id": session_doc.get("user_id"),
                "status": "active",
            },
            {"_id": 0, "idle_expires_at": 1, "absolute_expires_at": 1},
        )
        user = await self.db.users.find_one(
            {"id": session_doc.get("user_id"), "role": "user"},
            {"_id": 0, "status": 1},
        )
        if (
            not auth_session
            or not user
            or user.get("status") == "blocked"
            or ensure_utc(auth_session.get("idle_expires_at", now)) <= now
            or ensure_utc(auth_session.get("absolute_expires_at", now)) <= now
        ):
            raise ReadingPassError("AUTH_REQUIRED", 401, "The member session is no longer active.")
        return session_doc

    async def end_session(self, *, user_id: str, auth_session_id: str, session_id: str, reason: str = "user_end") -> dict[str, Any]:
        now = _now()

        async def operation(mongo_session):
            session_doc = await self.db.reading_pass_sessions.find_one(
                {
                    "id": session_id,
                    "user_id": user_id,
                    "auth_session_id": auth_session_id,
                    "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
                },
                {"_id": 0},
                session=mongo_session,
            )
            if not session_doc:
                return {"ended": False, "session_id": session_id, "deducted_seconds": 0}
            debit, balance_after = await self._settle_terminal_session(
                mongo_session=mongo_session,
                session_doc=session_doc,
                now=now,
                terminal_status="ended",
                reason=str(reason or "user_end")[:80],
            )
            await self._audit(
                "metered_session_ended",
                session=mongo_session,
                document={
                    "user_id": user_id,
                    "session_id": session_id,
                    "deducted_seconds": debit,
                    "balance_seconds": balance_after,
                },
            )
            return {
                "ended": True,
                "session_id": session_id,
                "deducted_seconds": debit,
                "balance_seconds": balance_after,
            }

        return await self._transaction(operation)

    async def revoke_auth_session(self, *, user_id: str, auth_session_id: str) -> dict[str, Any]:
        """Revoke a login device and settle any metered interval atomically."""

        now = _now()

        async def operation(mongo_session):
            auth_session = await self.db.user_sessions.find_one(
                {"id": auth_session_id, "user_id": user_id},
                {"_id": 0, "id": 1},
                session=mongo_session,
            )
            device = await self.db.reading_pass_devices.find_one(
                {"user_id": user_id, "auth_session_id": auth_session_id},
                {"_id": 0},
                session=mongo_session,
            )
            if not auth_session and not device:
                raise ReadingPassError("DEVICE_NOT_FOUND", 404, "This device session was not found.")
            sessions = await self.db.reading_pass_sessions.find(
                {
                    "user_id": user_id,
                    "auth_session_id": auth_session_id,
                    "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
                },
                {"_id": 0},
                session=mongo_session,
            ).to_list(10)
            total_debit = 0
            balance_after: Optional[int] = None
            for session_doc in sessions:
                debit, balance_after = await self._settle_terminal_session(
                    mongo_session=mongo_session,
                    session_doc=session_doc,
                    now=now,
                    terminal_status="revoked",
                    reason="member_device_revoke",
                )
                total_debit += debit
            await self.db.user_sessions.update_one(
                {"id": auth_session_id, "user_id": user_id},
                {"$set": {"status": "revoked", "revoked_at": now, "revoked_reason": "member_device_revoke"}},
                session=mongo_session,
            )
            await self.db.reading_pass_devices.update_one(
                {"user_id": user_id, "auth_session_id": auth_session_id},
                {"$set": {"revoked_at": now}},
                session=mongo_session,
            )
            await self._audit(
                "device_revoked",
                session=mongo_session,
                document={
                    "user_id": user_id,
                    "device_id": str((device or {}).get("device_id") or ""),
                    "auth_session_id": auth_session_id,
                    "deducted_seconds": total_debit,
                },
            )
            return {
                "revoked": True,
                "session_id": auth_session_id,
                "device_id": str((device or {}).get("device_id") or ""),
                "deducted_seconds": total_debit,
                "balance_seconds": balance_after,
            }

        return await self._transaction(operation)

    async def save_position(
        self,
        *,
        user_id: str,
        content_type: str,
        content_id: str,
        position: Mapping[str, Any],
        version: int,
    ) -> dict[str, Any]:
        if content_type not in {"text", "audio"}:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "Unsupported position type.")
        if content_type == "text":
            page_index = int(position.get("canonical_page_index", 0) or 0)
            if page_index < 1 or page_index > 10_000_000:
                raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A valid canonical page is required.")
            safe_position = {
                "canonical_page_index": page_index,
                "chapter_id": str(position.get("chapter_id") or "")[:200],
            }
        else:
            try:
                media_position = float(position.get("media_position_seconds", 0) or 0)
            except (TypeError, ValueError) as exc:
                raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A valid media position is required.") from exc
            if not 0 <= media_position <= 1_000_000_000:
                raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A valid media position is required.")
            safe_position = {"media_position_seconds": round(media_position, 3)}

        async def operation(mongo_session):
            now = _now()
            identity = {"user_id": user_id, "content_type": content_type, "content_id": content_id}
            current = await self.db.reading_pass_positions.find_one(
                identity, {"_id": 0}, session=mongo_session
            )
            current_version = int((current or {}).get("version", 0) or 0)
            if version < current_version:
                return {**current, "stale": True}
            next_version = max(version, current_version) + 1
            query = {**identity, **({"version": current_version} if current else {})}
            updated = await self.db.reading_pass_positions.update_one(
                query,
                {
                    "$set": {"position": safe_position, "version": next_version, "updated_at": now},
                    "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now},
                },
                upsert=not bool(current),
                session=mongo_session,
            )
            if current and updated.modified_count != 1:
                raise ReadingPassError("POSITION_CONFLICT", 409, "The saved position changed concurrently.")
            return {
                "content_type": content_type,
                "content_id": content_id,
                "position": safe_position,
                "version": next_version,
                "updated_at": _iso(now),
            }

        return await self._transaction(operation)

    async def credit_verified_payment(self, *, intent: Mapping[str, Any], payment_id: str, source: str) -> dict[str, Any]:
        """Credit a verified Razorpay intent exactly once in one transaction."""

        now = _now()
        intent_id = str(intent["id"])
        idempotency_key = f"payment:{intent_id}"
        seconds = safe_seconds(int(intent["minutes"]) * 60)
        user_id = str(intent["user_id"])

        async def operation(mongo_session):
            fresh_intent = await self.db.topup_intents.find_one({"id": intent_id}, {"_id": 0}, session=mongo_session)
            if not fresh_intent:
                raise ReadingPassError("PAYMENT_VERIFICATION_FAILED", 404, "Top-up intent not found.")
            if fresh_intent.get("status") == "credited":
                return fresh_intent
            updated = await self.db.topup_intents.update_one(
                {"id": intent_id, "status": {"$ne": "credited"}},
                {
                    "$set": {
                        "status": "credited",
                        "credited_at": _iso(now),
                        "credited_by": source,
                        "razorpay_payment_id": payment_id or fresh_intent.get("razorpay_payment_id"),
                    }
                },
                session=mongo_session,
            )
            if updated.modified_count != 1:
                return await self.db.topup_intents.find_one({"id": intent_id}, {"_id": 0}, session=mongo_session)
            await self.db.users.update_one(
                {"id": user_id, "role": "user"},
                {"$inc": {"reading_seconds_balance": seconds, "wallet_seconds": seconds}},
                session=mongo_session,
            )
            balance_after = await self._balance(user_id, mongo_session)
            transaction_id = str(uuid.uuid4())
            await self.db.wallet_transactions.insert_one(
                {
                    "id": transaction_id,
                    "user_id": user_id,
                    "type": "credit",
                    "seconds": seconds,
                    "reason": f"Razorpay top-up · {fresh_intent.get('pack_id')} · {fresh_intent.get('minutes')} min",
                    "created_at": _iso(now),
                    "actor": f"razorpay:{source}",
                    "session_id": "",
                },
                session=mongo_session,
            )
            await self.db.wallet_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": "",
                    "action": "topup_credit",
                    "event_type": "PASS_CREDIT",
                    "signed_seconds": seconds,
                    "debit": 0,
                    "credit": seconds,
                    "timestamp": _iso(now),
                    "reason": "Verified Reading Pass purchase",
                    "actor": f"razorpay:{source}",
                    "creating_service": "earnalism-api",
                    "balance_after": balance_after,
                    "source_transaction_id": transaction_id,
                    "idempotency_key": idempotency_key,
                    "metadata": {"topup_intent_id": intent_id, "payment_id": str(payment_id or "")[:120]},
                },
                session=mongo_session,
            )
            await self._audit(
                "pass_credited",
                session=mongo_session,
                document={"user_id": user_id, "intent_id": intent_id, "seconds": seconds, "source": source},
            )
            return await self.db.topup_intents.find_one({"id": intent_id}, {"_id": 0}, session=mongo_session)

        return await self._transaction(operation)


def hmac_compare(left: str, right: str) -> bool:
    return secrets.compare_digest(str(left or ""), str(right or ""))
