# Background Tasks

`z8ter.tasks.TaskManager` runs lightweight asynchronous work in the application process. Use it for periodic cleanup or refresh work that can tolerate interruption. Tasks are not persisted and each application worker runs its own manager; use a durable job system for work that must survive restarts or run once across workers.

## Enabling Tasks

```python
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_background_tasks()
app = builder.build()
```

The application lifespan starts and stops the manager. Handlers can access it at `request.app.state.task_manager`; it is also published as the `tasks` service.

### Session Cleanup

By default, the manager schedules a cleanup check every 3,600 seconds. At each run it looks for a registered session repository and calls `cleanup_expired()` if available. Without one, the check does nothing.

Choose an interval when registering the manager:

```python
builder.use_background_tasks(session_cleanup_interval=600)
```

Use `session_cleanup_interval=None` to disable automatic session cleanup. Cleanup only removes records according to the repository implementation; it does not impose a fixed storage bound on active sessions.

## Registering Startup and Interval Tasks

Pass a configured manager into your builder. This example logs a startup message and a recurring heartbeat; replace the task bodies with your own work:

```python
import logging

from z8ter.builders.app_builder import AppBuilder
from z8ter.tasks import TaskManager

logger = logging.getLogger("myapp.tasks")
tasks = TaskManager()


def announce_startup() -> None:
    logger.info("Application tasks are starting")


@tasks.interval(seconds=300, run_immediately=True)
async def heartbeat() -> None:
    logger.info("Application heartbeat")


tasks.add_startup_task(announce_startup)

builder = AppBuilder()
builder.use_background_tasks(task_manager=tasks)
app = builder.build()
```

Startup tasks are awaited in registration order before interval loops start. A slow startup task delays application startup. Synchronous functions run in the default executor; async functions run on the event loop and should avoid blocking work.

An interval is the delay **after one run finishes and before the next starts**, not a wall-clock schedule. The default is to wait one interval before the first run; `run_immediately=True` runs once as soon as the interval loop starts.

For tasks needing arguments, use `add_interval_task(func, seconds=..., args=(...), kwargs={...})`. Register startup tasks before the manager starts. Interval tasks added after startup are launched immediately as new interval loops.

## Starting Work from a Handler

Call `spawn()` from a running event loop. It returns an `asyncio.Task`; the response need not wait for that task:

```python
import logging

from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import JSONResponse

logger = logging.getLogger("myapp.tasks")


def record_demo_event() -> None:
    logger.info("A demo task ran")


class Demo(View):
    async def post(self, request: Request) -> JSONResponse:
        request.app.state.task_manager.spawn(record_demo_event)
        return JSONResponse({"accepted": True}, status_code=202)
```

Enable background tasks in the application's builder before using this view. The 202 response means work was scheduled in this process, not that it completed or was durably queued.

## Errors and Shutdown

Ordinary task exceptions are logged with a traceback through `z8ter.tasks`. A failing interval task continues on its next interval; the manager does not retry an individual failed run automatically. Startup-task exceptions are also logged rather than preventing later startup tasks from running, so use application startup logic for checks that must prevent the server from starting.

Shutdown cancels tracked tasks and waits up to five seconds by default. Cancellation cannot forcibly stop a synchronous function already running in an executor thread, and work may be interrupted by a process exit. Tests that depend on startup or shutdown must run the application's lifespan; see [Testing](testing.md).
