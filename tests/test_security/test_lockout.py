"""Tests for z8ter.security.lockout.AccountLockout."""

from __future__ import annotations

from z8ter.security.lockout import AccountLockout


def make_lockout(**kwargs) -> AccountLockout:
    defaults = dict(max_attempts=3, lockout_seconds=900, window_seconds=900)
    defaults.update(kwargs)
    return AccountLockout(**defaults)


def test_not_locked_initially() -> None:
    lockout = make_lockout()
    assert not lockout.is_locked("user@example.com")
    assert lockout.remaining_attempts("user@example.com") == 3


def test_locks_after_max_attempts() -> None:
    lockout = make_lockout()
    assert lockout.record_failure("user@example.com") is False
    assert lockout.record_failure("user@example.com") is False
    assert lockout.record_failure("user@example.com") is True
    assert lockout.is_locked("user@example.com")
    assert lockout.remaining_attempts("user@example.com") == 0
    assert lockout.seconds_until_unlock("user@example.com") > 0


def test_identifiers_are_case_insensitive() -> None:
    lockout = make_lockout(max_attempts=2)
    lockout.record_failure("User@Example.com")
    lockout.record_failure("user@example.COM ")
    assert lockout.is_locked("user@example.com")


def test_success_clears_failures() -> None:
    lockout = make_lockout()
    lockout.record_failure("user@example.com")
    lockout.record_failure("user@example.com")
    lockout.record_success("user@example.com")
    assert lockout.remaining_attempts("user@example.com") == 3


def test_success_does_not_clear_active_lock() -> None:
    lockout = make_lockout()
    for _ in range(3):
        lockout.record_failure("user@example.com")
    lockout.record_success("user@example.com")
    assert lockout.is_locked("user@example.com")


def test_reset_clears_lock() -> None:
    lockout = make_lockout()
    for _ in range(3):
        lockout.record_failure("user@example.com")
    lockout.reset("user@example.com")
    assert not lockout.is_locked("user@example.com")
    assert lockout.remaining_attempts("user@example.com") == 3


def test_lock_expires_after_lockout_seconds(monkeypatch) -> None:
    import z8ter.security.lockout as lockout_module

    now = [1_000_000.0]
    monkeypatch.setattr(lockout_module.time, "time", lambda: now[0])

    lockout = make_lockout(lockout_seconds=60)
    for _ in range(3):
        lockout.record_failure("user@example.com")
    assert lockout.is_locked("user@example.com")

    now[0] += 61
    assert not lockout.is_locked("user@example.com")
    assert lockout.remaining_attempts("user@example.com") == 3


def test_failures_outside_window_forgotten(monkeypatch) -> None:
    import z8ter.security.lockout as lockout_module

    now = [1_000_000.0]
    monkeypatch.setattr(lockout_module.time, "time", lambda: now[0])

    lockout = make_lockout(window_seconds=100)
    lockout.record_failure("user@example.com")
    lockout.record_failure("user@example.com")
    now[0] += 101
    # Old failures expired; this is failure #1 of a fresh window
    assert lockout.record_failure("user@example.com") is False
    assert not lockout.is_locked("user@example.com")


def test_cleanup_drops_expired_state(monkeypatch) -> None:
    import z8ter.security.lockout as lockout_module

    now = [1_000_000.0]
    monkeypatch.setattr(lockout_module.time, "time", lambda: now[0])

    lockout = make_lockout(lockout_seconds=60, window_seconds=60)
    for _ in range(3):
        lockout.record_failure("locked@example.com")
    lockout.record_failure("stale@example.com")

    now[0] += 120
    removed = lockout.cleanup()
    assert removed == 2
    assert not lockout._failures
    assert not lockout._locked_until


def test_independent_identifiers() -> None:
    lockout = make_lockout()
    for _ in range(3):
        lockout.record_failure("a@example.com")
    assert lockout.is_locked("a@example.com")
    assert not lockout.is_locked("b@example.com")
