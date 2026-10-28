"""Runtime settings with defaults independent of the launch directory."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAIR_COUNT = 6
AUDIT_EVENT_LIMIT = 60


@dataclass(frozen=True)
class Settings:
    """Configuration for a single local demo instance."""

    database_path: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        """Resolve relative database paths against the repository root."""
        path = Path(os.environ.get("ONCOFLOW_DB", "data/oncoflow.sqlite3"))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return cls(database_path=path)
