"""Application use cases shared by HTTP handlers and integration adapters."""

from .adapters.fhir import FHIRReportAdapter
from .config import CHAIR_COUNT
from .repository import SQLiteVisitRepository
from .scheduler import ChairScheduler
from .schemas import (
    Command,
    CommandResult,
    DemoOnboardRequest,
    GhostApproval,
    ReportWebhook,
)


class ClinicService:
    """Coordinate status-only input, domain transitions and persistence."""

    def __init__(self, repository: SQLiteVisitRepository) -> None:
        self.repository = repository
        self.scheduler = ChairScheduler()

    def snapshot(self) -> dict:
        """Return the existing dashboard contract with derived visit state."""
        visits, events, revision, minute, scenario = (
            self.repository.read_snapshot()
        )
        return {
            "patients": [visit.to_view() for visit in visits],
            "events": events,
            "revision": revision,
            "mode": "synthetic_demo",
            "chair_count": CHAIR_COUNT,
            "schedule": self.scheduler.recommend(visits, minute),
            "ghost_slots": self.scheduler.ghost_slots(visits, minute),
            "demo_minute": minute,
            "scenario": scenario,
        }

    def approve_ghost(self, body: GhostApproval) -> CommandResult:
        """Confirm a currently feasible ghost-slot replacement."""
        return CommandResult(duplicate=self.repository.approve_ghost(body))

    def advance_clock(self, minute: int, expected_revision: int) -> None:
        """Advance only the fictional demonstration clock."""
        self.repository.advance_clock(minute, expected_revision)

    def onboard_demo_visit(self, body: DemoOnboardRequest) -> CommandResult:
        """Accept a synthetic visit at its current recorded stage."""
        return CommandResult(
            duplicate=self.repository.onboard_demo_visit(body)
        )

    def receive_webhook(self, body: ReportWebhook) -> CommandResult:
        """Normalize the synthetic source report to a status-only event."""
        report = FHIRReportAdapter.normalize(body.report)
        return CommandResult(
            duplicate=self.repository.apply_report_webhook(
                body.patient_id,
                body.panel,
                report["status"],
                body.source_sequence,
                body.event_id,
            )
        )

    def execute(self, patient_id: str, command: Command) -> CommandResult:
        """Persist a versioned operational command."""
        return CommandResult(
            duplicate=self.repository.execute(patient_id, command)
        )

    def receive_report(
        self,
        patient_id: str,
        panel: str,
        payload: dict,
        *,
        expected_version: int,
        event_id: str,
    ) -> CommandResult:
        """Drop report content before constructing a persistent command."""
        report = FHIRReportAdapter.normalize(payload)
        command = Command(
            event_id=event_id,
            expected_version=expected_version,
            action="report_status",
            panel=panel,
            status=report["status"],
        )
        return self.execute(patient_id, command)
