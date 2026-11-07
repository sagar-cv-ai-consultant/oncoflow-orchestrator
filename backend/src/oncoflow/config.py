"""Runtime settings with defaults independent of the launch directory."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAIR_COUNT = 6
NURSE_START_CAPACITY = 2
NURSE_SETUP_MINUTES = 15
CHAIR_TURNOVER_MINUTES = 10
GHOST_GRACE_MINUTES = 5
AUDIT_EVENT_LIMIT = 60


@dataclass(frozen=True)
class Settings:
    """Configuration for a single local demo instance."""

    database_path: Path
    scenario: str = "manual"
    demo_routes_enabled: bool = False

    @classmethod
    def from_environment(cls) -> "Settings":
        """Resolve relative database paths against the repository root."""
        path = Path(os.environ.get("ONCOFLOW_DB", "data/oncoflow.sqlite3"))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        scenario = os.environ.get("ONCOFLOW_SCENARIO", "manual")
        if scenario not in ("manual", "ghost"):
            raise ValueError("ONCOFLOW_SCENARIO must be manual or ghost.")
        return cls(
            database_path=path,
            scenario=scenario,
            demo_routes_enabled=(os.environ.get("ONCOFLOW_LOCAL_DEMO") == "1"),
        )
