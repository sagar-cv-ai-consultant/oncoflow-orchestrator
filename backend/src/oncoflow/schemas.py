"""Validated input and output contracts for operational commands."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportStatus = Literal[
    "pending", "final", "corrected", "cancelled", "entered-in-error"
]
Location = Literal["waiting_room", "nearby", "with_team", "left"]
Action = Literal[
    "report_status",
    "start_consult",
    "finish_consult",
    "clearance",
    "pharmacy_ready",
    "start_infusion",
    "finish_infusion",
    "location",
    "no_show",
]
Stage = Literal[
    "awaiting_reports",
    "ready_for_consult",
    "with_doctor",
    "awaiting_clearance",
    "awaiting_pharmacy",
    "ready_for_chair",
    "infusing",
    "discharged",
    "no_show",
]


class Command(BaseModel):
    """A versioned command; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=0)
    action: Action
    panel: Literal["CBC", "CMP"] | None = None
    status: ReportStatus | None = None
    chair: int | None = Field(default=None, ge=1, le=6)
    location: Location | None = None


class CommandResult(BaseModel):
    """Indicate whether an identical event was already processed."""

    duplicate: bool


class GhostApproval(BaseModel):
    """Coordinator confirmation tied to a specific clinic revision."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=0)
    booked_patient_id: str = Field(min_length=1)
    replacement_id: str = Field(min_length=1)
    chair: int = Field(ge=1, le=6)


class DemoClockUpdate(BaseModel):
    """Advance the synthetic clinic clock for a replayable demo."""

    model_config = ConfigDict(extra="forbid")

    minute: int = Field(ge=0, le=480)
    expected_revision: int = Field(ge=0)


class DemoOnboardRequest(BaseModel):
    """Add a fixed synthetic visit with a completed report status."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=0)


class ReportWebhook(BaseModel):
    """Synthetic source event; report content is discarded at the adapter."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    patient_id: str = Field(min_length=1)
    panel: Literal["CBC", "CMP"]
    source_sequence: int = Field(ge=1)
    report: dict
