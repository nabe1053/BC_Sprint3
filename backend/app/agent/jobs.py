"""Local job boundary: immediate dispatch, bounded work and durable terminal callback."""
import asyncio
import logging
from app.domain.run_types import RunResult

_tasks: set[asyncio.Task] = set()
_workers: set[asyncio.Task] = set()
logger = logging.getLogger(__name__)
CANCEL_GRACE_S = 0.02
FINISH_TIMEOUT_S = 5


def start_agent_job(run_id: int, *, work, on_finish, outer_timeout_s: float):
    task = asyncio.create_task(
        _execute(work, on_finish, outer_timeout_s), name=f"agent-run-{run_id}"
    )
    _tasks.add(task)
    task.add_done_callback(_done)
    return task


def _done(task):
    _tasks.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error(
            "Agent terminal persistence failed (%s); next start/startup recovery is required",
            type(task.exception()).__name__,
        )


def _worker_done(task):
    _workers.discard(task)
    if not task.cancelled():
        exc = task.exception()
        if exc is not None:
            logger.error("Agent background task failed (%s)", type(exc).__name__)


async def _cancel_with_grace(task):
    task.cancel()
    # wait_for would wait indefinitely when a worker suppresses cancellation.
    await asyncio.wait({task}, timeout=CANCEL_GRACE_S)


async def _persist(on_finish, result):
    task = asyncio.create_task(on_finish(result))
    _workers.add(task)
    task.add_done_callback(_worker_done)
    done, _ = await asyncio.wait({task}, timeout=FINISH_TIMEOUT_S)
    if not done:
        await _cancel_with_grace(task)
        raise TimeoutError("Terminal callback exceeded its deadline")
    task.result()


async def _execute(work, on_finish, timeout):
    worker = asyncio.create_task(work())
    _workers.add(worker)
    worker.add_done_callback(_worker_done)
    try:
        done, _ = await asyncio.wait({worker}, timeout=timeout)
        if not done:
            await _cancel_with_grace(worker)
            result = RunResult("outer_timeout")
        else:
            result = worker.result()
    except asyncio.CancelledError:
        await _cancel_with_grace(worker)
        result = RunResult("failed", detail="process_interrupted")
    except Exception:
        result = RunResult("failed", detail="worker_failed")
    # A transient DB error must not permanently strand a run.
    for attempt in range(3):
        try:
            await _persist(on_finish, result)
            return
        except Exception as exc:
            logger.error(
                "Agent terminal persistence attempt failed (%s)", type(exc).__name__
            )
            if attempt == 2:
                raise RuntimeError("Terminal state could not be persisted") from None
            await asyncio.sleep(0.1 * 2**attempt)


async def stop_jobs():
    tasks = list(_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.wait(tasks, timeout=16)
    for worker in list(_workers):
        worker.cancel()


async def local_worker_unavailable(context):
    """T-203 supplies generation; no unfinished draft is fabricated as success."""
    return RunResult("failed", detail="agent_implementation_pending")
