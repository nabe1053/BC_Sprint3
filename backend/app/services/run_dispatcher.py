"""Service-layer job dispatch. The composition root chooses the local worker."""
from app.agent.jobs import start_agent_job
from app.domain.run_types import RunContext


class RunDispatcher:
    def __init__(self, background, worker, limits):
        self.background = background
        self.worker = worker
        self.limits = limits

    def __call__(self, run):
        context = RunContext(
            run.id, run.case_id, run.version_id, run.rule_set_id, self.limits
        )

        async def work():
            return await self.worker(context)

        async def finish(result):
            await self.background.finish(context.run_id, result)

        return start_agent_job(
            run.id,
            work=work,
            on_finish=finish,
            outer_timeout_s=self.limits.outer_timeout_s,
        )
