"""Atomic run reservation and durable polling. SQL and disk metadata stay here."""
import hashlib
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from sqlalchemy import select, func
from app.domain.draft_errors import DraftError
from app.domain.run_types import RECOVERY_GRACE_S, RunResult
from app.models import (
    Case,
    RuleSet,
    Version,
    AgentRun,
    AgentRunStep,
    Document,
    DocumentPage,
    EmailPart,
    ItemEdit,
    Confirmation,
    Question,
    QuestionJudgement,
)
from app.repositories.draft_repository import DraftRepository


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _is_recoverable(run, now):
    limit = run.limits.get("outerTimeoutS")
    return (
        run.outcome == "running"
        and isinstance(limit, (int, float))
        and not isinstance(limit, bool)
        and (now - utc(run.started_at)).total_seconds() > limit + RECOVERY_GRACE_S
    )


class RunRepository(DraftRepository):
    def __init__(self, session, *, file_size, trace=None):
        super().__init__(session)
        self.file_size = file_size
        self.trace = trace

    async def _has_records(self, case_id):
        versions = select(Version.id).where(Version.case_id == case_id)
        for model in (ItemEdit, Confirmation):
            result = await self.session.execute(
                select(model.id)
                .where(
                    model.version_id.in_(versions),
                    model.undone_at.is_(None),
                )
                .limit(1)
            )
            if result.first() is not None:
                return True
        return (
            await self.session.execute(
                select(QuestionJudgement.id)
                .join(
                    Question,
                    Question.id == QuestionJudgement.question_id,
                )
                .where(Question.version_id.in_(versions))
                .limit(1)
            )
        ).first() is not None

    async def reserve(
        self,
        case_id,
        rule_version,
        acknowledged,
        limits,
        validate,
        impl_version,
        *,
        model,
    ):
        async with self._transaction():
            case = (
                await self.session.execute(
                    select(Case).where(Case.id == case_id).with_for_update()
                )
            ).scalar_one_or_none()
            if case is None:
                raise DraftError("E_NOT_FOUND", "案件が存在しません")
            active = (
                await self.session.execute(
                    select(AgentRun.id).where(
                        AgentRun.case_id == case_id, AgentRun.outcome == "running"
                    )
                )
            ).first()
            if active:
                raise DraftError("E_RUN_IN_PROGRESS", "この案件は実行中です")
            rule = (
                await self.session.execute(
                    select(RuleSet).where(
                        RuleSet.rule_version == rule_version
                        if rule_version is not None
                        else RuleSet.is_current.is_(True)
                    )
                )
            ).scalar_one_or_none()
            if rule is None:
                raise DraftError(
                    "E_NOT_FOUND", "指定した規則版または現行規則が存在しません"
                )
            previous = (
                await self.session.execute(
                    select(Version)
                    .where(Version.case_id == case_id)
                    .order_by(Version.version_no.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if previous and not acknowledged and await self._has_records(case_id):
                raise DraftError(
                    "E_CARRY_OVER_NOT_ACKNOWLEDGED",
                    "既存版の人の記録は引き継がれません",
                )
            docs = list(
                (
                    await self.session.execute(
                        select(Document).where(Document.case_id == case_id)
                    )
                ).scalars()
            )
            readable = False
            for doc in docs:
                if doc.read_status not in ("success", "partial"):
                    continue
                pages = (
                    await self.session.execute(
                        select(DocumentPage).where(DocumentPage.document_id == doc.id)
                    )
                ).scalars()
                parts = (
                    await self.session.execute(
                        select(EmailPart).where(EmailPart.document_id == doc.id)
                    )
                ).scalars()
                if any((p.text and p.text.strip()) or p.cells for p in pages) or any(
                    (p.body and p.body.strip()) or p.attachment_name for p in parts
                ):
                    readable = True
            # This service policy executes inside the case lock and before inserting anything.
            validate(docs, readable, self.file_size)
            now = datetime.now(UTC)
            version = Version(
                case_id=case_id,
                version_no=previous.version_no + 1 if previous else 1,
                prev_version_id=previous.id if previous else None,
                rule_set_id=rule.id,
                current_state="draft",
                is_complete=False,
            )
            self.session.add(version)
            await self.session.flush()
            run = AgentRun(
                case_id=case_id,
                version_id=version.id,
                rule_set_id=rule.id,
                model=model,
                impl_version=impl_version,
                limits=limits,
                started_at=now,
                outcome="running",
                stage="reading",
                turns=0,
            )
            self.session.add(run)
            await self.session.flush()
            await self._step(
                run,
                "job_start",
                "ok",
                input_documents=[
                    {"documentId": d.id, "contentHash": d.content_hash} for d in docs
                ],
            )
            run_id = run.id
        await self._export_or_fail(run_id, starting=True)
        return await self._get(run_id)

    async def _get(self, run_id, *, lock=False):
        statement = (
            select(AgentRun)
            .where(AgentRun.id == run_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        run = (await self.session.execute(statement)).scalar_one_or_none()
        if run is None:
            raise DraftError("E_NOT_FOUND", "実行が存在しません")
        return run

    async def _step(self, run, tool, result, input_documents=None):
        seq = (
            await self.session.execute(
                select(func.coalesce(func.max(AgentRunStep.seq), 0)).where(
                    AgentRunStep.agent_run_id == run.id
                )
            )
        ).scalar_one() + 1
        summary = json.dumps(
            {
                "runId": run.id,
                "caseId": run.case_id,
                "versionId": run.version_id,
                "outcome": run.outcome,
                "inputDocuments": input_documents,
            },
            sort_keys=True,
        )
        step = AgentRunStep(
            agent_run_id=run.id,
            seq=seq,
            tool_name=tool,
            args_digest=hashlib.sha256(summary.encode()).hexdigest(),
            args_summary=summary,
            result_status=result,
        )
        self.session.add(step)
        await self.session.flush()
        step.trace_event = {
            "type": "meta" if tool == "job_start" else "result",
            "at": datetime.now(UTC).isoformat(),
            "runId": run.id,
            "caseId": run.case_id,
            "inputDocuments": input_documents,
            "seq": seq,
            "tool": tool,
            "result": result,
            "versionId": run.version_id,
            "outcome": run.outcome,
            "stopReason": run.stop_reason,
            "model": run.model,
            "implVersion": run.impl_version,
            "ruleSetId": run.rule_set_id,
            "limits": run.limits,
        }
        if tool == "job_finish":
            # finish() stores the terminal fixed diagnostic code (e.g. tool_rejected).
            step.trace_event = {**step.trace_event, "stopDetail": run.stage_detail}

    async def _export_or_fail(self, run_id, *, starting=False):
        if self.trace is None:
            return
        try:
            # Serialize exports with run/step writers. Every event here committed
            # in a previous transaction, so even export-commit failure is retry-safe.
            async with self._transaction():
                await self._get(run_id, lock=True)
                events = list(
                    (
                        await self.session.execute(
                            select(AgentRunStep.trace_event)
                            .where(
                                AgentRunStep.agent_run_id == run_id,
                                AgentRunStep.trace_event.is_not(None),
                            )
                            .order_by(AgentRunStep.seq)
                        )
                    ).scalars()
                )
                events = [event for event in events if event is not None]
                # Recovery events alone cannot reconstruct the beginning of a legacy run.
                if (
                    not events
                    or events[0].get("seq") != 1
                    or events[0].get("tool") != "job_start"
                ):
                    return
                self.trace.sync(run_id, events)
        except OSError:
            logging.getLogger(__name__).error("Agent trace write failed")
            async with self._transaction():
                run = await self._get(run_id, lock=True)
                if run.stage_detail == "trace_write_failed":
                    return
                if run.outcome == "success" or (starting and run.outcome == "running"):
                    run.outcome = "failed"
                    run.stop_reason = "failed"
                run.stage_detail = "trace_write_failed"
                if run.outcome != "running":
                    run.stage = "done"
                    run.ended_at = run.ended_at or datetime.now(UTC)
                    run.elapsed_sec = Decimal(
                        str(
                            max(
                                0,
                                (
                                    utc(run.ended_at) - utc(run.started_at)
                                ).total_seconds(),
                            )
                        )
                    )
                await self._step(run, "job_trace_failure", "error")

    async def finish(self, run_id, result):
        async with self._transaction():
            run = await self._get(run_id, lock=True)
            if run.outcome == "running":
                version = (
                    await self.session.get(Version, run.version_id)
                    if run.version_id
                    else None
                )
                if result.stop_reason == "completed" and (
                    version is None
                    or version.finalized_at is None
                    or version.case_id != run.case_id
                    or version.rule_set_id != run.rule_set_id
                ):
                    result = RunResult("failed", result.turns, "draft_not_finalized")
                run.stop_reason = result.stop_reason
                run.outcome = (
                    "success"
                    if result.stop_reason == "completed"
                    else ("failed" if result.stop_reason == "failed" else "stopped")
                )
                run.stage = "done"
                run.stage_detail = result.detail
                if result.turns is not None:
                    run.turns = result.turns
                run.ended_at = datetime.now(UTC)
                run.elapsed_sec = Decimal(
                    str(
                        max(
                            0, (utc(run.ended_at) - utc(run.started_at)).total_seconds()
                        )
                    )
                )
                await self._step(
                    run, "job_finish", "ok" if run.outcome == "success" else "error"
                )
        await self._export_or_fail(run_id)
        return await self._get(run_id)

    async def progress(self, run_id):
        run = await self._get(run_id)
        version = (
            await self.session.get(Version, run.version_id)
            if run.outcome == "success" and run.version_id
            else None
        )
        visible = version is not None and version.finalized_at is not None
        elapsed = (
            run.elapsed_sec
            if run.ended_at
            else Decimal(
                str(max(0, (datetime.now(UTC) - utc(run.started_at)).total_seconds()))
            )
        )
        return dict(
            run_id=run.id,
            outcome=run.outcome,
            stage=run.stage,
            stage_detail=run.stage_detail,
            turns=run.turns,
            elapsed_sec=elapsed,
            stop_reason=run.stop_reason,
            limits=run.limits,
            version_id=version.id if visible else None,
            is_complete=bool(visible and version.is_complete),
        )

    async def steps(self, run_id):
        await self._get(run_id)
        return list(
            (
                await self.session.execute(
                    select(AgentRunStep)
                    .where(AgentRunStep.agent_run_id == run_id)
                    .order_by(AgentRunStep.seq)
                )
            ).scalars()
        )

    async def recover_interrupted(self):
        runs = list(
            (
                await self.session.execute(
                    select(AgentRun)
                    .where(AgentRun.outcome == "running")
                    .execution_options(populate_existing=True)
                )
            ).scalars()
        )
        now = datetime.now(UTC)
        for run in runs:
            if _is_recoverable(run, now):
                # finish exports only this recovered run after committing its end.
                await self.finish(
                    run.id, RunResult("failed", detail="process_interrupted")
                )

    async def recover_expired(self, *, run_id=None, case_id=None):
        query = select(AgentRun).where(AgentRun.outcome == "running")
        if run_id is not None:
            query = query.where(AgentRun.id == run_id)
        if case_id is not None:
            query = query.where(AgentRun.case_id == case_id)
        runs = list(
            (
                await self.session.execute(
                    query.execution_options(populate_existing=True)
                )
            ).scalars()
        )
        now = datetime.now(UTC)
        for run in runs:
            if _is_recoverable(run, now):
                await self.finish(
                    run.id,
                    RunResult(
                        "outer_timeout", turns=run.turns, detail="terminal_recovery"
                    ),
                )
