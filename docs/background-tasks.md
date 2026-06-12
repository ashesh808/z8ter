# Background Tasks

Z8ter includes an in-process asyncio task manager (`z8ter.tasks`) for
lightweight background work — no broker or worker processes required.

Good for: session cleanup, cache refresh, sending email outside the
request path, polling. Not for: CPU-heavy or must-not-be-lost work —
tasks die with the process. Use Celery/RQ/arq for durable queues.

## Enabling

```python
builder = AppBuilder()
builder.use_background_tasks()   # also schedules hourly session cleanup
app = builder.build()
```

The manager starts on app startup and stops on shutdown via the
application lifespan.

### Automatic session cleanup

When auth repos are registered, `use_background_tasks()` automatically
runs `session_repo.cleanup_expired()` every hour, keeping session storage
bounded. Tune or disable it:

```python
builder.use_background_tasks(session_cleanup_interval=600)   # every 10 min
builder.use_background_tasks(session_cleanup_interval=None)  # disabled
```

## Registering tasks

Pass a pre-configured manager to the builder:

```python
from z8ter.tasks import TaskManager

tasks = TaskManager()

@tasks.interval(seconds=300)
async def refresh_cache():
    ...

@tasks.interval(seconds=86400, run_immediately=True)
def daily_report():          # sync functions run in a threadpool
    ...

tasks.add_startup_task(warm_connections)

builder.use_background_tasks(task_manager=tasks)
```

## Fire-and-forget work in handlers

The manager is available at `request.app.state.task_manager` (and as the
`tasks` service). `spawn()` runs work in the background with error
logging, so the response is not delayed:

```python
class Register(View):
    async def post(self, request):
        tasks = request.app.state.task_manager
        tasks.spawn(send_welcome_email, user["email"])
        return redirect("/app")
```

## Error handling

Exceptions raised by tasks are logged (logger `z8ter.tasks`) with a full
traceback and never crash the app; a failing interval task keeps its
schedule.
