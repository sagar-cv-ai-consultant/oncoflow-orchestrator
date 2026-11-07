"""Scheduling behavior at the domain and HTTP boundaries."""

import sqlite3

from fastapi.testclient import TestClient

from oncoflow.api import create_app
from oncoflow.fixtures import demo_visits
from oncoflow.scheduler import ChairScheduler, ScheduleSettings


def test_only_recorded_ready_patients_are_recommended():
    visits = demo_visits()
    plan = ChairScheduler().recommend(visits)
    assert [item["patient_id"] for item in plan["recommendations"]] == [
        "OF-007"
    ]
    assert plan["recommendations"][0]["chair"] == 2
    assert plan["pinned"] == [{"patient_id": "OF-001", "chair": 1}]

    candidate = next(visit for visit in visits if visit.id == "OF-007")
    candidate.panels["CBC"] = "corrected"
    assert ChairScheduler().recommend(visits)["recommendations"] == []


def test_nurse_limit_and_occupied_chair_are_respected():
    visits = demo_visits()
    ready = next(visit for visit in visits if visit.id == "OF-007")
    second = ready.model_copy(deep=True)
    third = ready.model_copy(deep=True)
    second.id = "EXTRA-2"
    third.id = "EXTRA-3"
    settings = ScheduleSettings(chairs=4, nurses_for_starts=1)
    plan = ChairScheduler(settings).recommend(
        [visits[0], ready, second, third]
    )
    entries = plan["recommendations"]
    assert [item["start_in_minutes"] for item in entries] == [0, 15, 30]
    assert all(item["chair"] != 1 for item in entries)
    assignments = {
        (item["chair"], item["start_in_minutes"]) for item in entries
    }
    assert len(assignments) == 3


def test_plan_recalculates_after_confirmed_start_and_report_change(tmp_path):
    with TestClient(create_app(tmp_path / "scheduler.sqlite3")) as client:
        before = client.get("/api/state").json()
        suggestion = before["schedule"]["recommendations"][0]
        assert suggestion["patient_id"] == "OF-007"
        assert client.get("/api/health").json()["scheduler_enabled"]
        visit = next(
            item for item in before["patients"] if item["id"] == "OF-007"
        )
        response = client.post(
            "/api/visits/OF-007/commands",
            json={
                "event_id": "scheduler-confirm-1",
                "expected_version": visit["version"],
                "action": "start_infusion",
                "chair": suggestion["chair"],
            },
        )
        assert response.status_code == 200
        after = client.get("/api/state").json()
        assert {item["chair"] for item in after["schedule"]["pinned"]} == {
            1,
            2,
        }
        assert after["schedule"]["recommendations"] == []
        assert after["revision"] > before["revision"]


def test_nearby_patient_requires_return_before_recommendation():
    visits = demo_visits()
    ready = next(visit for visit in visits if visit.id == "OF-007")
    ready.location = "nearby"
    assert ChairScheduler().recommend(visits)["recommendations"] == []


def test_follow_up_uses_same_five_step_rank_as_ghost_scheduler():
    visits = demo_visits()
    by_id = {visit.id: visit for visit in visits}
    by_id["OF-007"].appointment_minute = 120
    by_id["OF-011"].priority = by_id["OF-007"].priority
    by_id["OF-011"].pharmacy_ready = True
    by_id["OF-011"].appointment_minute = 90
    assert (
        ChairScheduler().recommend(visits)["recommendations"][0]["patient_id"]
        == "OF-011"
    )


def test_direct_start_respects_active_nurse_setup(tmp_path):
    path = tmp_path / "ghost.sqlite3"
    with TestClient(create_app(path, scenario="ghost")) as client:
        with sqlite3.connect(path) as connection:
            for patient_id in ("OF-001", "OF-002"):
                row = connection.execute(
                    "SELECT data FROM visits WHERE id = ?", (patient_id,)
                ).fetchone()[0]
                from oncoflow.domain import PatientVisit

                visit = PatientVisit.model_validate_json(row)
                visit.infusion_started_minute = 145
                connection.execute(
                    "UPDATE visits SET data = ? WHERE id = ?",
                    (visit.model_dump_json(), patient_id),
                )
        response = client.post(
            "/api/visits/OF-007/commands",
            json={
                "event_id": "nurse-capacity-bypass",
                "expected_version": 0,
                "action": "start_infusion",
                "chair": 2,
            },
        )
        assert response.status_code == 409
        assert "Nurse start capacity" in response.json()["detail"]
