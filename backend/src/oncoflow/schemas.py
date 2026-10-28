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
