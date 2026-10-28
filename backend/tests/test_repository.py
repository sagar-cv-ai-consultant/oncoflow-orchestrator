"""Regression checks for persistence boundaries and the refactored layout."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from oncoflow.api import create_app
from oncoflow.fixtures import demo_visits


def test_app_factory_does_not_create_database_before_startup(tmp_path):
    path = tmp_path / "not-created" / "clinic.sqlite3"
    app = create_app(path)
    assert not path.exists()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert path.exists()


def test_seed_preserves_original_manual_demo_contract(tmp_path):
    with TestClient(create_app(tmp_path / "clinic.sqlite3")) as client:
        state = client.get("/api/state").json()
    visits = {visit["id"]: visit for visit in state["patients"]}
    assert len(visits) == 12
    assert state["chair_count"] == 6
    assert state["revision"] == 12
    assert visits["OF-001"]["stage"] == "infusing"
    assert visits["OF-003"]["stage"] == "awaiting_reports"
    assert visits["OF-007"]["stage"] == "ready_for_chair"
    assert sum(v["location"] == "waiting_room" for v in visits.values()) == 8


def test_existing_database_json_is_loaded_without_reseeding(tmp_path):
    path = tmp_path / "existing.sqlite3"
    # Old milestone rows used JSON dictionaries with the same fields.
    old_visit = demo_visits()[2].model_dump()
    old_visit.update(version=7, location="nearby")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE visits (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO visits VALUES (?, ?)",
            (old_visit["id"], json.dumps(old_visit)),
        )
    with TestClient(create_app(path)) as client:
        state = client.get("/api/state").json()
    assert len(state["patients"]) == 1
    assert state["patients"][0]["version"] == 7
    assert state["patients"][0]["location"] == "nearby"


def test_simultaneous_assignments_cannot_double_book(tmp_path):
    with TestClient(create_app(tmp_path / "clinic.sqlite3")) as client:
        response = client.post(
            "/api/visits/OF-011/commands",
            json={
                "event_id": str(uuid4()),
                "expected_version": 0,
                "action": "pharmacy_ready",
            },
        )
        assert response.status_code == 200

        def occupy(patient_id):
            version = 1 if patient_id == "OF-011" else 0
            return client.post(
                f"/api/visits/{patient_id}/commands",
                json={
                    "event_id": str(uuid4()),
                    "expected_version": version,
                    "action": "start_infusion",
                    "chair": 2,
                },
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(occupy, ["OF-007", "OF-011"]))
        assert sorted(statuses) == [200, 422]
        patients = client.get("/api/state").json()["patients"]
        assert sum(p["infusing"] and p["chair"] == 2 for p in patients) == 1


def test_malformed_report_status_is_rejected_without_echo(tmp_path):
    with TestClient(create_app(tmp_path / "clinic.sqlite3")) as client:
        response = client.post(
            "/api/demo/visits/OF-003/reports/CBC",
            params={"event_id": "malformed", "expected_version": 0},
            json={
                "resourceType": "DiagnosticReport",
                "id": "report-1",
                "status": {"private": "PRIVATE_SENTINEL"},
            },
        )
        assert response.status_code == 422
        assert "PRIVATE_SENTINEL" not in response.text
