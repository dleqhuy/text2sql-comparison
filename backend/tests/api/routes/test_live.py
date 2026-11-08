"""Account-free dashboard APIs, shared history and PostgreSQL persistence."""

import json
import threading
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.live_models import PipelineRun
from app.services import pipeline, run_store

PREFIX = settings.API_V1_STR + "/live"
BODY = {
    "question": "How many singers do we have?",
    "db_id": "concert_singer",
    "methods": ["din_sql"],
    "example_index": 0,
}


@pytest.fixture(autouse=True)
def data_fixture(monkeypatch, tmp_path: Path):
    # API validation tests do not depend on a downloaded 1.7 GB Spider archive.
    database = tmp_path / "database/concert_singer/concert_singer.sqlite"
    database.parent.mkdir(parents=True)
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE singer (name TEXT)")
    (tmp_path / "dev.json").write_text(
        json.dumps(
            [
                {
                    "question": BODY["question"],
                    "db_id": BODY["db_id"],
                    "query": "SELECT COUNT(*) FROM singer",
                }
            ]
        )
    )
    monkeypatch.setattr(pipeline, "DATA", tmp_path)


def fake_completed(path, request, _cancel):
    assert "ground_truth" not in request
    assert "query" not in request
    directory = path / request["methods"][0]
    directory.mkdir()
    pipeline.append(
        path,
        request["methods"][0],
        "result",
        "Final SQL",
        output="SELECT COUNT(*) FROM singer",
    )
    meta = json.loads((path / "run.json").read_text())
    meta.update(status="completed", finished_at=time.time())
    try:
        pipeline.save_meta(path, meta)
    finally:
        with pipeline.LOCK:
            pipeline.ACTIVE.pop(path.name, None)


def wait_finished(client, run_id):
    for _ in range(100):
        response = client.get(f"{PREFIX}/runs/{run_id}")
        if response.json()["meta"]["status"] != "running":
            return response.json()
        time.sleep(0.01)
    raise AssertionError("Mock run did not finish")


def test_dashboard_api_is_available_without_accounts(client: TestClient):
    assert client.get(f"{PREFIX}/bootstrap").status_code == 200
    assert client.get(f"{PREFIX}/runs").status_code == 200
    spec = client.get("/api/v1/openapi.json").json()
    assert "securitySchemes" not in spec.get("components", {})
    assert all(
        not route.get("security")
        for path in spec["paths"].values()
        for route in path.values()
    )
    for path in (
        "/api/v1/users/",
        "/api/v1/login/access-token",
        "/api/v1/items/",
        "/api/v1/private/users/",
    ):
        assert client.get(path).status_code == 404
        assert client.post(path, json={}).status_code == 404


def test_local_origin_guard(client: TestClient):
    assert (
        client.get(
            f"{PREFIX}/runs", headers={"Origin": "https://external.invalid"}
        ).status_code
        == 403
    )
    assert (
        client.get(f"{PREFIX}/runs", headers={"Host": "external.invalid"}).status_code
        == 400
    )


def test_run_persists_in_postgres_and_replays(client, db: Session, monkeypatch):
    monkeypatch.setattr(pipeline, "execute_run", fake_completed)
    response = client.post(f"{PREFIX}/runs", json=BODY)
    assert response.status_code == 201
    run_id = response.json()["id"]
    snapshot = wait_finished(client, run_id)
    with Session(db.bind) as fresh:
        stored = fresh.get(PipelineRun, run_id)
        assert stored.status == "completed"
        assert stored.payload["question"] == BODY["question"]
        assert "owner_id" not in stored.payload
    assert snapshot["events"][0]["stage"] == "Final SQL"
    stream = client.get(f"{PREFIX}/runs/{run_id}/events")
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert (
        json.loads(stream.text.removeprefix("data: "))["meta"]["status"] == "completed"
    )
    assert any(r["id"] == run_id for r in client.get(f"{PREFIX}/runs").json())


def test_missing_run_returns_404(client):
    for suffix in ("", "/events"):
        assert client.get(f"{PREFIX}/runs/000000000000{suffix}").status_code == 404
    assert client.post(f"{PREFIX}/runs/000000000000/cancel").status_code == 404


@pytest.mark.parametrize(
    "patch,status",
    [
        ({"db_id": "../escape"}, 422),
        ({"question": "Changed question"}, 400),
        ({"methods": ["din_sql", "din_sql"]}, 400),
        ({"methods": ["unsupported"]}, 422),
        ({"example_index": True}, 422),
        ({"question": "   "}, 400),
    ],
)
def test_validation_before_runner_starts(client, patch, status):
    assert client.post(f"{PREFIX}/runs", json={**BODY, **patch}).status_code == status


def test_active_run_guard_and_cancel(client, monkeypatch):
    def waiting(path, _request, cancel):
        cancel.wait(5)
        meta = json.loads((path / "run.json").read_text())
        meta.update(status="cancelled", finished_at=time.time())
        try:
            pipeline.save_meta(path, meta)
        finally:
            with pipeline.LOCK:
                pipeline.ACTIVE.pop(path.name, None)

    monkeypatch.setattr(pipeline, "execute_run", waiting)
    run = client.post(f"{PREFIX}/runs", json=BODY)
    assert run.status_code == 201
    run_id = run.json()["id"]
    try:
        assert client.post(f"{PREFIX}/runs", json=BODY).status_code == 409
    finally:
        assert client.post(f"{PREFIX}/runs/{run_id}/cancel").status_code == 200
    assert wait_finished(client, run_id)["meta"]["status"] == "cancelled"


def seed_history(status="completed"):
    """Local fixtures have no model calls and only use the isolated test DB."""
    run_id = uuid.uuid4().hex[:12]
    path = pipeline.RUNS / run_id
    (path / "din_sql").mkdir(parents=True)
    meta = dict(id=run_id, **BODY, started_at=time.time(), status=status)
    pipeline.save(path / "run.json", meta)
    pipeline.append(path, "din_sql", "result", "Final SQL", output="SELECT 1")
    run_store.save_meta(meta)
    return run_id, path, meta


def test_delete_and_undo_preserve_exact_trace(client, db):
    run_id, path, _ = seed_history()
    original = client.get(f"{PREFIX}/runs/{run_id}").json()
    response = client.delete(f"{PREFIX}/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["changed_ids"] == [run_id]
    assert run_id not in [r["id"] for r in client.get(f"{PREFIX}/runs").json()]
    for suffix in ("", "/events"):
        assert client.get(f"{PREFIX}/runs/{run_id}{suffix}").status_code == 404
    assert client.delete(f"{PREFIX}/runs/{run_id}").status_code == 404
    assert (path / "din_sql/events.jsonl").exists()
    with Session(db.bind) as session:
        assert session.get(PipelineRun, run_id).deleted_at is not None
    restored = client.post(f"{PREFIX}/runs/restore", json={"run_ids": [run_id, run_id]})
    assert restored.json()["changed_ids"] == [run_id]
    assert client.get(f"{PREFIX}/runs/{run_id}").json() == original


@pytest.mark.parametrize("status,active", [("running", False), ("completed", True)])
def test_deletion_never_interrupts_active_runs(client, status, active):
    run_id, _, _ = seed_history(status)
    if active:
        pipeline.ACTIVE[run_id] = {"cancel": threading.Event(), "process": None}
    try:
        assert client.delete(f"{PREFIX}/runs/{run_id}").status_code == 409
        assert client.get(f"{PREFIX}/runs/{run_id}").status_code == 200
        response = client.delete(f"{PREFIX}/runs")
        assert run_id in response.json()["skipped_ids"]
        assert run_id not in response.json()["changed_ids"]
        if active:
            assert not pipeline.ACTIVE[run_id]["cancel"].is_set()
    finally:
        pipeline.ACTIVE.pop(run_id, None)


def test_clear_history_and_restore_multiple(client):
    first, _, _ = seed_history("completed")
    second, _, _ = seed_history("failed")
    response = client.delete(f"{PREFIX}/runs")
    deleted = response.json()["changed_ids"]
    assert {first, second}.issubset(deleted)
    assert not {first, second}.intersection(
        r["id"] for r in client.get(f"{PREFIX}/runs").json()
    )
    restored = client.post(f"{PREFIX}/runs/restore", json={"run_ids": deleted})
    assert set(restored.json()["changed_ids"]) == set(deleted)
    # Repeated restore is harmless and does not duplicate history.
    assert (
        client.post(f"{PREFIX}/runs/restore", json={"run_ids": deleted}).json()[
            "changed_ids"
        ]
        == []
    )


def test_restart_does_not_reimport_deleted_artifacts(client):
    run_id, _, meta = seed_history()
    assert client.delete(f"{PREFIX}/runs/{run_id}").status_code == 200
    run_store.save_meta(meta)
    run_store.reconcile_legacy()
    assert client.get(f"{PREFIX}/runs/{run_id}").status_code == 404
    assert run_id not in [r["id"] for r in client.get(f"{PREFIX}/runs").json()]
    assert client.post(f"{PREFIX}/runs/restore", json={"run_ids": [run_id]}).json()[
        "changed_ids"
    ] == [run_id]


def test_missing_delete_and_empty_restore(client):
    assert client.delete(f"{PREFIX}/runs/000000000000").status_code == 404
    assert (
        client.post(f"{PREFIX}/runs/restore", json={"run_ids": []}).status_code == 422
    )
