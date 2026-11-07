"""SQLite persistence with atomic workflow changes and audit records."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import (
    AUDIT_EVENT_LIMIT,
    CHAIR_TURNOVER_MINUTES,
    NURSE_SETUP_MINUTES,
    NURSE_START_CAPACITY,
)
from .domain import PatientVisit
from .exceptions import ConflictError, VisitNotFoundError
from .fixtures import demo_visits, ghost_day_visits, utc_timestamp
from .scheduler import ChairScheduler
from .schemas import Command, DemoOnboardRequest, GhostApproval


class SQLiteVisitRepository:
    """Persist visits with atomic version and event-identifier checks."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self, scenario: str = "manual") -> None:
        """Initialize storage and seed only when no visits exist."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS visits (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    patient_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS demo_clock (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    minute INTEGER NOT NULL,
                    scenario TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS report_source_state (
                    patient_id TEXT NOT NULL,
                    panel TEXT NOT NULL,
                    source_sequence INTEGER NOT NULL,
                    PRIMARY KEY (patient_id, panel)
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR IGNORE INTO demo_clock VALUES (1, 150, ?)",
                (scenario,),
            )
            count = connection.execute(
                "SELECT count(*) FROM visits"
            ).fetchone()[0]
            if count:
                return
            seeded = (
                ghost_day_visits() if scenario == "ghost" else demo_visits()
            )
            for index, visit in enumerate(seeded, start=1):
                connection.execute(
                    "INSERT INTO visits VALUES (?, ?)",
                    (visit.id, visit.model_dump_json()),
                )
                self._append_event(
                    connection,
                    event_id=f"seed-{index}",
                    patient_id=visit.id,
                    timestamp=visit.updated_at,
                    action="demo_seed",
                    actor="synthetic fixture",
                    payload=visit.model_dump(),
                )

    def read_snapshot(
        self,
    ) -> tuple[list[PatientVisit], list[dict], int, int, str]:
        """Read visits, audit events and revision from the same snapshot."""
        with self._connection() as connection:
            connection.execute("BEGIN")
            visits = [
                PatientVisit.model_validate_json(row["data"])
                for row in connection.execute(
                    "SELECT data FROM visits ORDER BY id"
                )
            ]
            events = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM events ORDER BY seq DESC LIMIT ?",
                    (AUDIT_EVENT_LIMIT,),
                )
            ]
            revision = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events"
            ).fetchone()[0]
            clock = connection.execute(
                "SELECT minute, scenario FROM demo_clock WHERE id = 1"
            ).fetchone()
        for event in events:
            event["payload"] = json.loads(event["payload"])
        return visits, events, revision, clock["minute"], clock["scenario"]

    def execute(self, patient_id: str, command: Command) -> bool:
        """Apply and audit a command atomically; return True for duplicates."""
        body = command.model_dump(exclude_none=True)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT patient_id, payload FROM events WHERE event_id = ?",
                (command.event_id,),
            ).fetchone()
            if previous:
                if (
                    previous["patient_id"] != patient_id
                    or json.loads(previous["payload"]) != body
                ):
                    raise ConflictError(
                        "This event identifier was already used "
                        "for a different action."
                    )
                return True
            row = connection.execute(
                "SELECT data FROM visits WHERE id = ?", (patient_id,)
            ).fetchone()
            if row is None:
                raise VisitNotFoundError("Visit not found.")
            visit = PatientVisit.model_validate_json(row["data"])
            if visit.version != command.expected_version:
                raise ConflictError(
                    "The visit changed. Refresh and review the "
                    "current state before trying again."
                )
            visits = [
                PatientVisit.model_validate_json(current["data"])
                for current in connection.execute("SELECT data FROM visits")
            ]
            occupied = {
                other.chair
                for other in visits
                if other.infusing and other.chair is not None
            }
            clock = connection.execute(
                "SELECT minute, scenario FROM demo_clock WHERE id = 1"
            ).fetchone()
            displaced_bookings: list[PatientVisit] = []
            if command.action == "start_infusion":
                active_starts = sum(
                    other.infusing
                    and other.infusion_started_minute is not None
                    and other.infusion_started_minute
                    <= clock["minute"]
                    < other.infusion_started_minute + NURSE_SETUP_MINUTES
                    for other in visits
                )
                if active_starts >= NURSE_START_CAPACITY:
                    raise ConflictError(
                        "Nurse start capacity is full. Review the schedule."
                    )
                if clock["scenario"] == "ghost":
                    owns_due_booking = (
                        visit.booking_status == "active"
                        and visit.booked_chair == command.chair
                        and visit.booked_start_minute is not None
                        and visit.booked_start_minute <= clock["minute"]
                    )
                    end = (
                        clock["minute"]
                        + visit.scheduled_duration_minutes
                        + CHAIR_TURNOVER_MINUTES
                    )
                    for other in visits:
                        if (
                            other.id == visit.id
                            or other.closed
                            or other.booking_status != "active"
                            or other.booked_chair != command.chair
                        ):
                            continue
                        earlier_missed = (
                            owns_due_booking
                            and other.booked_start_minute is not None
                            and other.booked_start_minute
                            < visit.booked_start_minute
                            and other.booked_start_minute <= clock["minute"]
                            and (
                                other.stage != "ready_for_chair"
                                or other.location != "waiting_room"
                            )
                        )
                        if earlier_missed:
                            displaced_bookings.append(other)
                            continue
                        if (
                            other.booked_start_minute is None
                            or other.booked_start_minute <= clock["minute"]
                            or end > other.booked_start_minute
                        ):
                            raise ConflictError(
                                "This chair has a protected booking. "
                                "Review the current chair plan."
                            )
            was_ready = visit.stage == "ready_for_chair"
            visit.apply(command, occupied)
            if visit.stage == "ready_for_chair" and not was_ready:
                visit.ready_since_minute = clock["minute"]
            elif visit.stage != "ready_for_chair" and not visit.infusing:
                visit.ready_since_minute = None
            if command.action == "start_infusion":
                visit.infusion_started_minute = clock["minute"]
                visit.ready_since_minute = None
                if clock["scenario"] == "ghost":
                    visit.booking_status = "active"
                    visit.booked_chair = command.chair
                    visit.booked_start_minute = clock["minute"]
            visit.version += 1
            visit.updated_at = utc_timestamp()
            connection.execute(
                "UPDATE visits SET data = ? WHERE id = ?",
                (visit.model_dump_json(), patient_id),
            )
            for other in displaced_bookings:
                other.booking_status = "displaced"
                other.version += 1
                other.updated_at = utc_timestamp()
                connection.execute(
                    "UPDATE visits SET data = ? WHERE id = ?",
                    (other.model_dump_json(), other.id),
                )
            self._append_event(
                connection,
                event_id=command.event_id,
                patient_id=patient_id,
                timestamp=visit.updated_at,
                action=command.action,
                actor="local demo operator",
                payload=body,
            )
        return False

    def approve_ghost(self, body: GhostApproval) -> bool:
        """Revalidate and fill an overdue slot in one audited transaction."""
        payload = body.model_dump()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT payload FROM events WHERE event_id = ?",
                (body.event_id,),
            ).fetchone()
            if previous:
                if json.loads(previous["payload"]) != payload:
                    raise ConflictError("Event identifier already used.")
                return True
            revision = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events"
            ).fetchone()[0]
            if body.expected_revision != revision:
                raise ConflictError("Clinic state changed. Review the plan.")
            clock = connection.execute(
                "SELECT minute FROM demo_clock WHERE id = 1"
            ).fetchone()[0]
            visits = [
                PatientVisit.model_validate_json(row["data"])
                for row in connection.execute("SELECT data FROM visits")
            ]
            slot = next(
                (
                    item
                    for item in ChairScheduler().ghost_slots(visits, clock)
                    if item["booked_patient_id"] == body.booked_patient_id
                    and item["chair"] == body.chair
                    and item["replacement"] is not None
                    and item["replacement"]["patient_id"]
                    == body.replacement_id
                ),
                None,
            )
            if slot is None:
                raise ConflictError("Ghost-slot proposal changed. Review it.")
            by_id = {visit.id: visit for visit in visits}
            booked = by_id[body.booked_patient_id]
            replacement = by_id[body.replacement_id]
            occupied = {visit.chair for visit in visits if visit.infusing}
            command = Command(
                event_id=body.event_id,
                expected_version=replacement.version,
                action="start_infusion",
                chair=body.chair,
            )
            replacement.apply(command, occupied)
            replacement.infusion_started_minute = clock
            replacement.booked_chair = body.chair
            replacement.booked_start_minute = clock
            replacement.booking_status = "active"
            replacement.ready_since_minute = None
            superseded = [
                other
                for other in visits
                if other.id not in (booked.id, replacement.id)
                and other.booking_status == "active"
                and other.booked_chair == body.chair
                and other.booked_start_minute is not None
                and other.booked_start_minute <= booked.booked_start_minute
                and (
                    other.stage != "ready_for_chair"
                    or other.location != "waiting_room"
                )
            ]
            for original in (booked, *superseded):
                original.booking_status = "displaced"
            for visit in (booked, replacement, *superseded):
                visit.version += 1
                visit.updated_at = utc_timestamp()
                connection.execute(
                    "UPDATE visits SET data = ? WHERE id = ?",
                    (visit.model_dump_json(), visit.id),
                )
            self._append_event(
                connection,
                event_id=body.event_id,
                patient_id=body.replacement_id,
                timestamp=utc_timestamp(),
                action="ghost_slot_filled",
                actor="local demo coordinator",
                payload=payload,
            )
        return False

    def advance_clock(self, minute: int, expected_revision: int) -> None:
        """Move the fictional clock forward and audit the change."""
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            revision = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events"
            ).fetchone()[0]
            if revision != expected_revision:
                raise ConflictError("Clinic state changed. Refresh the clock.")
            current = connection.execute(
                "SELECT minute FROM demo_clock WHERE id = 1"
            ).fetchone()[0]
            if minute <= current or minute > 480:
                raise ConflictError("Demo clock must advance within the day.")
            connection.execute(
                "UPDATE demo_clock SET minute = ? WHERE id = 1", (minute,)
            )
            self._append_event(
                connection,
                event_id=f"demo-clock-{revision + 1}",
                patient_id="CLINIC",
                timestamp=utc_timestamp(),
                action="demo_clock_advanced",
                actor="local demo operator",
                payload={"from_minute": current, "to_minute": minute},
            )

    def onboard_demo_visit(self, body: DemoOnboardRequest) -> bool:
        """Import a fictional patient already past the report-status step."""
        payload = body.model_dump()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT payload FROM events WHERE event_id = ?",
                (body.event_id,),
            ).fetchone()
            if previous:
                if json.loads(previous["payload"]) != payload:
                    raise ConflictError("Event identifier already used.")
                return True
            revision = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events"
            ).fetchone()[0]
            if revision != body.expected_revision:
                raise ConflictError("Clinic state changed. Refresh first.")
            if connection.execute(
                "SELECT 1 FROM visits WHERE id = 'OF-013'"
            ).fetchone():
                raise ConflictError("The synthetic onboarded visit exists.")
            clock = connection.execute(
                "SELECT minute FROM demo_clock WHERE id = 1"
            ).fetchone()[0]
            visit = PatientVisit(
                id="OF-013",
                alias="Demo patient 13",
                priority=0,
                panels={"CBC": "final"},
                scheduled_duration_minutes=60,
                appointment_minute=clock,
                location="waiting_room",
                arrival=f"{8 + clock // 60:02}:{clock % 60:02}",
                updated_at=utc_timestamp(),
            )
            connection.execute(
                "INSERT INTO visits VALUES (?, ?)",
                (visit.id, visit.model_dump_json()),
            )
            self._append_event(
                connection,
                event_id=body.event_id,
                patient_id=visit.id,
                timestamp=visit.updated_at,
                action="demo_visit_onboarded",
                actor="synthetic status snapshot",
                payload=payload,
            )
        return False

    def apply_report_webhook(
        self,
        patient_id: str,
        panel: str,
        status: str,
        source_sequence: int,
        event_id: str,
    ) -> bool:
        """Apply a status-only source event once and reject old ordering."""
        payload = {
            "patient_id": patient_id,
            "panel": panel,
            "status": status,
            "source_sequence": source_sequence,
        }
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT payload FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if previous:
                if json.loads(previous["payload"]) != payload:
                    raise ConflictError("Event identifier already used.")
                return True
            source = connection.execute(
                "SELECT source_sequence FROM report_source_state "
                "WHERE patient_id = ? AND panel = ?",
                (patient_id, panel),
            ).fetchone()
            if source is not None and source_sequence <= source[0]:
                raise ConflictError("Older report status event rejected.")
            row = connection.execute(
                "SELECT data FROM visits WHERE id = ?", (patient_id,)
            ).fetchone()
            if row is None:
                raise VisitNotFoundError("Visit not found.")
            visit = PatientVisit.model_validate_json(row["data"])
            clock = connection.execute(
                "SELECT minute FROM demo_clock WHERE id = 1"
            ).fetchone()[0]
            was_ready = visit.stage == "ready_for_chair"
            visit.apply(
                Command(
                    event_id=event_id,
                    expected_version=visit.version,
                    action="report_status",
                    panel=panel,
                    status=status,
                ),
                set(),
            )
            if visit.stage == "ready_for_chair" and not was_ready:
                visit.ready_since_minute = clock
            elif visit.stage != "ready_for_chair" and not visit.infusing:
                visit.ready_since_minute = None
            visit.version += 1
            visit.updated_at = utc_timestamp()
            connection.execute(
                "UPDATE visits SET data = ? WHERE id = ?",
                (visit.model_dump_json(), patient_id),
            )
            connection.execute(
                "INSERT INTO report_source_state VALUES (?, ?, ?) "
                "ON CONFLICT(patient_id, panel) DO UPDATE SET "
                "source_sequence = excluded.source_sequence",
                (patient_id, panel, source_sequence),
            )
            self._append_event(
                connection,
                event_id=event_id,
                patient_id=patient_id,
                timestamp=visit.updated_at,
                action="report_status_webhook",
                actor="synthetic LIS status feed",
                payload=payload,
            )
        return False

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        *,
        event_id: str,
        patient_id: str,
        timestamp: str,
        action: str,
        actor: str,
        payload: dict,
    ) -> None:
        connection.execute(
            "INSERT INTO events "
            "(event_id, patient_id, timestamp, action, actor, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event_id,
                patient_id,
                timestamp,
                action,
                actor,
                json.dumps(payload),
            ),
        )
