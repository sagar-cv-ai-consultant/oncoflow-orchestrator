"""Application use cases shared by HTTP handlers and integration adapters."""

from .adapters.fhir import FHIRReportAdapter
from .config import CHAIR_COUNT
from .repository import SQLiteVisitRepository
from .schemas import Command, CommandResult


class ClinicService:
    """Coordinate status-only input, domain transitions and persistence."""

    def __init__(self, repository: SQLiteVisitRepository) -> None:
        self.repository = repository

    def snapshot(self) -> dict:
        """Return the existing dashboard contract with derived visit state."""
        visits, events, revision = self.repository.read_snapshot()
        return {
            "patients": [visit.to_view() for visit in visits],
            "events": events,
            "revision": revision,
            "mode": "synthetic_demo",
            "chair_count": CHAIR_COUNT,
        }

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
