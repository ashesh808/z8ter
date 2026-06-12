"""Asyncio background task manager for Z8ter.

`TaskManager` runs lightweight background work inside the application's
event loop — no broker or worker processes required:

- Fire-and-forget jobs (`spawn`) with error logging.
- Recurring interval tasks (`add_interval_task` / `@interval` decorator).
- One-shot startup tasks (`add_startup_task`).

The manager is started/stopped by the app lifespan when enabled via
`AppBuilder.use_background_tasks()`. Sync callables are offloaded to the
default executor so they never block the loop.

Scope guidance:
- Good for: session cleanup, cache refresh, sending emails, polling.
- Not for: CPU-heavy or must-not-be-lost work. Tasks die with the process;
  use Celery/RQ/arq for durable queues.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("z8ter.tasks")

TaskFunc = Callable[..., Any]


@dataclass
class IntervalTask:
    """Specification for a recurring task.

    Attributes:
        func: Sync or async callable invoked each tick (no arguments).
        seconds: Delay between runs (measured end-of-run to next start).
        name: Label used in logs.
        run_immediately: Run once at startup instead of waiting one interval.
        args: Positional arguments passed to `func`.
        kwargs: Keyword arguments passed to `func`.

    """

    func: TaskFunc
    seconds: float
    name: str
    run_immediately: bool = False
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)


class TaskManager:
    """Run startup, interval, and fire-and-forget tasks on the event loop.

    Lifecycle:
        - Register tasks any time before (or after) `start()`.
        - `start()` launches startup tasks then interval loops.
        - `stop()` cancels all loops and awaits spawned tasks briefly.

    Error handling:
        - Exceptions from any task are logged with traceback and never
          propagate; a failing interval task keeps its schedule.

    """

    def __init__(self) -> None:
        """Initialize an empty manager (not yet running)."""
        self._interval_specs: list[IntervalTask] = []
        self._startup_funcs: list[tuple[TaskFunc, tuple, dict]] = []
        self._running_tasks: set[asyncio.Task] = set()
        self._started = False

    @property
    def started(self) -> bool:
        """Whether `start()` has run (and `stop()` has not)."""
        return self._started

    # -------- Registration --------

    def add_startup_task(
        self, func: TaskFunc, *args: Any, **kwargs: Any
    ) -> None:
        """Register a one-shot task executed when the app starts.

        Args:
            func: Sync or async callable.
            *args: Positional arguments for the callable.
            **kwargs: Keyword arguments for the callable.

        """
        self._startup_funcs.append((func, args, kwargs))

    def add_interval_task(
        self,
        func: TaskFunc,
        *,
        seconds: float,
        name: str | None = None,
        run_immediately: bool = False,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> None:
        """Register a recurring task.

        Args:
            func: Sync or async callable invoked each tick.
            seconds: Interval between runs (must be > 0).
            name: Log label (defaults to the function name).
            run_immediately: Run once right after startup.
            args: Positional arguments for the callable.
            kwargs: Keyword arguments for the callable.

        Raises:
            ValueError: If `seconds` is not positive.

        """
        if seconds <= 0:
            raise ValueError("Z8ter: interval task seconds must be > 0.")
        spec = IntervalTask(
            func=func,
            seconds=seconds,
            name=name or getattr(func, "__name__", "task"),
            run_immediately=run_immediately,
            args=args,
            kwargs=kwargs or {},
        )
        self._interval_specs.append(spec)
        if self._started:
            self._launch_interval(spec)

    def interval(
        self,
        seconds: float,
        *,
        name: str | None = None,
        run_immediately: bool = False,
    ) -> Callable[[TaskFunc], TaskFunc]:
        """Register a recurring task (decorator form of `add_interval_task`).

        Example:
            @tasks.interval(seconds=3600)
            async def cleanup():
                session_repo.cleanup_expired()

        Args:
            seconds: Interval between runs.
            name: Log label (defaults to the function name).
            run_immediately: Run once right after startup.

        Returns:
            The original function, unmodified.

        """

        def decorator(func: TaskFunc) -> TaskFunc:
            self.add_interval_task(
                func,
                seconds=seconds,
                name=name,
                run_immediately=run_immediately,
            )
            return func

        return decorator

    # -------- Execution --------

    async def _call(self, func: TaskFunc, *args: Any, **kwargs: Any) -> Any:
        """Invoke a callable, offloading sync functions to the executor."""
        result = None
        if inspect.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: func(*args, **kwargs)
            )
            # A sync wrapper may still return an awaitable.
            if isinstance(result, Awaitable):
                result = await result
        return result

    async def _run_safely(self, name: str, coro: Awaitable[Any]) -> None:
        """Await a coroutine, logging (not raising) any exception."""
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background task '%s' failed", name)

    def spawn(
        self,
        func: TaskFunc,
        *args: Any,
        name: str | None = None,
        **kwargs: Any,
    ) -> asyncio.Task:
        """Run a task in the background (fire-and-forget) with error logging.

        Must be called from within a running event loop (i.e., a request
        handler or another task).

        Args:
            func: Sync or async callable.
            *args: Positional arguments for the callable.
            name: Log label (defaults to the function name).
            **kwargs: Keyword arguments for the callable.

        Returns:
            The created `asyncio.Task` (awaitable if the caller cares).

        """
        label = name or getattr(func, "__name__", "task")
        task = asyncio.get_running_loop().create_task(
            self._run_safely(label, self._call(func, *args, **kwargs))
        )
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
        return task

    async def _interval_loop(self, spec: IntervalTask) -> None:
        """Run one interval task forever (until cancelled)."""
        if spec.run_immediately:
            await self._run_safely(
                spec.name, self._call(spec.func, *spec.args, **spec.kwargs)
            )
        while True:
            await asyncio.sleep(spec.seconds)
            await self._run_safely(
                spec.name, self._call(spec.func, *spec.args, **spec.kwargs)
            )

    def _launch_interval(self, spec: IntervalTask) -> None:
        """Create the asyncio task driving one interval spec."""
        task = asyncio.get_running_loop().create_task(
            self._interval_loop(spec), name=f"z8ter-interval-{spec.name}"
        )
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)

    async def start(self) -> None:
        """Run startup tasks, then launch all interval loops.

        Idempotent: a second call while running is a no-op.
        """
        if self._started:
            return
        self._started = True
        for func, args, kwargs in self._startup_funcs:
            label = getattr(func, "__name__", "startup-task")
            await self._run_safely(label, self._call(func, *args, **kwargs))
        for spec in self._interval_specs:
            self._launch_interval(spec)
        if self._interval_specs:
            logger.info(
                "Task manager started with %d interval task(s)",
                len(self._interval_specs),
            )

    async def stop(self, *, timeout: float = 5.0) -> None:
        """Cancel interval loops and wait briefly for in-flight tasks.

        Args:
            timeout: Seconds to wait for tasks to finish after cancellation.

        """
        if not self._started:
            return
        self._started = False
        tasks = list(self._running_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=timeout)
        self._running_tasks.clear()
        logger.info("Task manager stopped")
