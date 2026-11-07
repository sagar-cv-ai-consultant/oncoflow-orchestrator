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
                scheduled_duration_minutes=(60, 90, 120)[(index - 1) % 3],
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


def ghost_day_visits() -> list[PatientVisit]:
    """Seed two overdue bookings and two ready replacements for a demo."""
    visits = demo_visits()
    by_id = {visit.id: visit for visit in visits}
    for visit_id, chair in (
        ("OF-001", 1),
        ("OF-002", 4),
        ("OF-005", 5),
        ("OF-010", 6),
    ):
        visit = by_id[visit_id]
        visit.panels = {"CBC": "final"}
        visit.in_consult = False
        visit.consult_done = True
        visit.cleared = True
        visit.pharmacy_ready = True
        visit.infusing = True
        visit.chair = chair
        visit.location = "with_team"
        visit.infusion_started_minute = 130

    for visit_id, chair in (("OF-003", 2), ("OF-004", 3)):
        visit = by_id[visit_id]
        visit.panels = {"CBC": "pending"}
        visit.booked_start_minute = 135
        visit.booked_chair = chair
        visit.booking_status = "active"
        visit.scheduled_duration_minutes = 60

    for visit_id, chair, start in (
        ("OF-012", 2, 300),
        ("OF-006", 3, 330),
    ):
        visit = by_id[visit_id]
        visit.booked_chair = chair
        visit.booked_start_minute = start
        visit.booking_status = "active"

    for visit_id, priority, ready_at, appointment in (
        ("OF-007", 1, 90, 100),
        ("OF-011", 0, 110, 120),
    ):
        visit = by_id[visit_id]
        visit.panels = {"CBC": "final"}
        visit.consult_done = True
        visit.cleared = True
        visit.pharmacy_ready = True
        visit.priority = priority
        visit.location = "waiting_room"
        visit.ready_since_minute = ready_at
        visit.appointment_minute = appointment
        visit.scheduled_duration_minutes = 60

    return visits
