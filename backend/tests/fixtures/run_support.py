"""Run repository/service builders; imports no test modules."""
from app.agent.definition import default_run_limits
from app.domain.run_types import InputLimits
from app.repositories.run_repository import RunRepository
from app.services.run_service import RunService


def repo(session):
    return RunRepository(session, file_size=lambda doc: 10)


def service(repository, scheduler=None, external=False):
    return RunService(
        repository,
        limits=default_run_limits(),
        input_limits=InputLimits(),
        scheduler=scheduler or (lambda run: None),
        external=external,
    )
