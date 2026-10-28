"""Visit entities own workflow decisions; no clinical values are modeled."""

from pydantic import BaseModel, ConfigDict

from .exceptions import WorkflowError
from .schemas import Command, Location, ReportStatus, Stage


class PatientVisit(BaseModel):
    """A visit with validated state and explicit operational transitions."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str
    alias: str
    priority: int
    panels: dict[str, ReportStatus]
    consult_done: bool = False
    in_consult: bool = False
    cleared: bool = False
    pharmacy_ready: bool = False
    infusing: bool = False
    chair: int | None = None
    closed: str | None = None
    version: int = 0
    location: Location = "waiting_room"
    arrival: str
    updated_at: str

    @property
    def labs_available(self) -> bool:
        """All required reports must be final, without reading values."""
        return all(status == "final" for status in self.panels.values())

    @property
    def blockers(self) -> list[str]:
        """List unmet prerequisites without interpreting medical data."""
        if self.closed:
            return []
        items = [
            f"{code} report {status}"
            for code, status in self.panels.items()
            if status != "final"
        ]
        if not self.consult_done:
            items.append("Consultation incomplete")
        if not self.cleared:
            items.append("Clinician clearance not recorded")
        if not self.pharmacy_ready:
            items.append("Pharmacy not ready")
        return items

    @property
    def stage(self) -> Stage:
        """Derive the displayed stage, preserving ongoing care."""
        if self.closed == "discharged":
            return "discharged"
        if self.closed == "no_show":
            return "no_show"
        if self.infusing:
            return "infusing"
        if not self.labs_available:
            return "awaiting_reports"
        if self.in_consult:
            return "with_doctor"
        if not self.consult_done:
            return "ready_for_consult"
        if not self.cleared:
            return "awaiting_clearance"
        if not self.pharmacy_ready:
            return "awaiting_pharmacy"
        return "ready_for_chair"

    def to_view(self) -> dict:
        """Add derived fields to the persisted data for the dashboard."""
        return {
            **self.model_dump(),
            "stage": self.stage,
            "blockers": self.blockers,
        }

    def apply(self, command: Command, occupied_chairs: set[int]) -> None:
        """Apply a supported transition; callers persist only on success."""
        if self.closed:
            raise WorkflowError("This visit is closed.")
        handlers = {
            "report_status": lambda: self._update_report(command),
            "start_consult": self._start_consultation,
            "finish_consult": self._finish_consultation,
            "clearance": self._record_clearance,
            "pharmacy_ready": self._record_pharmacy_ready,
            "start_infusion": lambda: self._start_infusion(
                command.chair, occupied_chairs
            ),
            "finish_infusion": self._finish_infusion,
            "location": lambda: self._update_location(command.location),
            "no_show": self._mark_no_show,
        }
        handlers[command.action]()

    def _update_report(self, command: Command) -> None:
        if command.panel not in self.panels or command.status is None:
            raise WorkflowError(
                "Choose a required panel and its report status."
            )
        self.panels[command.panel] = command.status
        if command.status != "final":
            self.cleared = False
            self.pharmacy_ready = False

    def _start_consultation(self) -> None:
        if self.stage != "ready_for_consult":
            raise WorkflowError(
                "Required reports must be final before starting "
                "this demo consultation."
            )
        self.in_consult = True
        self.location = "with_team"

    def _finish_consultation(self) -> None:
        if not self.in_consult or not self.labs_available:
            raise WorkflowError(
                "An active consultation and final reports are required. "
                "Review any report changes."
            )
        self.in_consult = False
        self.consult_done = True
        self.location = "waiting_room"

    def _record_clearance(self) -> None:
        if not self.consult_done or not self.labs_available or self.infusing:
            raise WorkflowError(
                "A completed consultation and final reports are required "
                "before recording clearance."
            )
        self.cleared = True

    def _record_pharmacy_ready(self) -> None:
        if not self.cleared or not self.labs_available or self.infusing:
            raise WorkflowError(
                "Record clinician clearance before marking pharmacy ready."
            )
        self.pharmacy_ready = True

    def _start_infusion(
        self, chair: int | None, occupied_chairs: set[int]
    ) -> None:
        if self.stage != "ready_for_chair":
            raise WorkflowError(
                "All prerequisites must be complete before starting infusion."
            )
        if self.location != "waiting_room":
            raise WorkflowError(
                "Confirm the patient has returned to the waiting room first."
            )
        if chair is None or chair in occupied_chairs:
            raise WorkflowError("Choose an available chair.")
        self.chair = chair
        self.infusing = True
        self.location = "with_team"

    def _finish_infusion(self) -> None:
        if not self.infusing:
            raise WorkflowError("This patient is not currently infusing.")
        self.infusing = False
        self.closed = "discharged"
        self.location = "left"
        self.chair = None

    def _update_location(self, location: Location | None) -> None:
        if (
            location not in ("waiting_room", "nearby")
            or self.infusing
            or self.in_consult
        ):
            raise WorkflowError(
                "Location can change between waiting room and nearby "
                "while awaiting care."
            )
        self.location = location

    def _mark_no_show(self) -> None:
        if self.infusing or self.in_consult:
            raise WorkflowError(
                "An active visit cannot be marked as a no-show."
            )
        self.closed = "no_show"
        self.location = "left"
