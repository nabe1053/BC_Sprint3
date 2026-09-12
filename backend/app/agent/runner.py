"""Run a decision stream through guarded tools; always dispatched via jobs.

Loop behavior is evaluated by make agent-eval, not by unit tests.
"""
import asyncio
import logging
import sys
from dataclasses import asdict
from time import monotonic

from app.agent import definition
from app.agent.local_policy import local_dummy_policy
from app.agent.tools import ToolExecutor, digest_args
from app.domain.agent_types import LocalPolicyStop, PolicyHeartbeat
from app.domain.errors import DomainError
from app.domain.run_types import HeartbeatDiagnostics, RunResult
from app.services.draft_validation import validate_snapshot

_pending = set()


def _consume(task):
    _pending.discard(task)
    if not task.cancelled():
        error = task.exception()
        if error is not None and not isinstance(
            error, (StopAsyncIteration, LocalPolicyStop)
        ):
            logging.getLogger(__name__).error(
                "Local agent operation failed (%s)",
                error.code if isinstance(error, DomainError) else type(error).__name__,
            )


class LocalAgentWorker:
    def __init__(self, gateway, policy_factory=local_dummy_policy):
        self.gateway = gateway
        self.policy_factory = policy_factory

    async def prepare_finish(self, context, result):
        """System cleanup after stopped work; retried by the existing jobs boundary."""
        if result.stop_reason == "completed":
            return
        async with self.gateway.cleanup(context) as repository:
            if repository is not None:
                snapshot = await repository.snapshot(context.version_id)
                validation = validate_snapshot(snapshot)
                await repository.record_interruption(
                    snapshot,
                    [asdict(v) for v in validation.violations],
                    result.stop_reason,
                    result.heartbeat_diagnostics,
                )

    async def __call__(self, context):
        executor = ToolExecutor(context, self.gateway)
        stream = self.policy_factory(context)
        last_heartbeat = monotonic()
        heartbeats = 0
        deadline = last_heartbeat + context.limits.inner_timeout_s
        turns = 0
        previous_call, repetitions = None, 0
        previous_validation, validation_repetitions = None, 0
        previous_error, error_repetitions = None, 0
        reply = None
        deadline_stop = False
        result_ready = False

        def outcome(result):
            nonlocal result_ready
            result_ready = True
            return result

        async def bounded(awaitable):
            nonlocal last_heartbeat, heartbeats
            last_message = monotonic()
            while True:
                remaining = deadline - monotonic()
                inactivity = context.limits.inactivity_timeout_s - (
                    monotonic() - last_message
                )
                with executor.bind():
                    task = asyncio.create_task(awaitable)
                _pending.add(task)
                task.add_done_callback(_consume)
                try:
                    done, _ = await asyncio.wait(
                        {task},
                        timeout=max(0, min(remaining, inactivity)),
                    )
                    if not done:
                        executor.close()
                        task.cancel()
                        reason = (
                            "inner_timeout"
                            if monotonic() >= deadline
                            else "inactivity_timeout"
                        )
                        raise LocalPolicyStop(reason)
                    result = task.result()
                    if isinstance(result, PolicyHeartbeat):
                        last_message = result.received_at
                        last_heartbeat = result.received_at
                        heartbeats += 1
                        awaitable = stream.asend(reply)
                        continue
                    return result
                except asyncio.CancelledError:
                    executor.close()
                    task.cancel()
                    raise

        try:
            while True:
                if turns >= context.limits.max_turns:
                    return outcome(RunResult("max_turns", turns))
                call = await bounded(stream.asend(reply))
                turns += 1
                reply = await bounded(executor.call(call.name, call.arguments))
                if reply.is_error:
                    error_key = (call.name, reply.data.get("code"))
                    error_repetitions = (
                        error_repetitions + 1 if error_key == previous_error else 1
                    )
                    previous_error = error_key
                    if error_repetitions >= definition.REPEATED_CALL_LIMIT:
                        return outcome(RunResult("failed", turns, "tool_rejected"))
                else:
                    previous_error, error_repetitions = None, 0
                if call.name == "finalize_draft" and not reply.is_error:
                    return outcome(RunResult("completed", turns))
                key = (call.name, digest_args(call.arguments))
                repetitions = repetitions + 1 if key == previous_call else 1
                previous_call = key
                if call.name == "validate_draft" and not reply.is_error:
                    violations = reply.data["violations"]
                    digest = digest_args(violations)
                    validation_repetitions = (
                        validation_repetitions + 1
                        if violations and digest == previous_validation
                        else (1 if violations else 0)
                    )
                    previous_validation = digest
                    if validation_repetitions >= definition.VALIDATION_REPEAT_LIMIT:
                        return outcome(RunResult("validation_loop", turns))
                if repetitions >= definition.REPEATED_CALL_LIMIT:
                    return outcome(RunResult("repeated_call", turns))
        except LocalPolicyStop as exc:
            deadline_stop = exc.reason in ("inner_timeout", "inactivity_timeout")
            if exc.reason in (
                "inner_timeout",
                "inactivity_timeout",
                "no_readable_document",
                "max_turns",
            ):
                return outcome(
                    RunResult(
                        exc.reason,
                        turns,
                        heartbeat_diagnostics=HeartbeatDiagnostics(
                            max(0, monotonic() - last_heartbeat), heartbeats
                        )
                        if deadline_stop
                        else None,
                    )
                )
            return outcome(
                RunResult(
                    "failed",
                    turns,
                    exc.reason
                    if exc.reason in ("local_dummy_unsupported", "model_error")
                    else "validation_unresolved",
                )
            )
        except StopAsyncIteration:
            return outcome(RunResult("failed", turns, "draft_not_finalized"))
        except Exception:
            return outcome(RunResult("failed", turns, "worker_failed"))
        finally:
            pending_exception = sys.exc_info()[0] is not None
            executor.close()
            # Never wait unboundedly for cancellation-suppressing policy cleanup.
            try:
                closer = asyncio.create_task(stream.aclose())
                _pending.add(closer)
                closer.add_done_callback(_consume)
                done, _ = await asyncio.wait(
                    {closer}, timeout=definition.CANCEL_CLEANUP_S
                )
                if not done:
                    closer.cancel()
            except asyncio.CancelledError:
                if not (deadline_stop or pending_exception or result_ready):
                    raise
                # Preserve the exception/result already chosen before SDK cleanup.
                asyncio.current_task().uncancel()
