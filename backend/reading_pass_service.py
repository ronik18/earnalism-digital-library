"""MongoDB-backed Reading Pass ledger and lease service.

Every balance mutation and lease transition is committed in one MongoDB
transaction.  The service stores only a keyed fingerprint of the opaque lease
token and treats MongoDB uniqueness constraints as the cross-instance lock.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import secrets
import uuid
from typing import Any, Mapping, Optional

from pymongo.errors import DuplicateKeyError

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
                        # A conflicting transaction may still be committing.
                        # Yield with a bounded backoff before opening a fresh
                        # snapshot; immediately replaying the callback can
                        # consume the entire retry budget against that same
                        # in-flight writer.
                        await asyncio.sleep(0.01 * (attempt + 1))
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
                            await asyncio.sleep(0.01 * (attempt + 1))
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

    @staticmethod
    def _text_revocation(state: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
        """Return only a complete, durable text-revocation record.

        A missing record means no separately committed revocation. A malformed
        record is never treated as a successful allow or as a trustworthy
        historical cutoff.
        """

        record = (state or {}).get("text_revocation")
        if record is None:
            return None
        if not isinstance(record, Mapping):
            raise ReadingPassError(
                "CONTENT_AUTHORITY_UNAVAILABLE", 503,
                "Reader availability could not be verified.",
            )
        cutoff = record.get("cutoff_at")
        if (
            record.get("status") != "revoked"
            or not isinstance(record.get("generation"), int)
            or int(record["generation"]) < 1
            or not isinstance(record.get("operation_id"), str)
            or not record["operation_id"]
            or not isinstance(cutoff, datetime)
            or not isinstance(record.get("activation_generation"), int)
            or int(record["activation_generation"]) < 0
            or not isinstance(record.get("segmentation_version"), str)
            or not record["segmentation_version"]
            or not isinstance(record.get("manifest_version"), str)
            or not record["manifest_version"]
        ):
            raise ReadingPassError(
                "CONTENT_AUTHORITY_UNAVAILABLE", 503,
                "Reader availability could not be verified.",
            )
        return dict(record)

    @staticmethod
    def _text_revocation_binding(session_doc: Mapping[str, Any], revocation: Mapping[str, Any]) -> str:
        """Classify a session against one immutable text-revocation record.

        Only a session explicitly bound to the revoked pointer may be charged
        to its server-timed cutoff. A legacy session without all binding fields
        cannot honestly be assigned to this publication, and a fully bound
        retained version is not silently reclassified as the current one.
        """

        scope = session_doc.get("scope")
        if not isinstance(scope, Mapping):
            return "legacy_unbound"
        version = scope.get("segmentation_version")
        manifest = scope.get("manifest_version")
        activation_generation = scope.get("authority_activation_generation")
        if (
            not isinstance(version, str)
            or not version
            or not isinstance(manifest, str)
            or not manifest
            or not isinstance(activation_generation, int)
            or activation_generation < 0
        ):
            return "legacy_unbound"
        if (
            version == revocation["segmentation_version"]
            and manifest == revocation["manifest_version"]
            and activation_generation == revocation["activation_generation"]
        ):
            return "matches_revoked_publication"
        return "different_retained_publication"

    async def _current_text_revocation(self, content_id: str, mongo_session) -> Optional[dict[str, Any]]:
        state = await self.db.reader_segment_activation_state.find_one(
            {"book_slug": content_id},
            {"_id": 0, "text_revocation": 1},
            session=mongo_session,
        )
        return self._text_revocation(state)

    async def _require_text_revocation_operation_index(self) -> None:
        """Refuse a revocation when its cross-title idempotency index is absent.

        ``create_index`` in application startup is a deployment instruction,
        not proof that the running database has accepted the prerequisite.
        The administrative writer therefore checks the concrete unique index
        before it makes any publication or session change.
        """

        try:
            indexes = await self.db.reading_pass_text_revocation_operations.index_information()
        except Exception as exc:
            raise ReadingPassError(
                "REVOCATION_SCHEMA_UNAVAILABLE", 503,
                "The revocation operation schema could not be verified.",
            ) from exc
        required_key = [("operation_id", 1)]
        if not any(
            spec.get("unique") is True
            and list(spec.get("key") or []) == required_key
            and "partialFilterExpression" not in spec
            for spec in indexes.values()
            if isinstance(spec, Mapping)
        ):
            raise ReadingPassError(
                "REVOCATION_SCHEMA_UNAVAILABLE", 503,
                "The revocation operation schema is not ready.",
            )

    async def _mark_text_authority_unavailable(
        self,
        *,
        mongo_session,
        session_doc: Mapping[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Stop new protected use without fabricating a disputed debit.

        This transition is used only when the current file/runtime authority
        cannot establish a historical, server-timed revocation cutoff. It
        releases the active lock and retains an audit trail for later policy
        review; it does not forgive, backdate, or collect time.
        """

        session_id = str(session_doc.get("id") or "")
        user_id = str(session_doc.get("user_id") or "")
        current_version = int(session_doc.get("lease_version", 0) or 0)
        # Preserve the last known accounting and publication boundary before
        # this fail-closed transition overwrites the live lease fields.  This
        # audit record is private, durable, and in the same transaction as the
        # transition; it is evidence for a later accounting decision, not a
        # debit/refund instruction.  ``now`` is the time this transaction
        # observed the missing authority, not a database-commit timestamp.
        scope = session_doc.get("scope") if isinstance(session_doc.get("scope"), Mapping) else {}
        await self._audit(
            "text_authority_unavailable_accounting_bounds",
            session=mongo_session,
            document={
                "user_id": user_id,
                "session_id": session_id,
                "content_id": str(session_doc.get("content_id") or ""),
                "lease_version": current_version,
                "observed_at": now,
                "original_accounting_bounds": {
                    "lease_issued_at": session_doc.get("lease_issued_at"),
                    "last_billed_at": session_doc.get("last_billed_at"),
                    "lease_expires_at": session_doc.get("lease_expires_at"),
                    "last_heartbeat_at": session_doc.get("last_heartbeat_at"),
                    "last_sequence": int(session_doc.get("last_sequence", 0) or 0),
                    "seconds_consumed": int(session_doc.get("seconds_consumed", 0) or 0),
                    "billing_active": bool(session_doc.get("billing_active", session_doc.get("status") == "active")),
                },
                "publication_identity": {
                    "segmentation_version": scope.get("segmentation_version"),
                    "manifest_version": scope.get("manifest_version"),
                    "activation_generation": scope.get("authority_activation_generation"),
                },
            },
        )
        updated = await self.db.reading_pass_sessions.update_one(
            {
                "id": session_id,
                "lease_version": current_version,
                "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
            },
            {
                "$set": {
                    "status": "authority_unavailable",
                    "ended_at": now,
                    "ended_reason": "text_authority_cutoff_unavailable",
                    "lease_expires_at": now,
                    "billing_active": False,
                    "authority_unavailable_at": now,
                    "updated_at": now,
                },
                "$unset": {"active_lock": ""},
            },
            session=mongo_session,
        )
        if updated.modified_count != 1:
            raise ReadingPassError("LEASE_EXPIRED", 409, "The Reading Pass lease changed concurrently.")
        await self._audit(
            "text_authority_unavailable",
            session=mongo_session,
            document={
                "user_id": user_id,
                "session_id": session_id,
                "content_id": str(session_doc.get("content_id") or ""),
                "lease_version": current_version,
                "unsettled_from": session_doc.get("last_billed_at") or session_doc.get("lease_issued_at"),
            },
        )
        return {"session_id": session_id, "balance_seconds": await self._balance(user_id, mongo_session)}

    async def _assert_text_start_authority(
        self,
        *,
        mongo_session,
        content_id: str,
        scope: Mapping[str, Any],
        now: datetime,
    ) -> None:
        """Order a new protected-text lease against the durable revocation writer.

        Current file/runtime reader truth authorizes the route before this
        service is reached. The activation-state touch below gives the durable
        title-level revocation writer a transaction-visible ordering point.
        Historical callers without the new publication binding keep their
        legacy behavior; they cannot be reinterpreted as a newly coordinated
        start.
        """

        generation = scope.get("authority_activation_generation")
        segmentation_version = scope.get("segmentation_version")
        if not isinstance(generation, int) or generation < 0 or not isinstance(segmentation_version, str) or not segmentation_version:
            return
        # Incrementing this fence makes every permitted start a real write,
        # even under a fixed server clock.  The write is deliberately against
        # the same pointer the revocation writer changes, so Mongo's
        # transaction conflict rules order starts and revocations without
        # changing the canonical publication identity.
        updated = await self.db.reader_segment_activation_state.update_one(
            {
                "book_slug": content_id,
                "active_segmentation_version": segmentation_version,
                "generation": generation,
                "text_revocation": {"$exists": False},
            },
            {
                "$set": {"text_authority_last_start_at": now},
                "$inc": {"text_authority_fence": 1},
            },
            session=mongo_session,
        )
        if updated.modified_count == 1:
            return
        state = await self.db.reader_segment_activation_state.find_one(
            {"book_slug": content_id}, {"_id": 0, "text_revocation": 1}, session=mongo_session
        )
        revocation = self._text_revocation(state)
        if revocation:
            raise ReadingPassError("CONTENT_REVOKED", 403, "This protected text is no longer available.")
        raise ReadingPassError(
            "CONTENT_AUTHORITY_UNAVAILABLE", 503,
            "Reader availability could not be verified.",
        )

    async def _settle_terminal_session(
        self,
        *,
        mongo_session,
        session_doc: Mapping[str, Any],
        now: datetime,
        terminal_status: str,
        reason: str,
        billing_cutoff_at: Optional[datetime] = None,
    ) -> tuple[int, int]:
        """Settle the final server-timed interval and release the account lock."""

        user_id = str(session_doc.get("user_id") or "")
        session_id = str(session_doc.get("id") or "")
        current_version = int(session_doc.get("lease_version", 0) or 0)
        billing_cutoff = ensure_utc(billing_cutoff_at or now)
        billable = server_billable_seconds(
            last_billed_at=session_doc.get("last_billed_at") or session_doc.get("lease_issued_at") or now,
            lease_expires_at=session_doc.get("lease_expires_at") or now,
            now=now,
            active=bool(session_doc.get("billing_active", session_doc.get("status") == "active")),
            config=self.config,
            billing_cutoff_at=billing_cutoff,
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
                billing_cutoff_at=billing_cutoff,
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
                    "settlement_at": now,
                    "billing_cutoff_at": billing_cutoff,
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
            if content_kind == "text":
                await self._assert_text_start_authority(
                    mongo_session=mongo_session,
                    content_id=str(content_id),
                    scope=scope,
                    now=now,
                )
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

    async def revoke_text_publication(
        self,
        *,
        book_slug: str,
        expected_activation_generation: int,
        expected_segmentation_version: str,
        expected_manifest_version: str,
        operation_id: str,
        reason: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """Commit one durable text revocation and terminal settlement together.

        The cutoff is assigned from the server clock inside the transaction,
        never accepted from a request. The existing activation-state document
        is the coordinated title-level authority record; its generation and
        active immutable manifest bind the revocation to the reviewed
        publication that the administrator observed before submitting it.
        """

        slug = str(book_slug or "").strip().lower()
        if not slug or len(slug) > 200:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A valid canonical title is required.")
        if not operation_id or len(operation_id) > 160:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A bounded operation id is required.")
        if not reason or len(reason) > 120:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A bounded revocation reason is required.")
        if not actor_id or len(actor_id) > 200:
            raise ReadingPassError("AUTH_REQUIRED", 401, "An administrator identity is required.")
        if (
            not isinstance(expected_activation_generation, int)
            or expected_activation_generation < 0
            or not expected_segmentation_version
            or not expected_manifest_version
        ):
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A complete current publication identity is required.")
        intent = {
            "book_slug": slug,
            "expected_activation_generation": expected_activation_generation,
            "expected_segmentation_version": expected_segmentation_version,
            "expected_manifest_version": expected_manifest_version,
            "reason": reason,
        }

        await self._require_text_revocation_operation_index()

        async def operation(mongo_session):
            previous = await self.db.reading_pass_text_revocation_operations.find_one(
                {"operation_id": operation_id}, {"_id": 0}, session=mongo_session
            )
            if previous:
                if previous.get("intent") != intent:
                    raise ReadingPassError(
                        "REVOCATION_OPERATION_CONFLICT", 409,
                        "The operation id is already bound to a different revocation intent.",
                    )
                return {**dict(previous.get("result") or {}), "duplicate": True}

            state = await self.db.reader_segment_activation_state.find_one(
                {
                    "book_slug": slug,
                    "active_segmentation_version": expected_segmentation_version,
                    "generation": expected_activation_generation,
                },
                {"_id": 0},
                session=mongo_session,
            )
            if not state:
                raise ReadingPassError(
                    "STALE_PUBLICATION_AUTHORITY", 409,
                    "The active canonical publication changed; refresh before revoking it.",
                )
            current_revocation = self._text_revocation(state)
            if current_revocation:
                raise ReadingPassError(
                    "TEXT_PUBLICATION_ALREADY_REVOKED", 409,
                    "This protected text already has a durable revocation record.",
                )
            manifest = await self.db.reader_segment_manifests.find_one(
                {
                    "book_slug": slug,
                    "segmentation_version": expected_segmentation_version,
                    "version": expected_manifest_version,
                    "status": "active",
                },
                {"_id": 0, "version": 1},
                session=mongo_session,
            )
            if not manifest:
                raise ReadingPassError(
                    "STALE_PUBLICATION_AUTHORITY", 409,
                    "The active canonical publication changed; refresh before revoking it.",
                )

            cutoff = _now()
            revocation = {
                "status": "revoked",
                "generation": int(state.get("text_revocation_generation", 0) or 0) + 1,
                "operation_id": operation_id,
                "cutoff_at": cutoff,
                "recorded_at": cutoff,
                "reason": reason,
                "activation_generation": expected_activation_generation,
                "segmentation_version": expected_segmentation_version,
                "manifest_version": expected_manifest_version,
                "actor_id": actor_id,
            }
            ordered = await self.db.reader_segment_activation_state.update_one(
                {
                    "book_slug": slug,
                    "active_segmentation_version": expected_segmentation_version,
                    "generation": expected_activation_generation,
                    "text_revocation": {"$exists": False},
                },
                {
                    "$set": {"text_revocation": revocation, "updated_at": cutoff},
                    "$inc": {"text_revocation_generation": 1},
                },
                session=mongo_session,
            )
            if ordered.modified_count != 1:
                raise ReadingPassError(
                    "STALE_PUBLICATION_AUTHORITY", 409,
                    "The text authority changed concurrently; refresh before revoking it.",
                )

            sessions = await self.db.reading_pass_sessions.find(
                {
                    "content_type": "text",
                    "content_id": slug,
                    "status": {"$in": list(ACTIVE_SESSION_STATUSES)},
                },
                {"_id": 0},
                session=mongo_session,
            ).to_list(10_001)
            if len(sessions) > 10_000:
                raise ReadingPassError(
                    "REVOCATION_SCOPE_LIMIT", 503,
                    "Too many active text sessions require a scoped containment operation.",
                )
            total_debit = 0
            settlements: list[dict[str, Any]] = []
            authority_unavailable_sessions = 0
            retained_version_sessions = 0
            for session_doc in sessions:
                binding = self._text_revocation_binding(session_doc, revocation)
                if binding == "legacy_unbound":
                    await self._mark_text_authority_unavailable(
                        mongo_session=mongo_session,
                        session_doc=session_doc,
                        now=cutoff,
                    )
                    authority_unavailable_sessions += 1
                    continue
                if binding == "different_retained_publication":
                    retained_version_sessions += 1
                    continue
                debit, balance_after = await self._settle_terminal_session(
                    mongo_session=mongo_session,
                    session_doc=session_doc,
                    now=cutoff,
                    terminal_status="revoked",
                    reason="text_publication_revoked",
                    billing_cutoff_at=cutoff,
                )
                total_debit += debit
                settlements.append({"session_id": str(session_doc.get("id") or ""), "deducted_seconds": debit, "balance_seconds": balance_after})
                await self._audit(
                    "text_session_revoked",
                    session=mongo_session,
                    document={
                        "user_id": str(session_doc.get("user_id") or ""),
                        "session_id": str(session_doc.get("id") or ""),
                        "content_id": slug,
                        "revocation_generation": revocation["generation"],
                        "billing_cutoff_at": cutoff,
                        "deducted_seconds": debit,
                    },
                )
            result = {
                "book_slug": slug,
                "operation_id": operation_id,
                "revocation_generation": revocation["generation"],
                "activation_generation": expected_activation_generation,
                "segmentation_version": expected_segmentation_version,
                "manifest_version": expected_manifest_version,
                "cutoff_at": _iso(cutoff),
                "settled_session_count": len(settlements),
                "authority_unavailable_session_count": authority_unavailable_sessions,
                "retained_version_session_count": retained_version_sessions,
                "deducted_seconds": total_debit,
                "revoked": True,
            }
            await self.db.reading_pass_text_revocation_operations.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "operation_id": operation_id,
                    "intent": intent,
                    "result": result,
                    "created_at": cutoff,
                },
                session=mongo_session,
            )
            await self._audit(
                "text_publication_revoked",
                session=mongo_session,
                document={
                    "book_slug": slug,
                    "operation_id": operation_id,
                    "revocation_generation": revocation["generation"],
                    "activation_generation": expected_activation_generation,
                    "segmentation_version": expected_segmentation_version,
                    "manifest_version": expected_manifest_version,
                    "billing_cutoff_at": cutoff,
                    "settled_session_count": len(settlements),
                    "deducted_seconds": total_debit,
                },
            )
            return result

        try:
            return await self._transaction(operation)
        except DuplicateKeyError as exc:
            # A concurrent caller may have committed the same operation after
            # our transaction snapshot. Resolve only an exact intent replay;
            # any conflicting operation id remains a fail-closed conflict.
            previous = await self.db.reading_pass_text_revocation_operations.find_one(
                {"operation_id": operation_id}, {"_id": 0}
            )
            if previous and previous.get("intent") == intent:
                return {**dict(previous.get("result") or {}), "duplicate": True}
            raise ReadingPassError(
                "REVOCATION_OPERATION_CONFLICT", 409,
                "The operation id is already bound to a different revocation intent.",
            ) from exc

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
        text_authority: str = "allowed",
    ) -> dict[str, Any]:
        if not idempotency_key or len(idempotency_key) > 160:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "A bounded idempotency key is required.")
        if sequence < 1:
            raise ReadingPassError("CONTENT_NOT_AUTHORIZED", 400, "Heartbeat sequence must be positive.")
        if text_authority not in {"allowed", "denied", "unavailable"}:
            raise ReadingPassError("CONTENT_AUTHORITY_UNAVAILABLE", 503, "Reader availability could not be verified.")
        token_hash = token_fingerprint(lease_token, self.token_secret)
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
            if session_doc.get("content_type") == "text":
                revocation = await self._current_text_revocation(str(session_doc.get("content_id") or ""), mongo_session)
                if revocation:
                    binding = self._text_revocation_binding(session_doc, revocation)
                    if binding == "legacy_unbound":
                        unavailable = await self._mark_text_authority_unavailable(
                            mongo_session=mongo_session,
                            session_doc=session_doc,
                            now=now,
                        )
                        return {"terminal_error": "CONTENT_AUTHORITY_UNAVAILABLE", **unavailable}
                    if binding == "matches_revoked_publication":
                        debit, balance_after = await self._settle_terminal_session(
                            mongo_session=mongo_session,
                            session_doc=session_doc,
                            now=now,
                            terminal_status="revoked",
                            reason="text_publication_revoked",
                            billing_cutoff_at=ensure_utc(revocation["cutoff_at"]),
                        )
                        await self._audit(
                            "text_session_revocation_observed",
                            session=mongo_session,
                            document={
                                "user_id": user_id,
                                "session_id": session_id,
                                "content_id": str(session_doc.get("content_id") or ""),
                                "revocation_generation": revocation["generation"],
                                "billing_cutoff_at": ensure_utc(revocation["cutoff_at"]),
                                "deducted_seconds": debit,
                            },
                        )
                        return {
                            "terminal_error": "CONTENT_REVOKED",
                            "balance_seconds": balance_after,
                            "deducted_seconds": debit,
                        }
                if text_authority == "denied":
                    unavailable = await self._mark_text_authority_unavailable(
                        mongo_session=mongo_session,
                        session_doc=session_doc,
                        now=now,
                    )
                    return {"terminal_error": "CONTENT_AUTHORITY_UNAVAILABLE", **unavailable}
                if text_authority == "unavailable":
                    raise ReadingPassError(
                        "CONTENT_AUTHORITY_UNAVAILABLE", 503,
                        "Reader availability could not be verified.",
                    )
            existing = await self.db.reading_pass_heartbeats.find_one(
                {"session_id": session_id, "user_id": user_id, "idempotency_key": idempotency_key},
                {"_id": 0, "response": 1, "sequence": 1, "lease_version": 1, "active": 1, "playback_state": 1},
                session=mongo_session,
            )
            if existing:
                recorded_intent = "active" in existing and "playback_state" in existing
                if (
                    int(existing.get("sequence", 0) or 0) != sequence
                    or int(existing.get("lease_version", 0) or 0) != lease_version
                    or (
                        recorded_intent
                        and (
                            bool(existing.get("active")) is not bool(active)
                            or str(existing.get("playback_state") or "") != str(playback_state or "")
                        )
                    )
                ):
                    raise ReadingPassError(
                        "HEARTBEAT_INTENT_CONFLICT", 409,
                        "The idempotency key is already bound to a different renewal intent.",
                    )
                # Pre-413 receipts did not record full renewal intent.  They
                # must not be promoted into a fresh Running response or
                # charged again; a stale result tells the current client to
                # refresh its lease state without trusting missing fields.
                if not recorded_intent:
                    return {
                        "session_id": session_id,
                        "lease_version": current_version,
                        "lease_expires_at": _iso(session_doc["lease_expires_at"]),
                        "balance_seconds": await self._balance(user_id, mongo_session),
                        "deducted_seconds": 0,
                        "status": "Stale",
                        "stale": True,
                        "duplicate": True,
                        "legacy_receipt": True,
                    }
                response = dict(existing.get("response") or {})
                if (
                    int(response.get("lease_version", 0) or 0) != current_version
                    or last_sequence != sequence
                    or session_doc.get("status") not in ACTIVE_SESSION_STATUSES
                ):
                    return {
                        "session_id": session_id,
                        "lease_version": current_version,
                        "lease_expires_at": _iso(session_doc["lease_expires_at"]),
                        "balance_seconds": await self._balance(user_id, mongo_session),
                        "deducted_seconds": 0,
                        "status": "Stale",
                        "stale": True,
                        "duplicate": True,
                    }
                return {**response, "lease_token": lease_token, "duplicate": True}
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
                    "active": bool(active),
                    "playback_state": str(playback_state or ""),
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

        result = await self._transaction(operation)
        terminal_error = result.get("terminal_error")
        if terminal_error == "CONTENT_REVOKED":
            raise ReadingPassError(
                "CONTENT_REVOKED", 403,
                "This protected text is no longer available.",
                balance_seconds=int(result.get("balance_seconds", 0) or 0),
            )
        if terminal_error == "CONTENT_AUTHORITY_UNAVAILABLE":
            raise ReadingPassError(
                "CONTENT_AUTHORITY_UNAVAILABLE", 503,
                "Reader availability could not be verified; no additional time was collected.",
                balance_seconds=int(result.get("balance_seconds", 0) or 0),
            )
        return result

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
        billing_cutoff_at: Optional[datetime] = None,
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
                **({"billing_cutoff_at": _iso(billing_cutoff_at)} if billing_cutoff_at else {}),
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
                "metadata": {
                    "content_type": content_type,
                    "content_id": content_id[:200],
                    **({"billing_cutoff_at": _iso(billing_cutoff_at)} if billing_cutoff_at else {}),
                },
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
        if content_type == "text":
            revocation = await self._current_text_revocation(content_id, mongo_session=None)
            if revocation:
                binding = self._text_revocation_binding(session_doc, revocation)
                if binding == "matches_revoked_publication":
                    raise ReadingPassError("CONTENT_REVOKED", 403, "This protected text is no longer available.")
                if binding == "legacy_unbound":
                    raise ReadingPassError(
                        "CONTENT_AUTHORITY_UNAVAILABLE", 503,
                        "Reader availability could not be verified.",
                    )
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
        publication_segmentation_version: Optional[str] = None,
        publication_manifest_version: Optional[str] = None,
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
            # An unversioned historical position remains readable but is never
            # mistaken for a position known to belong to a retained immutable
            # publication version.
            if publication_segmentation_version or publication_manifest_version:
                if not publication_segmentation_version or not publication_manifest_version:
                    raise ReadingPassError(
                        "PUBLICATION_VERSION_REQUIRED", 400,
                        "Both canonical publication version fields are required together.",
                    )
                safe_position.update({
                    "segmentation_version": str(publication_segmentation_version),
                    "manifest_version": str(publication_manifest_version),
                    "publication_version_state": "bound",
                })
            else:
                safe_position["publication_version_state"] = "legacy_unversioned"
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
