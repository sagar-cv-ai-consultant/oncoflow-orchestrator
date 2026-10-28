import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from oncoflow.adapters.fhir import FHIRReportAdapter
from oncoflow.api import create_app


@pytest.fixture
def clinic(tmp_path):
    path = tmp_path / "clinic.sqlite3"
    with TestClient(create_app(path)) as client:
        yield client, path


def patient(client, visit="OF-003"):
    return next(
        p
        for p in client.get("/api/state").json()["patients"]
        if p["id"] == visit
    )


def send(client, action, visit="OF-003", **fields):
    return client.post(
        f"/api/visits/{visit}/commands",
        json={
            "event_id": str(uuid4()),
            "expected_version": patient(client, visit)["version"],
            "action": action,
            **fields,
        },
    )


def test_complete_journey_and_audit_survive_restart(clinic):
    client, path = clinic
    assert send(client, "start_consult").status_code == 422
    assert (
        send(client, "report_status", panel="CBC", status="final").status_code
        == 200
    )
    assert patient(client)["stage"] == "ready_for_consult"
    assert not patient(client)["cleared"]
    for action in (
        "start_consult",
        "finish_consult",
        "clearance",
        "pharmacy_ready",
    ):
        assert send(client, action).status_code == 200
    assert send(client, "start_infusion", chair=1).status_code == 422
    assert send(client, "location", location="nearby").status_code == 200
    assert send(client, "start_infusion", chair=2).status_code == 422
    assert send(client, "location", location="waiting_room").status_code == 200
    assert send(client, "start_infusion", chair=2).status_code == 200
    assert send(client, "no_show").status_code == 422
    assert send(client, "finish_infusion").status_code == 200
    assert patient(client)["stage"] == "discharged"
    assert send(client, "start_consult").status_code == 422
    with TestClient(create_app(path)) as restarted:
        assert patient(restarted)["stage"] == "discharged"
        assert any(
            e["action"] == "finish_infusion"
            for e in restarted.get("/api/state").json()["events"]
        )


def test_multiple_reports_and_finality_do_not_grant_clearance(clinic):
    client, _ = clinic
    assert (
        send(
            client, "report_status", "OF-004", panel="CMP", status="final"
        ).status_code
        == 200
    )
    assert patient(client, "OF-004")["stage"] == "ready_for_consult"
    assert send(client, "clearance", "OF-004").status_code == 422
    assert send(client, "pharmacy_ready", "OF-004").status_code == 422
    assert (
        send(
            client, "report_status", "OF-004", panel="CBC", status="pending"
        ).status_code
        == 200
    )
    assert patient(client, "OF-004")["stage"] == "awaiting_reports"
    assert send(client, "start_consult", "OF-004").status_code == 422


def test_stale_actions_and_duplicate_delivery(clinic):
    client, _ = clinic
    body = {
        "event_id": "same-source-event",
        "expected_version": 0,
        "action": "report_status",
        "panel": "CBC",
        "status": "final",
    }
    assert (
        client.post("/api/visits/OF-003/commands", json=body).status_code
        == 200
    )
    assert client.post("/api/visits/OF-003/commands", json=body).json() == {
        "duplicate": True
    }
    assert patient(client)["version"] == 1
    assert (
        client.post(
            "/api/visits/OF-003/commands",
            json={**body, "event_id": "late-event", "status": "pending"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/visits/OF-003/commands", json={**body, "status": "pending"}
        ).status_code
        == 409
    )
    assert patient(client)["panels"]["CBC"] == "final"


def test_report_correction_invalidates_clearance_without_interrupting_care(
    clinic,
):
    client, _ = clinic
    assert (
        send(
            client, "report_status", "OF-007", panel="CBC", status="corrected"
        ).status_code
        == 200
    )
    assert patient(client, "OF-007")["stage"] == "awaiting_reports"
    assert not patient(client, "OF-007")["cleared"]
    assert not patient(client, "OF-007")["pharmacy_ready"]
    assert send(client, "start_infusion", "OF-007", chair=2).status_code == 422
    assert (
        send(
            client,
            "report_status",
            "OF-001",
            panel="CBC",
            status="entered-in-error",
        ).status_code
        == 200
    )
    p = patient(client, "OF-001")
    assert p["infusing"] and p["chair"] == 1
    assert p["blockers"] and not p["cleared"]


def test_status_adapter_never_stores_or_returns_result_values(clinic):
    client, path = clinic
    secret = "PRIVATE_RESULT_SENTINEL_95812"
    payload = {
        "resourceType": "DiagnosticReport",
        "id": "report-123",
        "status": "final",
        "conclusion": secret,
        "result": [{"valueString": secret}],
        "contained": [{"resourceType": "Observation", "valueString": secret}],
    }
    normalized = FHIRReportAdapter.normalize(payload)
    assert normalized == {"report_id": "report-123", "status": "final"}
    res = client.post(
        "/api/demo/visits/OF-003/reports/CBC",
        params={"expected_version": 0, "event_id": "source-123"},
        json=payload,
    )
    assert res.status_code == 200
    assert secret not in res.text
    assert secret not in client.get("/api/state").text
    with sqlite3.connect(path) as db:
        stored = json.dumps(list(db.iterdump()))
    assert secret not in stored


def test_invalid_commands_do_not_echo_rejected_values_or_change_history(
    clinic,
):
    client, _ = clinic
    before = client.get("/api/state").json()["revision"]
    res = client.post(
        "/api/visits/OF-003/commands",
        json={"action": "clearance", "clinical_value": "PRIVATE_SENTINEL"},
    )
    assert res.status_code == 422
    assert "PRIVATE_SENTINEL" not in res.text
    assert client.get("/api/state").json()["revision"] == before


def test_closed_visits_and_unknown_visits(clinic):
    client, _ = clinic
    assert send(client, "no_show").status_code == 200
    assert (
        send(client, "report_status", panel="CBC", status="final").status_code
        == 422
    )
    res = client.post(
        "/api/visits/missing/commands",
        json={
            "event_id": str(uuid4()),
            "expected_version": 0,
            "action": "start_consult",
        },
    )
    assert res.status_code == 404


def test_demonstration_does_not_claim_ai_or_scheduler(clinic):
    client, _ = clinic
    assert client.get("/api/health").json() == {
        "status": "ok",
        "mode": "synthetic_demo",
        "ai_enabled": False,
        "scheduler_enabled": False,
    }
