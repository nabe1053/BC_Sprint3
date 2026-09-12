"""Per-tool sessions, scope locks, and atomic artifact/trace persistence."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import json
import hashlib

from sqlalchemy import select, func

from app.models import (
    Case,
    RuleSet,
    Version,
    AgentRun,
    AgentRunStep,
)
from app.models.documents import DocumentIssue
from app.repositories.document_repository import DocumentRepository
from app.repositories.draft_repository import DraftRepository, require


def check_open(closed):
    if closed.is_set():
        raise asyncio.CancelledError


class AgentToolRepository(DraftRepository):
    """DraftService reuses its existing validation; the outer gateway owns commit."""

    def __init__(self, session, context, run):
        super().__init__(session)
        self.context = context
        self.run = run
        self.documents = DocumentRepository(session)

    @asynccontextmanager
    async def _transaction(self):
        yield
        await self.session.flush()

    async def document(self, document_id):
        document = await self.documents.get_by_id(document_id)
        require(document is not None and document.case_id == self.context.case_id)
        return document

    async def list_documents(self):
        case = await self.session.get(Case, self.context.case_id)
        require(case is not None)
        documents = await self.documents.list_by_case(case.id)
        return {
            "case_id": case.id,
            "case_name": case.title,
            "documents": [
                {
                    "document_id": d.id,
                    "file_name": d.file_name,
                    "kind": d.kind,
                    "page_count": d.page_count,
                    "read_status": d.read_status,
                }
                for d in documents
            ],
        }

    async def read_document(self, document_id, from_seq, to_seq):
        document = await self.document(document_id)
        require(
            document.kind != "eml",
            "E_VALIDATION_FAILED",
            "メールはread_emailで取得してください",
        )
        pages = await self.documents.list_pages(document_id, from_seq, to_seq)
        require(
            all(not p.locator.startswith("email:") for p in pages),
            "E_VALIDATION_FAILED",
            "資料の位置表記が不正です",
        )
        return {
            "pages": [
                {
                    "locator": p.locator,
                    "text": p.text,
                    "cells": p.cells,
                    "read_status": "success"
                    if (p.text and p.text.strip()) or p.cells
                    else "unreadable",
                }
                for p in pages
            ]
        }

    async def read_email(self, document_id):
        document = await self.document(document_id)
        require(document.kind == "eml", "E_NOT_EMAIL", "メール資料ではありません")
        parts = await self.documents.list_email_parts(document_id)
        require(
            len({(p.part_role, p.seq) for p in parts}) == len(parts),
            "E_VALIDATION_FAILED",
            "メールの位置表記が重複しています",
        )
        return {
            "parts": [
                {
                    "part_role": p.part_role,
                    "seq": p.seq,
                    "locator": f"email:{p.part_role}:{p.seq}",
                    "sent_at": p.sent_at.isoformat() if p.sent_at else None,
                    "from_addr": p.from_addr,
                    "subject": p.subject,
                    "body": p.body,
                    "attachment_name": p.attachment_name,
                }
                for p in parts
            ]
        }

    async def search(self, query, limit):
        rows = await self.documents.search_pages(self.context.case_id, query, limit)
        return {
            "results": [
                {
                    "document_id": d.id,
                    "locator": p.locator,
                    "excerpt": (p.text or "")[:200],
                }
                for d, p in rows
            ]
        }

    async def get_rules(self):
        rule = await self.session.get(RuleSet, self.context.rule_set_id)
        require(rule is not None)
        require(
            not rule.conversion_enabled,
            "E_VALIDATION_FAILED",
            "換算は無効である必要があります",
        )
        return {
            "rule_set_id": rule.id,
            "rule_version": rule.rule_version,
            "rules": rule.rules,
            "conversion_enabled": False,
        }

    async def report_unreadable(self, args):
        await self.document(args.document_id)
        issue = DocumentIssue(
            document_id=args.document_id,
            agent_run_id=self.context.run_id,
            locator=args.locator,
            issue_type=args.issue_type,
            detail=args.detail,
        )
        self.session.add(issue)
        await self.session.flush()
        return {"issue_id": issue.id}

    async def record_interruption(self, snapshot, violations, reason):
        existing = (
            await self.session.execute(
                select(AgentRunStep.id).where(
                    AgentRunStep.agent_run_id == self.context.run_id,
                    AgentRunStep.tool_name == "job_interrupted",
                )
            )
        ).first()
        if existing:
            return
        remaining = (
            snapshot.readable_ranges - snapshot.scanned_ranges - snapshot.excused_ranges
        )
        self.session.add_all(
            [
                DocumentIssue(
                    document_id=document,
                    agent_run_id=self.context.run_id,
                    locator=locator,
                    issue_type="not_scanned",
                    detail="実行停止時に未走査の範囲です",
                )
                for document, locator in sorted(remaining)
            ]
        )
        if self.run.validation_result is None:
            self.run.validation_result = violations
        step = await self.add_step(
            "job_interrupted",
            hashlib.sha256(reason.encode()).hexdigest(),
            self.run.stage,
        )
        self.event(step, self.run.stage, "error", count=len(remaining), code=reason)

    async def add_step(self, name, digest, stage, parent_step_id=None):
        # Every caller holds the run row lock; max+1 is serialized across sessions.
        seq = (
            await self.session.execute(
                select(func.coalesce(func.max(AgentRunStep.seq), 0)).where(
                    AgentRunStep.agent_run_id == self.context.run_id
                )
            )
        ).scalar_one() + 1
        step = AgentRunStep(
            agent_run_id=self.context.run_id,
            seq=seq,
            tool_name=name,
            args_digest=digest,
            args_summary=json.dumps(
                {"caseId": self.context.case_id, "versionId": self.context.version_id}
            ),
            result_status="error",
            parent_step_id=parent_step_id,
        )
        self.session.add(step)
        await self.session.flush()
        self.event(step, stage, "pending")
        return step

    def event(self, step, stage, status, *, count=0, code=None):
        run = self.run
        step.trace_event = {
            "type": "tool_use",
            "at": datetime.now(UTC).isoformat(),
            "seq": step.seq,
            "runId": run.id,
            "caseId": run.case_id,
            "versionId": run.version_id,
            "ruleSetId": run.rule_set_id,
            "model": run.model,
            "implVersion": run.impl_version,
            "limits": run.limits,
            "tool": step.tool_name,
            "result": status,
            "outcome": run.outcome,
            "stopReason": run.stop_reason,
            "input": {"caseId": run.case_id, "versionId": run.version_id},
            "decision": stage,
            "tool_use": {"name": step.tool_name, "argsDigest": step.args_digest},
            "observation": {"status": status, "count": count, "code": code},
            "documentId": step.document_id,
            "locator": step.locator,
        }

    async def record_result(self, step_id, name, args, data):
        step = await self.session.get(AgentRunStep, step_id)
        require(step is not None and step.agent_run_id == self.context.run_id)
        locators = []
        if name == "read_document":
            locators = [
                p["locator"] for p in data["pages"] if p["read_status"] == "success"
            ]
        elif name == "read_email" and data["parts"]:
            locators = ["email:*"]
        step.result_status = "ok"
        if locators:
            step.document_id, step.locator = args.document_id, locators[0]
        count = next(
            (
                len(data[k])
                for k in (
                    "pages",
                    "parts",
                    "documents",
                    "items",
                    "entries",
                    "violations",
                    "results",
                )
                if k in data
            ),
            1,
        )
        # Active-run diagnostics remain in trace metadata; the reading payload
        # below is always a progress object, never a diagnostic string.
        diagnostic = (
            "trace_write_failed"
            if self.run.stage_detail == "trace_write_failed"
            else None
        )
        self.event(step, self.run.stage, "ok", count=count, code=diagnostic)
        for locator in locators[1:]:
            child = await self.add_step(name, step.args_digest, self.run.stage, step.id)
            child.document_id, child.locator, child.result_status = (
                args.document_id,
                locator,
                "ok",
            )
            self.event(child, self.run.stage, "ok", count=1)
        await self.session.flush()
        if name in {"list_case_documents", "read_document", "read_email"}:
            documents = (
                data["documents"]
                if name == "list_case_documents"
                else (await self.list_documents())["documents"]
            )
            snapshot = await self.snapshot(self.context.version_id)
            # Reuse the completion predicate's range semantics (including email).
            # Partial/repeated reads and child steps do not count as extra documents.
            by_document = {}
            for document_id, locator in snapshot.readable_ranges:
                by_document.setdefault(document_id, set()).add((document_id, locator))
            read = sum(
                bool(by_document.get(d["document_id"]))
                and by_document[d["document_id"]] <= snapshot.scanned_ranges
                for d in documents
            )
            progress = {"documentsRead": read, "documentsTotal": len(documents)}
            self.run.stage_detail = json.dumps(progress)
            step.trace_event = {**step.trace_event, "progress": progress}
            await self.session.flush()


class AgentToolGateway:
    def __init__(self, sessions):
        self.sessions = sessions

    async def locked(self, session, context, *, for_cleanup=False):
        version = (
            await session.execute(
                select(Version)
                .where(Version.id == context.version_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        run = (
            await session.execute(
                select(AgentRun)
                .where(AgentRun.id == context.run_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        require(run is not None and version is not None)
        require(
            run.version_id == version.id
            and run.case_id == version.case_id == context.case_id
            and run.rule_set_id == version.rule_set_id == context.rule_set_id
        )
        if not for_cleanup:
            require(run.outcome == "running", "E_RUN_NOT_ACTIVE", "終了済み実行です")
            require(
                version.finalized_at is None, "E_VERSION_FINALIZED", "確定済み版です"
            )
        return AgentToolRepository(session, context, run)

    @asynccontextmanager
    async def cleanup(self, context):
        async with self.sessions() as session, session.begin():
            repository = await self.locked(session, context, for_cleanup=True)
            yield repository if repository.run.outcome == "running" else None

    async def begin_step(self, context, name, digest, stage, closed):
        check_open(closed)
        async with self.sessions() as session, session.begin():
            repository = await self.locked(session, context)
            check_open(closed)
            repository.run.stage = stage
            repository.run.turns += 1
            step = await repository.add_step(name, digest, stage)
            check_open(closed)
            return step.id

    async def record_denial(self, context, name, code, digest, closed):
        check_open(closed)
        async with self.sessions() as session, session.begin():
            repository = await self.locked(session, context)
            check_open(closed)
            step = await repository.add_step(
                "guardrail_denied", digest, repository.run.stage
            )
            repository.event(step, repository.run.stage, "error", code=code)
            step.trace_event = {
                **step.trace_event,
                "tool_use": {**step.trace_event["tool_use"], "deniedTool": name},
            }
            check_open(closed)

    @asynccontextmanager
    async def operation(self, context, step_id, closed):
        check_open(closed)
        async with self.sessions() as session, session.begin():
            repository = await self.locked(session, context)
            check_open(closed)
            yield repository
            check_open(closed)

    async def fail_step(self, context, step_id, code, closed):
        check_open(closed)
        async with self.sessions() as session, session.begin():
            repository = await self.locked(session, context)
            step = await session.get(AgentRunStep, step_id)
            require(step is not None and step.agent_run_id == context.run_id)
            repository.event(step, repository.run.stage, "error", code=code)
            check_open(closed)
