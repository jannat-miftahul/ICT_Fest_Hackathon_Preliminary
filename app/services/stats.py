"""Compatibility helpers for room statistics.

The stats endpoint derives values from the database directly. These functions are
kept as harmless no-ops for any legacy imports.
"""


def record_create(room_id: int, price_cents: int) -> None:
    return None


def record_cancel(room_id: int, price_cents: int) -> None:
    return None


def get(room_id: int) -> dict:
    return {"count": 0, "revenue": 0}