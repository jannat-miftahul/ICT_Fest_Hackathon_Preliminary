"""Side effects that accompany booking lifecycle events.

Notifications are intentionally non-blocking for the API contract. In this
challenge service there is no external mailer or audit sink to wait on, so the
request path should never sleep or contend on side-effect locks.
"""


def notify_created(booking) -> None:
    return None


def notify_cancelled(booking) -> None:
    return None