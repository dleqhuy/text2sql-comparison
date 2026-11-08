"""Typed API and SQLModel persistence for the pipeline explorer."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic import Field as InputField
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

Method = Literal["din_sql", "mac_sql", "codex_mcp"]


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = InputField(min_length=1, max_length=2000)
    db_id: str = InputField(pattern=r"^[A-Za-z0-9_-]+$", max_length=100)
    methods: list[Method] = InputField(min_length=1, max_length=3)
    example_index: int | None = InputField(default=None, ge=0, strict=True)


class RunPublic(RunCreate):
    model_config = ConfigDict(extra="ignore")
    id: str
    status: str
    started_at: float
    finished_at: float | None = None
    error: str | None = None
    models: dict[str, str] = InputField(default_factory=dict)


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_run"
    id: str = Field(primary_key=True, max_length=12)
    started_at: float = Field(index=True)
    status: str = Field(index=True, max_length=32)
    deleted_at: float | None = Field(default=None, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class TraceEvent(BaseModel):
    time: float
    method: Method
    kind: str
    stage: str
    input: Any = None
    output: Any = None
    elapsed: float | None = None


class RunSnapshot(BaseModel):
    meta: RunPublic
    events: list[TraceEvent]


class Example(BaseModel):
    index: int
    question: str
    db_id: str


class Readiness(BaseModel):
    ready: bool
    reason: str


class Bootstrap(BaseModel):
    examples: list[Example]
    databases: list[str]
    readiness: dict[Method, Readiness]
    endpoint: str | None
    model: str
    codex_model: str


class SchemaObject(BaseModel):
    name: str
    ddl: str | None


class CancelResult(BaseModel):
    ok: bool


class HistorySelection(BaseModel):
    run_ids: list[str] = InputField(min_length=1)


class HistoryChange(BaseModel):
    changed_ids: list[str]
    skipped_ids: list[str] = InputField(default_factory=list)
