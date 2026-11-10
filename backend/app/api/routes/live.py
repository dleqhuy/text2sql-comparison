"""Local FastAPI endpoints for live runs, history and replay."""

import asyncio
import json
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.api.deps import SessionDep
from app.live_models import (
    Bootstrap,
    CancelResult,
    HistoryChange,
    HistorySelection,
    PipelineRun,
    RunCreate,
    RunPublic,
    RunSnapshot,
    SchemaObject,
)
from app.services import pipeline

router = APIRouter(prefix="/live", tags=["live"])


def find_run(run_id, session):
    record = session.get(PipelineRun, run_id)
    if not record or record.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


@router.get("/bootstrap", response_model=Bootstrap)
def bootstrap():
    env = pipeline.environment()
    rows = json.loads((pipeline.DATA / "dev.json").read_text())
    readiness = {}
    for method, repo in pipeline.REPOS.items():
        installed = (pipeline.ROOT.parent / repo / ".venv/bin/python").exists()
        auth = (
            bool(
                env.get("CODEX_API_KEY")
                or env.get("OPENAI_API_KEY")
                or (
                    pipeline.Path(
                        env.get("CODEX_HOME", str(pipeline.Path.home() / ".codex"))
                    )
                    / "auth.json"
                ).is_file()
            )
            if method == "codex_mcp"
            else bool(env.get("LLM_API_KEY"))
        )
        readiness[method] = {
            "ready": installed and auth,
            "reason": "Ready"
            if installed and auth
            else "Install method .venv"
            if not installed
            else "Configure Codex login/API key"
            if method == "codex_mcp"
            else "Set LLM_API_KEY in .env",
        }
    if readiness["dail_sql"]["ready"]:
        missing = pipeline.dail_missing_resources(env)
        if missing:
            readiness["dail_sql"] = {
                "ready": False,
                "reason": "Missing: " + ", ".join(missing),
            }
    return {
        "examples": [
            {"index": i, "db_id": r["db_id"], "question": r["question"]}
            for i, r in enumerate(rows)
        ],
        "databases": sorted({r["db_id"] for r in rows}),
        "readiness": readiness,
        "endpoint": env.get("LLM_BASE_URL"),
        "model": env["LLM_MODEL"],
        "codex_model": env["CODEX_MODEL"],
    }


@router.get("/schema/{db_id}", response_model=list[SchemaObject])
def read_schema(db_id: str):
    try:
        return pipeline.schema(db_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/runs", response_model=list[RunPublic])
def list_runs(session: SessionDep):
    records = session.exec(
        select(PipelineRun)
        .where(PipelineRun.deleted_at.is_(None))
        .order_by(PipelineRun.started_at.desc())
    ).all()
    return [r.payload for r in records]


@router.delete("/runs", response_model=HistoryChange)
def clear_history(session: SessionDep):
    """Hide finished runs; leave active runners and their traces untouched."""
    changed, skipped = [], []
    with pipeline.LOCK:
        records = session.exec(
            select(PipelineRun).where(PipelineRun.deleted_at.is_(None))
        ).all()
        now = time.time()
        for record in records:
            if record.id in pipeline.ACTIVE or record.status == "running":
                skipped.append(record.id)
                continue
            record.deleted_at = now
            session.add(record)
            changed.append(record.id)
        session.commit()
    return {"changed_ids": changed, "skipped_ids": skipped}


@router.post("/runs/restore", response_model=HistoryChange)
def restore_history(body: HistorySelection, session: SessionDep):
    """Undo a deletion without rerunning methods or modifying trace content."""
    changed, skipped = [], []
    with pipeline.LOCK:
        for run_id in dict.fromkeys(body.run_ids):
            record = session.get(PipelineRun, run_id)
            if record is None or record.deleted_at is None:
                skipped.append(run_id)
                continue
            record.deleted_at = None
            session.add(record)
            changed.append(run_id)
        session.commit()
    return {"changed_ids": changed, "skipped_ids": skipped}


@router.delete("/runs/{run_id}", response_model=HistoryChange)
def delete_run(run_id: str, session: SessionDep):
    with pipeline.LOCK:
        record = find_run(run_id, session)
        if run_id in pipeline.ACTIVE or record.status == "running":
            raise HTTPException(
                status_code=409,
                detail="Không thể xóa phiên đang chạy. Hãy dừng phiên trước.",
            )
        record.deleted_at = time.time()
        session.add(record)
        session.commit()
    return {"changed_ids": [run_id], "skipped_ids": []}


@router.post("/runs", response_model=RunPublic, status_code=201)
def create_run(body: RunCreate):
    request = body.model_dump()
    try:
        pipeline.database(body.db_id)
        if not body.question.strip() or len(set(body.methods)) != len(body.methods):
            raise ValueError("Choose unique methods and a nonempty question")
        if body.example_index is not None:
            rows = json.loads((pipeline.DATA / "dev.json").read_text())
            index = body.example_index
            if (
                not 0 <= index < len(rows)
                or rows[index]["question"] != body.question
                or rows[index]["db_id"] != body.db_id
            ):
                raise ValueError("Example changed; use custom question mode")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    with pipeline.LOCK:
        if pipeline.ACTIVE:
            raise HTTPException(
                status_code=409,
                detail="A run is already active. Wait for it or cancel your active run from History.",
            )
        run_id = uuid.uuid4().hex[:12]
        path = pipeline.RUNS / run_id
        path.mkdir(parents=True)
        env = pipeline.environment()
        meta = dict(
            id=run_id,
            **request,
            started_at=time.time(),
            status="running",
            models={
                m: env["CODEX_MODEL" if m == "codex_mcp" else "LLM_MODEL"]
                for m in body.methods
            },
        )
        pipeline.save_meta(path, meta)
        cancel = threading.Event()
        thread = threading.Thread(
            target=pipeline.execute_run, args=(path, request, cancel), daemon=True
        )
        pipeline.ACTIVE[run_id] = {"cancel": cancel, "process": None, "thread": thread}
        thread.start()
    return pipeline.redact(meta)


@router.get("/runs/{run_id}", response_model=RunSnapshot)
def read_run(run_id: str, session: SessionDep):
    record = find_run(run_id, session)
    return {"meta": record.payload, "events": pipeline.events(pipeline.RUNS / run_id)}


@router.post("/runs/{run_id}/cancel", response_model=CancelResult)
def cancel_run(run_id: str, session: SessionDep):
    find_run(run_id, session)
    with pipeline.LOCK:
        if run_id in pipeline.ACTIVE:
            pipeline.ACTIVE[run_id]["cancel"].set()
    return {"ok": True}


@router.get(
    "/runs/{run_id}/events",
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
def stream_run(run_id: str, request: Request, session: SessionDep):
    find_run(run_id, session)
    path = pipeline.RUNS / run_id

    async def stream():
        previous = ""
        while not await request.is_disconnected():
            # File mirrors are atomic and reflect the same state as the run row.
            meta = json.loads((path / "run.json").read_text())
            payload = json.dumps(
                pipeline.redact(
                    {
                        "meta": RunPublic.model_validate(meta).model_dump(),
                        "events": pipeline.events(path),
                    }
                ),
                ensure_ascii=False,
                default=str,
            )
            if payload != previous:
                yield "data: " + payload + "\n\n"
                previous = payload
            else:
                yield ": keepalive\n\n"
            if meta["status"] != "running":
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
