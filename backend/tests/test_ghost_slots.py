"""Ghost-slot recommendations and atomic staff confirmation."""

import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from oncoflow import scheduler as scheduler_module
from oncoflow.api import create_app
from oncoflow.evaluation import evaluate_ghost_day, evaluate_varied_days
from oncoflow.fixtures import ghost_day_visits
from oncoflow.scheduler import ChairScheduler, ScheduleSettings


def save_visit(path, visit):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE visits SET data = ? WHERE id = ?",
            (visit.model_dump_json(), visit.id),
        )


def test_demo_routes_disabled_for_direct_api_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("ONCOFLOW_DB", str(tmp_path / "direct.sqlite3"))
    monkeypatch.setenv("ONCOFLOW_SCENARIO", "ghost")
    monkeypatch.delenv("ONCOFLOW_LOCAL_DEMO", raising=False)
    with TestClient(create_app()) as client:
        state = client.get("/api/state").json()
        assert state["scenario"] == "ghost"
        assert (
            client.post(
                "/api/demo/clock",
                json={"minute": 165, "expected_revision": state["revision"]},
            ).status_code
            == 404
        )


def test_ghost_day_explains_two_feasible_replacements(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        state = client.get("/api/state").json()
        assert state["demo_minute"] == 150
        slots = state["ghost_slots"]
        assert [slot["chair"] for slot in slots] == [2, 3]
        assert [slot["replacement"]["patient_id"] for slot in slots] == [
            "OF-007",
            "OF-011",
        ]
        assert any(
            item["patient_id"] == "OF-009" and "CBC" in item["reason"]
            for item in slots[0]["excluded"]
        )


def test_confirmation_moves_only_selected_visits_and_is_idempotent(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        before = client.get("/api/state").json()
        slot = before["ghost_slots"][0]
        request = {
            "event_id": "approve-ghost-1",
            "expected_revision": before["revision"],
            "booked_patient_id": slot["booked_patient_id"],
            "replacement_id": slot["replacement"]["patient_id"],
            "chair": slot["chair"],
        }
        first = client.post("/api/ghost-slots/approve", json=request)
        assert first.json() == {"duplicate": False}
        repeated = client.post("/api/ghost-slots/approve", json=request)
        assert repeated.json() == {"duplicate": True}
        after = client.get("/api/state").json()
        by_id = {visit["id"]: visit for visit in after["patients"]}
        assert by_id["OF-007"]["infusing"]
        assert by_id["OF-007"]["chair"] == 2
        assert by_id["OF-003"]["booking_status"] == "displaced"
        assert by_id["OF-001"]["chair"] == 1
        assert after["ghost_slots"][0]["booked_patient_id"] == "OF-004"
        assert any(
            event["action"] == "ghost_slot_filled" for event in after["events"]
        )


def test_stale_confirmation_cannot_bypass_report_change(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        state = client.get("/api/state").json()
        slot = state["ghost_slots"][0]
        patient = next(
            visit
            for visit in state["patients"]
            if visit["id"] == slot["replacement"]["patient_id"]
        )
        assert (
            client.post(
                f"/api/visits/{patient['id']}/commands",
                json={
                    "event_id": "corrected-before-approval",
                    "expected_version": patient["version"],
                    "action": "report_status",
                    "panel": "CBC",
                    "status": "corrected",
                },
            ).status_code
            == 200
        )
        response = client.post(
            "/api/ghost-slots/approve",
            json={
                "event_id": "stale-approval",
                "expected_revision": state["revision"],
                "booked_patient_id": slot["booked_patient_id"],
                "replacement_id": patient["id"],
                "chair": slot["chair"],
            },
        )
        assert response.status_code == 409
        current = client.get("/api/state").json()
        changed = next(
            visit
            for visit in current["patients"]
            if visit["id"] == patient["id"]
        )
        assert not changed["infusing"]


def test_equal_priority_uses_appointment_then_ready_time():
    visits = ghost_day_visits()
    by_id = {visit.id: visit for visit in visits}
    by_id["OF-007"].priority = 0
    by_id["OF-011"].priority = 0
    by_id["OF-011"].appointment_minute = 80
    slots = ChairScheduler().ghost_slots(visits, 150)
    assert slots[0]["replacement"]["patient_id"] == "OF-011"
    by_id["OF-007"].appointment_minute = 80
    by_id["OF-007"].ready_since_minute = 70
    slots = ChairScheduler().ghost_slots(visits, 150)
    assert slots[0]["replacement"]["patient_id"] == "OF-007"


def test_ready_later_booking_keeps_own_chair_and_can_start(tmp_path):
    path = tmp_path / "ghost.sqlite3"
    with TestClient(create_app(path, scenario="ghost")) as client:
        own = next(
            visit for visit in ghost_day_visits() if visit.id == "OF-008"
        )
        own.panels = {"CBC": "final"}
        own.consult_done = True
        own.cleared = True
        own.pharmacy_ready = True
        own.location = "waiting_room"
        own.booked_chair = 2
        own.booked_start_minute = 148
        own.booking_status = "active"
        save_visit(path, own)

        before = client.get("/api/state").json()
        assert all(slot["chair"] != 2 for slot in before["ghost_slots"])
        response = client.post(
            "/api/visits/OF-008/commands",
            json={
                "event_id": "start-own-booking",
                "expected_version": 0,
                "action": "start_infusion",
                "chair": 2,
            },
        )
        assert response.status_code == 200
        patients = {
            visit["id"]: visit
            for visit in client.get("/api/state").json()["patients"]
        }
        assert patients["OF-008"]["infusing"]
        assert patients["OF-003"]["booking_status"] == "displaced"


def test_higher_priority_wins_when_only_one_nurse_can_start():
    visits = ghost_day_visits()
    by_id = {visit.id: visit for visit in visits}
    by_id["OF-007"].priority = 2
    by_id["OF-007"].scheduled_duration_minutes = 120
    by_id["OF-011"].priority = 0
    by_id["OF-011"].scheduled_duration_minutes = 30
    by_id["OF-012"].booked_start_minute = 200
    scheduler = ChairScheduler(ScheduleSettings(nurses_for_starts=1))
    slots = scheduler.ghost_slots(visits, 150)
    assert [
        slot["replacement"]["patient_id"]
        for slot in slots
        if slot["replacement"]
    ] == ["OF-007"]


def test_two_missed_bookings_on_one_chair_show_one_card(tmp_path):
    path = tmp_path / "ghost.sqlite3"
    with TestClient(create_app(path, scenario="ghost")) as client:
        second = next(
            visit for visit in ghost_day_visits() if visit.id == "OF-009"
        )
        second.booked_chair = 2
        second.booked_start_minute = 145
        second.booking_status = "active"
        save_visit(path, second)
        before = client.get("/api/state").json()
        chair_two = [
            slot for slot in before["ghost_slots"] if slot["chair"] == 2
        ]
        assert len(chair_two) == 1
        assert chair_two[0]["booked_patient_id"] == "OF-009"
        assert (
            client.post(
                "/api/ghost-slots/approve",
                json={
                    "event_id": "replace-latest-missed",
                    "expected_revision": before["revision"],
                    "booked_patient_id": "OF-009",
                    "replacement_id": (
                        chair_two[0]["replacement"]["patient_id"]
                    ),
                    "chair": 2,
                },
            ).status_code
            == 200
        )
        patients = {
            visit["id"]: visit
            for visit in client.get("/api/state").json()["patients"]
        }
        assert patients["OF-003"]["booking_status"] == "displaced"
        assert patients["OF-009"]["booking_status"] == "displaced"


def test_cp_sat_fills_two_gaps_that_greedy_priority_cannot(monkeypatch):
    visits = ghost_day_visits()
    by_id = {visit.id: visit for visit in visits}
    by_id["OF-007"].scheduled_duration_minutes = 120
    by_id["OF-007"].priority = 0
    by_id["OF-011"].priority = 1
    by_id["OF-006"].booked_start_minute = 270
    optimized = ChairScheduler().ghost_slots(visits, 150)
    assert optimized[0]["solver"] == "cp_sat"
    assert [slot["replacement"]["patient_id"] for slot in optimized] == [
        "OF-007",
        "OF-011",
    ]
    monkeypatch.setattr(scheduler_module, "cp_model", None)
    fallback = ChairScheduler().ghost_slots(visits, 150)
    assert fallback[0]["solver"] == "heuristic_fallback"
    assert [slot["replacement"]["patient_id"] for slot in fallback] == [
        "OF-007",
        "OF-011",
    ]


def test_long_session_does_not_displace_protected_booking():
    visits = ghost_day_visits()
    by_id = {visit.id: visit for visit in visits}
    by_id["OF-007"].scheduled_duration_minutes = 180
    by_id["OF-011"].scheduled_duration_minutes = 180
    slots = ChairScheduler().ghost_slots(visits, 150)
    assert all(slot["replacement"] is None for slot in slots)
    assert any("do not fit" in item["reason"] for item in slots[0]["excluded"])


def test_manual_start_cannot_take_a_protected_ghost_chair(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        response = client.post(
            "/api/visits/OF-007/commands",
            json={
                "event_id": "bypass-attempt",
                "expected_version": 0,
                "action": "start_infusion",
                "chair": 2,
            },
        )
        assert response.status_code == 409
        state = client.get("/api/state").json()
        assert not next(p for p in state["patients"] if p["id"] == "OF-007")[
            "infusing"
        ]


def test_synthetic_case_reports_recovery_and_displacement_cost():
    totals = evaluate_ghost_day()["totals"]
    assert totals == {
        "baseline_idle_minutes": 140,
        "recovered_chair_minutes": 120,
        "possible_same_chair_delay_minutes": 10,
    }


def test_varied_days_are_reproducible_and_respect_future_bookings():
    first = evaluate_varied_days(10)
    second = evaluate_varied_days(10)
    assert first["scenario_count"] == second["scenario_count"] == 10
    for field in (
        "mean_fills_per_day",
        "median_recovered_chair_minutes",
        "p90_recovered_chair_minutes",
        "median_possible_same_chair_delay_minutes",
    ):
        assert first["summary"][field] == second["summary"][field]


def test_patient_onboards_at_existing_report_stage(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        before = client.get("/api/state").json()
        request = {
            "event_id": "onboard-existing-lab",
            "expected_revision": before["revision"],
        }
        assert client.post("/api/demo/onboard", json=request).json() == {
            "duplicate": False
        }
        assert client.post("/api/demo/onboard", json=request).json() == {
            "duplicate": True
        }
        after = client.get("/api/state").json()
        new_visit = next(
            visit for visit in after["patients"] if visit["id"] == "OF-013"
        )
        assert new_visit["panels"] == {"CBC": "final"}
        assert new_visit["stage"] == "ready_for_consult"
        assert not new_visit["cleared"]


def test_clock_change_invalidates_old_proposal(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        before = client.get("/api/state").json()
        slot = before["ghost_slots"][0]
        assert (
            client.post(
                "/api/demo/clock",
                json={"minute": 165, "expected_revision": before["revision"]},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/ghost-slots/approve",
                json={
                    "event_id": "old-clock-proposal",
                    "expected_revision": before["revision"],
                    "booked_patient_id": slot["booked_patient_id"],
                    "replacement_id": slot["replacement"]["patient_id"],
                    "chair": slot["chair"],
                },
            ).status_code
            == 409
        )


def test_webhook_replans_and_discards_report_values(tmp_path):
    path = tmp_path / "ghost.sqlite3"
    with TestClient(create_app(path, scenario="ghost")) as client:
        assert len(client.get("/api/state").json()["ghost_slots"]) == 2
        secret = "PRIVATE_LAB_VALUE_SENTINEL"
        event = {
            "event_id": "lis-status-1",
            "patient_id": "OF-007",
            "panel": "CBC",
            "source_sequence": 1,
            "report": {
                "resourceType": "DiagnosticReport",
                "id": "report-7",
                "status": "corrected",
                "conclusion": secret,
                "result": [{"valueString": secret}],
            },
        }
        first = client.post("/api/demo/webhook/report", json=event)
        assert first.status_code == 200
        assert first.json() == {"duplicate": False}
        assert client.post("/api/demo/webhook/report", json=event).json() == {
            "duplicate": True
        }
        after = client.get("/api/state").json()
        assert [
            slot["replacement"]["patient_id"]
            for slot in after["ghost_slots"]
            if slot["replacement"]
        ] == ["OF-011"]
        assert secret not in json.dumps(after)
        with sqlite3.connect(path) as connection:
            assert secret not in json.dumps(list(connection.iterdump()))

        old = {
            **event,
            "event_id": "lis-status-old",
            "report": {
                "resourceType": "DiagnosticReport",
                "id": "report-7",
                "status": "final",
            },
        }
        assert (
            client.post("/api/demo/webhook/report", json=old).status_code
            == 409
        )


def test_displaced_patient_gets_new_feasible_chair_after_return(tmp_path):
    with TestClient(
        create_app(tmp_path / "ghost.sqlite3", scenario="ghost")
    ) as client:
        state = client.get("/api/state").json()
        slot = state["ghost_slots"][0]
        approved = client.post(
            "/api/ghost-slots/approve",
            json={
                "event_id": "initial-backfill",
                "expected_revision": state["revision"],
                "booked_patient_id": slot["booked_patient_id"],
                "replacement_id": slot["replacement"]["patient_id"],
                "chair": slot["chair"],
            },
        )
        assert approved.status_code == 200
        state = client.get("/api/state").json()
        assert (
            client.post(
                "/api/demo/clock",
                json={"minute": 210, "expected_revision": state["revision"]},
            ).status_code
            == 200
        )

        def send(patient_id, action, **fields):
            snapshot = client.get("/api/state").json()
            patient = next(
                item
                for item in snapshot["patients"]
                if item["id"] == patient_id
            )
            return client.post(
                f"/api/visits/{patient_id}/commands",
                json={
                    "event_id": str(uuid4()),
                    "expected_version": patient["version"],
                    "action": action,
                    **fields,
                },
            )

        assert send("OF-007", "finish_infusion").status_code == 200
        assert (
            send(
                "OF-003", "report_status", panel="CBC", status="final"
            ).status_code
            == 200
        )
        for action in (
            "start_consult",
            "finish_consult",
            "clearance",
            "pharmacy_ready",
        ):
            assert send("OF-003", action).status_code == 200
        state = client.get("/api/state").json()
        suggestion = next(
            item
            for item in state["schedule"]["recommendations"]
            if item["patient_id"] == "OF-003"
        )
        assert suggestion["chair"] == 2
        assert suggestion["start_in_minutes"] == 0
        assert send("OF-003", "start_infusion", chair=2).status_code == 200
        state = client.get("/api/state").json()
        original = next(
            item for item in state["patients"] if item["id"] == "OF-003"
        )
        assert original["infusing"]
        assert original["booking_status"] == "active"
