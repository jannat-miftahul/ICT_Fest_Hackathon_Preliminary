# Bug Report

## 1. UTC offset datetimes were parsed incorrectly
- Location: `app/timeutils.py`
- Lines: Lines 12-13
- Bug: Offset-aware datetimes had their timezone stripped without converting to UTC.
- Impact: Bookings with offsets were stored and compared at the wrong instant.
- Fix: Convert aware datetimes with `astimezone(timezone.utc)` before storing as naive UTC.

## 2. Access token lifetime was 15 hours instead of 15 minutes
- Location: `app/auth.py`
- Lines: Line 53
- Bug: `ACCESS_TOKEN_EXPIRE_MINUTES` was multiplied by 60 before being passed as minutes.
- Impact: Access token `exp - iat` violated the required 900 seconds.
- Fix: Use `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`.

## 3. Logout checked revoked tokens by `sub` instead of `jti`
- Location: `app/auth.py`
- Lines: Lines 111-113
- Bug: Logout stored the token `jti`, but auth checked whether `sub` was revoked.
- Impact: Logged-out access tokens remained usable.
- Fix: Check revoked access tokens by `jti` under a lock.

## 4. Refresh tokens were reusable
- Location: `app/auth.py`, `app/routers/auth.py`
- Lines: app/auth.py: Lines 93-101, app/routers/auth.py: Lines 82-83
- Bug: Refresh token JTIs were never consumed or rejected after first use.
- Impact: A refresh token could be replayed indefinitely until expiry.
- Fix: Track consumed refresh token JTIs and reject reuse with `401`.

## 5. Duplicate usernames returned success
- Location: `app/routers/auth.py`
- Lines: Lines 40-41
- Bug: Registering an existing username in the same org returned the existing user.
- Impact: Violated the `409 USERNAME_TAKEN` contract.
- Fix: Raise `AppError(409, "USERNAME_TAKEN", ...)`.

## 6. Booking start time allowed a five-minute grace window
- Location: `app/routers/bookings.py`
- Lines: Line 88
- Bug: Past starts were allowed up to five minutes ago.
- Impact: Violated the strict future start-time rule.
- Fix: Reject `start <= now`.

## 7. Invalid zero/negative booking windows were not fully rejected
- Location: `app/routers/bookings.py`
- Lines: Lines 88-96
- Bug: `end_time <= start_time` and zero-hour bookings were not consistently rejected.
- Impact: Could create invalid bookings or incorrect prices.
- Fix: Reject `end <= start` and enforce duration range `1..8` whole hours.

## 8. Back-to-back bookings were treated as conflicts
- Location: `app/routers/bookings.py`
- Lines: Lines 45-54
- Bug: Conflict detection used inclusive comparisons.
- Impact: A booking ending exactly when another started was rejected.
- Fix: Use the required overlap condition: existing start `<` new end and existing end `>` new start.

## 9. Booking conflict and quota checks were race-prone
- Location: `app/routers/bookings.py`
- Lines: Lines 98, 120
- Bug: Artificial sleeps and unguarded check-then-insert logic allowed concurrent double booking or quota overflow.
- Impact: Concurrency rules could fail under simultaneous requests.
- Fix: Guard booking creation with a process lock and remove delay-based helpers.

## 10. Rate limiting was race-prone
- Location: `app/services/ratelimit.py`
- Lines: Lines 16-21
- Bug: Buckets were read, delayed, then written without synchronization.
- Impact: Concurrent requests could bypass the 20-per-minute limit.
- Fix: Protect bucket trim/append/check with a lock.

## 11. Reference code generation was race-prone
- Location: `app/services/reference.py`, `app/models.py`
- Lines: app/services/reference.py: Lines 5-6, app/models.py: Line 55
- Bug: A shared counter with a sleep could issue duplicate codes concurrently.
- Impact: Violated unique reference-code rule.
- Fix: Generate UUID-backed reference codes and add a database uniqueness constraint.

## 12. Booking pagination skipped items and ignored requested limits
- Location: `app/routers/bookings.py`
- Lines: Lines 140-142
- Bug: Results sorted descending, offset by `page * limit`, and always limited to 10.
- Impact: Pages skipped/repeated items and violated ordering rules.
- Fix: Sort ascending by `start_time, id`, offset `(page - 1) * limit`, and use the requested limit.

## 13. Members could read other members' bookings in the same org
- Location: `app/routers/bookings.py`
- Lines: Lines 165, 193
- Bug: Booking detail only checked organization membership.
- Impact: Violated member booking visibility.
- Fix: Return `404 BOOKING_NOT_FOUND` unless the caller is the owner or an admin.

## 14. Booking detail returned the wrong `start_time`
- Location: `app/routers/bookings.py`
- Lines: Line 168
- Bug: Detail serialization overwrote `start_time` with `created_at`.
- Impact: Returned incorrect booking data.
- Fix: Keep the serializer's actual booking `start_time`.

## 15. Refund policy used the wrong thresholds and values
- Location: `app/routers/bookings.py`
- Lines: Lines 201-206
- Bug: More than 48 hours, not at least 48, got 100%; less than 24 hours got 50%.
- Impact: Refund percentages violated the contract.
- Fix: Use `>= 48h` for 100%, `>= 24h` for 50%, otherwise 0%.

## 16. Refund amount calculation and logged amount disagreed
- Location: `app/routers/bookings.py`, `app/services/refunds.py`
- Lines: app/routers/bookings.py: Lines 37-41, app/services/refunds.py: Lines 22-25
- Bug: Response used Python `round`, while the refund log recalculated with truncation and received the percent rather than amount.
- Impact: Returned amount could differ from the stored `RefundLog` amount, and half-cent rounding was wrong.
- Fix: Calculate cents with `Decimal(..., ROUND_HALF_UP)` once and store that exact amount.

## 17. Concurrent cancellation could create multiple refund logs
- Location: `app/routers/bookings.py`, `app/models.py`, `app/services/refunds.py`
- Lines: app/routers/bookings.py: Lines 186-212, app/models.py: Line 66
- Bug: Cancellation checked status and wrote refund logs without synchronization; refund logging committed separately.
- Impact: Concurrent cancel requests could create duplicate refund logs or partial state.
- Fix: Guard cancellation with the booking lock, commit status and refund together, and make `refund_logs.booking_id` unique.

## 18. Room stats were stale and race-prone
- Location: `app/routers/rooms.py`, `app/services/stats.py`
- Lines: app/routers/rooms.py: Lines 103-110, app/services/stats.py: Lines 9-18
- Bug: Stats were maintained in in-memory counters with sleeps.
- Impact: Values could drift from actual confirmed bookings and fail after restart or concurrency.
- Fix: Derive stats directly from confirmed bookings in the database.

## 19. Availability responses could be stale
- Location: `app/routers/rooms.py`
- Lines: Lines 86-93
- Bug: Availability used an in-memory cache.
- Impact: Responses could fail the requirement to reflect current state immediately.
- Fix: Query confirmed bookings directly for each request.

## 20. Usage reports could be stale
- Location: `app/routers/admin.py`
- Lines: Lines 23-60
- Bug: Usage reports used an in-memory cache.
- Impact: Reports could fail to reflect current booking/cancellation state immediately.
- Fix: Query current confirmed bookings directly for each report request.

## 21. Admin export could leak cross-organization bookings
- Location: `app/services/export.py`, `app/routers/admin.py`
- Lines: app/services/export.py: Lines 39-59, app/routers/admin.py: Lines 65-71
- Bug: `include_all=true` with `room_id` used an unscoped raw room query.
- Impact: Admins could export bookings from another organization by room id.
- Fix: Validate `room_id` belongs to the admin's org and always fetch through an org-scoped query.

## 22. Notification side effects could deadlock
- Location: `app/services/notifications.py`
- Lines: Lines 9-14
- Bug: Created and cancelled notification paths acquired locks in opposite order and slept inside the request path.
- Impact: Concurrent valid requests could hang the service, violating liveness.
- Fix: Make challenge notifications non-blocking no-ops.