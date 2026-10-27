"""Exact Open Window acceptance policy; no provisioning or credential access."""
from datetime import datetime, timedelta

try:
    from .domain.reading_pass import ReadingPassError, ensure_utc
except ImportError:  # production backend working directory
    from domain.reading_pass import ReadingPassError, ensure_utc

SCHEMA = "audio-acceptance-budget.v1"
TEST_ID = "open-window-production-acceptance-600-v1"
SLUG = "the-open-window"
UUID = "74251b53-9e18-49fb-9fff-bb7c505633d4"
PACKAGE = "sha256-8e5c83a835cf8bea0a34809f8640603a2158a3cfe1aa8f1ac71117259a665b26"
DESCRIPTOR = "028f65d8551523eecaad03bb5b476070f0c48c1fb0771bf9abc9163ecd5ba4b2"
MAXIMUM_SECONDS = 600
MAXIMUM_SESSIONS = 2
EXPIRY_SECONDS = 900
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


def build_budget(user_id, now):
    """Pure proposal builder. It neither installs a budget nor starts a session."""
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("An exact privately verified account is required")
    return dict(schema=SCHEMA, user_id=user_id, content_type="audio", content_id=SLUG,
                test_id=TEST_ID, **PACKAGE_SCOPE, maximum_seconds=MAXIMUM_SECONDS,
                consumed_seconds=0, maximum_sessions=MAXIMUM_SESSIONS,
                sessions_started=0, created_at=ensure_utc(now),
                expires_at=ensure_utc(now) + timedelta(seconds=EXPIRY_SECONDS), status="enabled")


def validate_budget(budget, document, *, starting, now):
    scope = document.get("scope") or {}
    fixed = dict(schema=SCHEMA, content_type="audio", content_id=SLUG,
                 test_id=TEST_ID, maximum_seconds=MAXIMUM_SECONDS,
                 maximum_sessions=MAXIMUM_SESSIONS, status="enabled", **PACKAGE_SCOPE)
    valid = (
        isinstance(scope, dict)
        and all(budget.get(k) == v and type(budget.get(k)) is type(v) for k, v in fixed.items())
        and budget.get("user_id") == document.get("user_id")
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
