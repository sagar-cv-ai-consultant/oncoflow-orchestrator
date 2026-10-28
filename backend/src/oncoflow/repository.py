"""SQLite persistence with atomic workflow changes and audit records."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import AUDIT_EVENT_LIMIT
from .domain import PatientVisit
from .exceptions import ConflictError, VisitNotFoundError
from .fixtures import demo_visits, utc_timestamp
from .schemas import Command


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

    def initialize(self) -> None:
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
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT count(*) FROM visits"
            ).fetchone()[0]
            if count:
                return
            for index, visit in enumerate(demo_visits(), start=1):
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

    def read_snapshot(self) -> tuple[list[PatientVisit], list[dict], int]:
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
        for event in events:
            event["payload"] = json.loads(event["payload"])
        return visits, events, revision

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
            occupied = set()
            for current in connection.execute("SELECT data FROM visits"):
                other = PatientVisit.model_validate_json(current["data"])
                if other.infusing and other.chair is not None:
                    occupied.add(other.chair)
            visit.apply(command, occupied)
            visit.version += 1
            visit.updated_at = utc_timestamp()
            connection.execute(
                "UPDATE visits SET data = ? WHERE id = ?",
                (visit.model_dump_json(), patient_id),
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
