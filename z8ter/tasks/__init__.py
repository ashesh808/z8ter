"""Z8ter background tasks module.

In-process asyncio task support — no broker required:
- `TaskManager`: startup tasks, recurring interval tasks, fire-and-forget.
- `IntervalTask`: spec dataclass for recurring tasks.

Enable via the app builder:

    builder.use_background_tasks(session_cleanup_interval=3600)

Then access in handlers via `request.app.state.task_manager` (or the
`tasks` service) to spawn fire-and-forget work:

    tasks = request.app.state.task_manager
    tasks.spawn(email_service.send, message)

For durable or CPU-heavy workloads, use a dedicated queue (Celery/RQ/arq);
tasks registered here die with the process.
"""

from z8ter.tasks.manager import IntervalTask, TaskManager

__all__ = ["IntervalTask", "TaskManager"]
