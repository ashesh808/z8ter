"""Tests for z8ter.tasks.TaskManager."""

from __future__ import annotations

import asyncio
import logging

import pytest

from z8ter.tasks import TaskManager


def test_startup_tasks_run_on_start() -> None:
    manager = TaskManager()
    ran: list[str] = []

    async def async_startup() -> None:
        ran.append("async")

    def sync_startup(tag: str) -> None:
        ran.append(tag)

    manager.add_startup_task(async_startup)
    manager.add_startup_task(sync_startup, "sync")

    async def scenario() -> None:
        await manager.start()
        await manager.stop()

    asyncio.run(scenario())
    assert ran == ["async", "sync"]


def test_interval_task_runs_repeatedly() -> None:
    manager = TaskManager()
    ticks: list[int] = []

    manager.add_interval_task(
        lambda: ticks.append(1), seconds=0.02, name="ticker"
    )

    async def scenario() -> None:
        await manager.start()
        await asyncio.sleep(0.11)
        await manager.stop()

    asyncio.run(scenario())
    assert len(ticks) >= 2


def test_interval_decorator_and_run_immediately() -> None:
    manager = TaskManager()
    ticks: list[int] = []

    @manager.interval(seconds=60, run_immediately=True)
    async def tick() -> None:
        ticks.append(1)

    async def scenario() -> None:
        await manager.start()
        # Yield so the interval loop task gets a chance to do its
        # immediate run before we cancel it.
        await asyncio.sleep(0.05)
        await manager.stop()

    asyncio.run(scenario())
    # Ran exactly once at startup; the 60s interval never elapsed.
    assert ticks == [1]


def test_invalid_interval_rejected() -> None:
    manager = TaskManager()
    with pytest.raises(ValueError, match="must be > 0"):
        manager.add_interval_task(lambda: None, seconds=0)


def test_failing_task_logged_and_schedule_survives(caplog) -> None:
    manager = TaskManager()
    ticks: list[int] = []

    def flaky() -> None:
        ticks.append(1)
        raise RuntimeError("boom")

    manager.add_interval_task(flaky, seconds=0.02, name="flaky")

    async def scenario() -> None:
        await manager.start()
        await asyncio.sleep(0.07)
        await manager.stop()

    with caplog.at_level(logging.ERROR, logger="z8ter.tasks"):
        asyncio.run(scenario())

    assert len(ticks) >= 2  # kept running after the first failure
    assert "flaky" in caplog.text


def test_spawn_fire_and_forget() -> None:
    manager = TaskManager()
    done: list[str] = []

    async def job(tag: str) -> None:
        done.append(tag)

    async def scenario() -> None:
        task = manager.spawn(job, "one")
        await task

    asyncio.run(scenario())
    assert done == ["one"]


def test_start_is_idempotent() -> None:
    manager = TaskManager()
    ran: list[int] = []
    manager.add_startup_task(lambda: ran.append(1))

    async def scenario() -> None:
        await manager.start()
        await manager.start()
        await manager.stop()

    asyncio.run(scenario())
    assert ran == [1]


def test_lifespan_starts_and_stops_manager() -> None:
    from starlette.testclient import TestClient

    from z8ter.builders.app_builder import AppBuilder

    builder = AppBuilder()
    builder.use_background_tasks(session_cleanup_interval=None)
    app = builder.build(debug=True)
    manager = app.starlette_app.state.task_manager
    assert isinstance(manager, TaskManager)
    assert not manager.started

    with TestClient(app.starlette_app):
        assert manager.started
    assert not manager.started


def test_session_cleanup_task_registered() -> None:
    from z8ter.builders.app_builder import AppBuilder

    builder = AppBuilder()
    builder.use_background_tasks(session_cleanup_interval=3600)
    app = builder.build(debug=True)
    manager = app.starlette_app.state.task_manager
    names = [spec.name for spec in manager._interval_specs]
    assert "session_cleanup" in names
