"""Composition root. Runtime settings are never needed for isolated schema export."""
from contextlib import aclosing, asynccontextmanager
from functools import partial
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.database import get_db
from app.core.config import settings
from app.agent.jobs import stop_jobs
from app.agent import definition
from app.agent.claude_policy import claude_policy
from app.agent.local_policy import local_dummy_policy
from app.agent.runner import LocalAgentWorker
from app.agent.definition import default_run_limits
from app.domain.run_types import InputLimits
from app.repositories.draft_repository import DraftRepository
from app.repositories.run_repository import RunRepository
from app.repositories.run_input_files import RunInputFiles
from app.repositories.run_trace_store import RunTraceStore
from app.repositories.run_background import RunBackground
from app.repositories.agent_tool_repository import AgentToolGateway
from app.services.draft_service import DraftService
from app.services.inventory_service import InventoryService
from app.repositories.inventory_repository import InventoryRepository
from app.services.record_service import RecordService
from app.repositories.record_repository import RecordRepository
from app.services.run_service import RunService
from app.services.run_dispatcher import RunDispatcher


async def get_draft_service(session: AsyncSession = Depends(get_db)) -> DraftService:
    return DraftService(DraftRepository(session))


async def get_record_service(session: AsyncSession = Depends(get_db)) -> RecordService:
    return RecordService(RecordRepository(session))


async def get_inventory_service(
    session: AsyncSession = Depends(get_db)
) -> InventoryService:
    return InventoryService(InventoryRepository(session))


def make_run_repository(session):
    return RunRepository(
        session,
        file_size=RunInputFiles(settings.STORAGE_ROOT).size,
        trace=RunTraceStore(),
    )


async def get_run_service(session: AsyncSession = Depends(get_db)) -> RunService:
    sessions = async_sessionmaker(session.bind, expire_on_commit=False)
    limits = default_run_limits()
    background = RunBackground(
        sessions,
        file_size=RunInputFiles(settings.STORAGE_ROOT).size,
        trace=RunTraceStore(),
    )
    use_claude = settings.AGENT_MODE == "claude"
    policy = (
        partial(claude_policy, api_key=settings.ANTHROPIC_API_KEY)
        if use_claude
        else local_dummy_policy
    )
    worker = LocalAgentWorker(AgentToolGateway(sessions), policy_factory=policy)
    dispatcher = RunDispatcher(
        background, worker, limits, before_finish=worker.prepare_finish
    )
    return RunService(
        make_run_repository(session),
        limits=limits,
        input_limits=InputLimits(
            max_documents=settings.MAX_DOCUMENTS_PER_CASE,
            max_file_bytes=settings.MAX_FILE_SIZE_MB * 1024 * 1024,
            max_pdf_pages=settings.MAX_PDF_PAGES,
            max_xlsx_sheets=settings.MAX_XLSX_SHEETS,
        ),
        scheduler=dispatcher,
        external=use_claude and not settings.ANTHROPIC_API_KEY,
        model=definition.MODEL_ID if use_claude else definition.DUMMY_MODEL_ID,
    )


@asynccontextmanager
async def run_lifespan(app):
    # Another process may still be working; recovery checks saved deadlines.
    session_provider = app.dependency_overrides.get(get_db, get_db)
    async with aclosing(session_provider()) as sessions:
        async for session in sessions:
            await make_run_repository(session).recover_interrupted()
            break
    try:
        yield
    finally:
        await stop_jobs()
