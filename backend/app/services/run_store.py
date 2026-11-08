"""Shared local PostgreSQL history; detailed traces remain in artifact files."""

import json

from sqlmodel import Session

from app.core.db import engine
from app.live_models import PipelineRun
from app.services import pipeline


def public_meta(meta):
    return pipeline.redact(
        {key: value for key, value in meta.items() if key != "owner_id"}
    )


def save_meta(meta):
    meta = public_meta(meta)
    with Session(engine) as session:
        record = session.get(PipelineRun, meta["id"])
        if record is None:
            record = PipelineRun(
                id=meta["id"],
                started_at=meta["started_at"],
                status=meta["status"],
                payload=meta,
            )
        else:
            record.status = meta["status"]
            record.payload = meta
        session.add(record)
        session.commit()


def reconcile_legacy():
    """Preserve all existing runs when moving to the account-free dashboard."""
    pipeline.RUNS.mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        for path in pipeline.RUNS.glob("*/run.json"):
            artifact = json.loads(path.read_text())
            record = session.get(PipelineRun, artifact["id"])
            if record is not None and record.deleted_at is not None:
                # Trace files remain recoverable; do not import them back into history.
                continue
            meta = public_meta(record.payload if record else artifact)
            if meta["status"] == "running":
                meta["status"] = "interrupted"
            if record is None:
                record = PipelineRun(
                    id=meta["id"],
                    started_at=meta["started_at"],
                    status=meta["status"],
                    payload=meta,
                )
            else:
                record.status = meta["status"]
                record.payload = meta
            session.add(record)
            pipeline.save(path, meta)
        session.commit()
