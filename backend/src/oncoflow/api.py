"""FastAPI transport; application creation does not create a database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .exceptions import ConflictError, VisitNotFoundError, WorkflowError
from .repository import SQLiteVisitRepository
from .schemas import (
    Command,
    CommandResult,
    DemoClockUpdate,
    DemoOnboardRequest,
    GhostApproval,
    ReportWebhook,
)
from .service import ClinicService


def get_service(request: Request) -> ClinicService:
    """Resolve the instance created during this application's startup."""
    return request.app.state.clinic_service


ServiceDependency = Annotated[ClinicService, Depends(get_service)]


def create_app(
    path: str | Path | None = None, scenario: str = "manual"
) -> FastAPI:
    """Build an app with injectable storage for isolated workflow tests."""
    settings = (
        Settings(
            database_path=Path(path),
            scenario=scenario,
            demo_routes_enabled=True,
        )
        if path is not None
        else Settings.from_environment()
    )

    def require_demo_routes() -> None:
        if not settings.demo_routes_enabled:
            raise HTTPException(status_code=404, detail="Not found.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = SQLiteVisitRepository(settings.database_path)
        repository.initialize(settings.scenario)
        app.state.clinic_service = ClinicService(repository)
        yield

    app = FastAPI(
        title="OncoFlow local synthetic prototype", lifespan=lifespan
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Default validation errors can echo rejected clinical input.
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid operational command fields."},
        )

    @app.exception_handler(ConflictError)
    async def conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(VisitNotFoundError)
    async def not_found(
        request: Request, exc: VisitNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(WorkflowError)
    async def blocked(request: Request, exc: WorkflowError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": "synthetic_demo",
            "ai_enabled": False,
            "scheduler_enabled": True,
            "scheduler_mode": "advisory_heuristic",
            "ghost_solver": "cp_sat_with_heuristic_fallback",
        }

    @app.get("/api/state")
    def state(service: ServiceDependency) -> dict:
        return service.snapshot()

    @app.post(
        "/api/visits/{patient_id}/commands", response_model=CommandResult
    )
    def command(
        patient_id: str, body: Command, service: ServiceDependency
    ) -> CommandResult:
        return service.execute(patient_id, body)

    @app.post(
        "/api/demo/visits/{patient_id}/reports/{panel}",
        response_model=CommandResult,
        dependencies=[Depends(require_demo_routes)],
    )
    def report(
        patient_id: str,
        panel: str,
        body: dict,
        expected_version: int,
        event_id: str,
        service: ServiceDependency,
    ) -> CommandResult:
        try:
            return service.receive_report(
                patient_id,
                panel,
                body,
                expected_version=expected_version,
                event_id=event_id,
            )
        except ValueError:
            raise HTTPException(422, "Invalid report status event.") from None

    @app.post("/api/ghost-slots/approve", response_model=CommandResult)
    def approve_ghost(
        body: GhostApproval, service: ServiceDependency
    ) -> CommandResult:
        return service.approve_ghost(body)

    @app.post("/api/demo/clock", dependencies=[Depends(require_demo_routes)])
    def demo_clock(body: DemoClockUpdate, service: ServiceDependency) -> dict:
        service.advance_clock(body.minute, body.expected_revision)
        return {"minute": body.minute}

    @app.post(
        "/api/demo/onboard",
        response_model=CommandResult,
        dependencies=[Depends(require_demo_routes)],
    )
    def demo_onboard(
        body: DemoOnboardRequest, service: ServiceDependency
    ) -> CommandResult:
        return service.onboard_demo_visit(body)

    @app.post(
        "/api/demo/webhook/report",
        response_model=CommandResult,
        dependencies=[Depends(require_demo_routes)],
    )
    def demo_report_webhook(
        body: ReportWebhook, service: ServiceDependency
    ) -> CommandResult:
        try:
            return service.receive_webhook(body)
        except ValueError:
            raise HTTPException(422, "Invalid report status event.") from None

    return app
