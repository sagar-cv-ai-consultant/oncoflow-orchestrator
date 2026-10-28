"""Deterministic fictional visit states for the manual milestone."""

from datetime import datetime, timezone

from .domain import PatientVisit


def utc_timestamp() -> str:
    """Return an aware UTC timestamp for audit records."""
    return datetime.now(timezone.utc).isoformat()


def demo_visits() -> list[PatientVisit]:
    """Create the same twelve visits and six-chair fixture as milestone 01."""
    visits = []
    for index in range(1, 13):
        panels = {"CBC": "final" if index % 3 else "pending"}
        if index % 2 == 0:
            panels["CMP"] = "pending" if index % 4 == 0 else "final"
        location = "waiting_room"
        if index in (1, 2):
            location = "with_team"
        elif index in (4, 8):
            location = "nearby"
        visits.append(
            PatientVisit(
                id=f"OF-{index:03}",
                alias=f"Demo patient {index:02}",
                priority=1 if index in (3, 7) else 0,
                panels=panels,
                consult_done=index in (1, 5, 7, 11),
                in_consult=index == 2,
                cleared=index in (1, 7, 11),
                pharmacy_ready=index in (1, 7),
                infusing=index == 1,
                chair=1 if index == 1 else None,
                location=location,
                arrival=(
                    f"{8 + (index - 1) // 4:02}:{((index - 1) % 4) * 12:02}"
                ),
                updated_at=utc_timestamp(),
            )
        )
    return visits
