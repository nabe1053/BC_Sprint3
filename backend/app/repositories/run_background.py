"""Background persistence gateway: sessions outlive neither a callback nor a request."""
from app.repositories.run_repository import RunRepository


class RunBackground:
    def __init__(self, sessions, *, file_size, trace):
        self.sessions = sessions
        self.file_size = file_size
        self.trace = trace

    async def finish(self, run_id, result):
        async with self.sessions() as session:
            await RunRepository(
                session, file_size=self.file_size, trace=self.trace
            ).finish(run_id, result)
