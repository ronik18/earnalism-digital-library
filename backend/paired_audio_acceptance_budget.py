"""One fresh, separately approved public-package attempt. No provisioning or credential access."""
from datetime import datetime, timedelta
from hashlib import sha256

try:
    from .domain.reading_pass import ReadingPassError, ensure_utc
except ImportError:  # production backend working directory
    from domain.reading_pass import ReadingPassError, ensure_utc

SCHEMA = "paired-audio-acceptance-budget.v1"
TEST_ID = "open-window-paired-acceptance-40-20261110-v1"
SLUG = "the-open-window"
UUID = "74251b53-9e18-49fb-9fff-bb7c505633d4"
PACKAGE = "sha256-8e5c83a835cf8bea0a34809f8640603a2158a3cfe1aa8f1ac71117259a665b26"
DESCRIPTOR = "028f65d8551523eecaad03bb5b476070f0c48c1fb0771bf9abc9163ecd5ba4b2"
MAXIMUM_SECONDS = 40
MAXIMUM_SESSIONS = 1
EXPIRY_SECONDS = 900
APPROVAL_ID = "paired-reader-listener-40-20261110"
MEMBER_SHA256 = "c4ac3285d74eeba22185ccd4cb61c00a17e477c085f3d8c3a01f427f03e74a3a"
PACKAGE_SCOPE = dict(catalogue_uuid=UUID, package_version=PACKAGE,
                     release_descriptor_sha256=DESCRIPTOR)


def package_scope(slug, package):
    """Only server-selected, validated exact-package metadata can bind this cap."""
    if (slug == SLUG and isinstance(package, dict)
            and package.get("package_version") == PACKAGE
            and package.get("release_descriptor_sha256") == DESCRIPTOR
            and package.get("duration_ms") == 491436):
        return dict(PACKAGE_SCOPE)
    return {}


def build_budget(user_id, now, *, auth_session_id):
    """Pure proposal builder. It neither installs a budget nor starts a session."""
    if (not isinstance(user_id, str) or not user_id
            or sha256(user_id.encode()).hexdigest() != MEMBER_SHA256
            or not isinstance(auth_session_id, str) or not auth_session_id):
        raise ValueError("An exact privately verified account is required")
    return dict(schema=SCHEMA, approval_id=APPROVAL_ID, auth_session_id=auth_session_id, user_id=user_id, content_type="audio", content_id=SLUG,
                test_id=TEST_ID, **PACKAGE_SCOPE, maximum_seconds=MAXIMUM_SECONDS,
                consumed_seconds=0, maximum_sessions=MAXIMUM_SESSIONS,
                sessions_started=0, created_at=ensure_utc(now),
                expires_at=ensure_utc(now) + timedelta(seconds=EXPIRY_SECONDS), status="enabled")


def validate_budget(budget, document, *, starting, now):
    scope = document.get("scope") or {}
    fixed = dict(schema=SCHEMA, approval_id=APPROVAL_ID, content_type="audio", content_id=SLUG,
                 test_id=TEST_ID, maximum_seconds=MAXIMUM_SECONDS,
                 maximum_sessions=MAXIMUM_SESSIONS, status="enabled", **PACKAGE_SCOPE)
    valid = (
        isinstance(scope, dict)
        and all(budget.get(k) == v and type(budget.get(k)) is type(v) for k, v in fixed.items())
        and isinstance(budget.get("user_id"), str)
        and sha256(budget["user_id"].encode()).hexdigest() == MEMBER_SHA256
        and budget["user_id"] == document.get("user_id")
        and isinstance(budget.get("auth_session_id"), str) and bool(budget["auth_session_id"])
        and budget["auth_session_id"] == document.get("auth_session_id")
        and document.get("content_type") == "audio" and document.get("content_id") == SLUG
        and all(scope.get(k) == v for k, v in PACKAGE_SCOPE.items())
        and type(budget.get("consumed_seconds")) is int
        and 0 <= budget["consumed_seconds"] <= MAXIMUM_SECONDS
        and type(budget.get("sessions_started")) is int
        and 0 <= budget["sessions_started"] <= MAXIMUM_SESSIONS
        and isinstance(budget.get("created_at"), datetime)
        and isinstance(budget.get("expires_at"), datetime)
    )
    if valid:
        valid = (ensure_utc(budget["expires_at"]) - ensure_utc(budget["created_at"])
                 == timedelta(seconds=EXPIRY_SECONDS)
                 and ensure_utc(budget["created_at"]) <= ensure_utc(now))
    if valid and not starting:
        ordinal = document.get("acceptance_session_ordinal")
        valid = (document.get("acceptance_test_id") == TEST_ID
                 and type(ordinal) is int and 1 <= ordinal <= budget["sessions_started"])
    if not valid:
        raise ReadingPassError("ACCEPTANCE_SCOPE_UNAVAILABLE", 403,
                               "The exact audio acceptance scope could not be verified.")
    return budget


async def fence_start(db, user_id, retained_budget, *, mongo_session):
    """Serialize this member's starts with cap installation in one transaction.

    An uncapped start must write the account too; a read followed only by a
    session insert would permit snapshot write skew with concurrent installation.
    This monotonically increasing fence is neither a usage counter nor a grant.
    """
    if sha256(user_id.encode()).hexdigest() != MEMBER_SHA256:
        return
    query = {"id": user_id, "role": "user", "status": "active"}
    query["reader_acceptance_budget"] = (
        retained_budget if retained_budget is not None else {"$exists": False})
    result = await db.users.update_one(query, {"$inc": {
        "paired_audio_acceptance_admission_revision": 1}}, session=mongo_session)
    if result.modified_count != 1:
        raise ReadingPassError("ACCEPTANCE_OR_BALANCE_CHANGED", 409,
                               "Acceptance admission changed; no uncapped fallback.")
