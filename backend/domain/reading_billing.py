"""Pure reader-heartbeat billing decisions.

The server supplies runtime-configured thresholds. This package owns only the
time arithmetic and visibility/idle policy, so database mutation remains in
the application layer.
"""

from datetime import datetime, timezone
from typing import Optional


def _as_utc_dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def billable_reading_seconds(
    last_debit_at,
    now: datetime,
    *,
    visible: bool = True,
    idle: bool = False,
    heartbeat_tick_seconds: int,
    heartbeat_early_grace_seconds: int,
    session_idle_grace_seconds: int,
) -> int:
    """Return at most one heartbeat pulse for an eligible visible session."""

    if not visible or idle:
        return 0
    last = _as_utc_dt(last_debit_at) or now
    elapsed = max(0, int((now - last).total_seconds()))
    if elapsed > session_idle_grace_seconds:
        return 0
    if elapsed + heartbeat_early_grace_seconds < heartbeat_tick_seconds:
        return 0
    return heartbeat_tick_seconds


def should_reset_reading_clock(
    last_debit_at,
    now: datetime,
    *,
    visible: bool = True,
    idle: bool = False,
    session_idle_grace_seconds: int,
) -> bool:
    """Whether the next visible heartbeat must start a fresh billing window."""

    if not visible or idle:
        return True
    last = _as_utc_dt(last_debit_at) or now
    elapsed = max(0, int((now - last).total_seconds()))
    return elapsed > session_idle_grace_seconds
