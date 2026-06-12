"""Tests for z8ter.testing utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from z8ter.testing import (
    InMemorySessionRepo,
    InMemoryUserRepo,
    create_test_app,
)


def _expiry(minutes: int = 30) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _insert(repo: InMemorySessionRepo, sid: str, user_id: str = "u_1", **kw):
    defaults = dict(
        sid_plain=sid,
        user_id=user_id,
        expires_at=_expiry(),
        remember=False,
        ip=None,
        user_agent=None,
    )
    defaults.update(kw)
    repo.insert(**defaults)


class TestInMemorySessionRepo:
    def test_insert_and_lookup(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "sid-1")
        assert repo.get_user_id("sid-1") == "u_1"
        assert repo.get_user_id("unknown") is None

    def test_duplicate_sid_raises(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "sid-1")
        with pytest.raises(ValueError):
            _insert(repo, "sid-1")

    def test_revoke(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "sid-1")
        assert repo.revoke(sid_plain="sid-1") is True
        assert repo.get_user_id("sid-1") is None
        # Idempotency: second revoke returns False
        assert repo.revoke(sid_plain="sid-1") is False

    def test_expired_sessions_invalid(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "sid-1", expires_at=_expiry(minutes=-1))
        assert repo.get_user_id("sid-1") is None
        assert repo.revoke(sid_plain="sid-1") is False

    def test_rotation_revokes_old_session(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "old-sid")
        _insert(repo, "new-sid", rotated_from_sid="old-sid")
        assert repo.get_user_id("old-sid") is None
        assert repo.get_user_id("new-sid") == "u_1"

    def test_revoke_all_for_user(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "sid-1", user_id="u_1")
        _insert(repo, "sid-2", user_id="u_1")
        _insert(repo, "sid-3", user_id="u_2")
        assert repo.revoke_all_for_user("u_1") == 2
        assert repo.get_user_id("sid-1") is None
        assert repo.get_user_id("sid-3") == "u_2"

    def test_cleanup_expired(self) -> None:
        repo = InMemorySessionRepo()
        _insert(repo, "live")
        _insert(repo, "dead", expires_at=_expiry(minutes=-1))
        _insert(repo, "revoked")
        repo.revoke(sid_plain="revoked")
        assert repo.cleanup_expired() == 2
        assert repo.active_session_count() == 1


class TestInMemoryUserRepo:
    def test_create_and_get(self) -> None:
        repo = InMemoryUserRepo()
        user = repo.create_user(
            email="Ada@Example.com", password_hash="h", name="Ada"
        )
        assert user["email"] == "ada@example.com"
        assert "password_hash" not in user
        fetched = repo.get_user_by_id(user["id"])
        assert fetched is not None and fetched["name"] == "Ada"

    def test_get_by_email_includes_hash(self) -> None:
        repo = InMemoryUserRepo()
        repo.create_user(email="a@b.c", password_hash="hash-1")
        user = repo.get_user_by_email("A@B.C")
        assert user is not None and user["password_hash"] == "hash-1"

    def test_duplicate_email_rejected(self) -> None:
        repo = InMemoryUserRepo()
        repo.create_user(email="a@b.c", password_hash="h")
        with pytest.raises(ValueError, match="already exists"):
            repo.create_user(email="A@B.C", password_hash="h")

    def test_email_exists(self) -> None:
        repo = InMemoryUserRepo()
        repo.create_user(email="a@b.c", password_hash="h")
        assert repo.email_exists("a@b.c")
        assert not repo.email_exists("missing@b.c")

    def test_update_user_and_password(self) -> None:
        repo = InMemoryUserRepo()
        user = repo.create_user(email="a@b.c", password_hash="h")
        assert repo.update_user(user["id"], is_verified=True)
        assert repo.get_user_by_id(user["id"])["is_verified"] is True
        assert repo.update_password(user["id"], "new-hash")
        assert repo.get_user_by_email("a@b.c")["password_hash"] == "new-hash"
        assert not repo.update_password("missing", "x")

    def test_delete_list_count(self) -> None:
        repo = InMemoryUserRepo()
        u1 = repo.create_user(email="a@b.c", password_hash="h")
        repo.create_user(email="b@b.c", password_hash="h")
        repo.update_user(u1["id"], is_active=False)
        assert repo.count_users() == 2
        assert repo.count_users(active_only=True) == 1
        assert len(repo.list_users(active_only=True)) == 1
        assert repo.delete_user(u1["id"])
        assert repo.count_users() == 1


def test_create_test_app_builds_and_serves() -> None:
    from starlette.responses import PlainTextResponse
    from starlette.testclient import TestClient

    app = create_test_app(
        session_repo=InMemorySessionRepo(),
        user_repo=InMemoryUserRepo(),
    )
    assert app.starlette_app.state.session_repo is not None

    async def ping(request):
        return PlainTextResponse("pong")

    from starlette.routing import Route

    app.starlette_app.routes.append(Route("/ping", ping))
    client = TestClient(app.starlette_app)
    assert client.get("/ping").text == "pong"
