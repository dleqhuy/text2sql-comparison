"""Typed API and SQLModel persistence for the pipeline explorer."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic import Field as InputField
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

Method = Literal["din_sql", "mac_sql", "dail_sql", "codex_mcp"]


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = InputField(min_length=1, max_length=2000)
    db_id: str = InputField(pattern=r"^[A-Za-z0-9_-]+$", max_length=100)
    methods: list[Method] = InputField(min_length=1, max_length=4)
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
    difficulty: Literal["easy", "medium", "hard", "extra"] | None


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


class SchemaColumn(BaseModel):
    name: str
    type: str
    primary_key: int
    not_null: bool


class SchemaForeignKey(BaseModel):
    id: int
    sequence: int
    column: str
    target_table: str
    target_column: str | None


class SchemaObject(BaseModel):
    name: str
    ddl: str | None
    columns: list[SchemaColumn]
    foreign_keys: list[SchemaForeignKey]


class CancelResult(BaseModel):
    ok: bool


class HistorySelection(BaseModel):
    run_ids: list[str] = InputField(min_length=1)


class HistoryChange(BaseModel):
    changed_ids: list[str]
    skipped_ids: list[str] = InputField(default_factory=list)


class ComponentScore(BaseModel):
    acc: float
    rec: float
    f1: float
    label_total: int
    pred_total: int


class SqlMetrics(BaseModel):
    cm: dict[str, ComponentScore] | None = None
    cm_error: str | None = None
    em: int | None = None
    ex: int | None = None
    ves: float | None = None
    em_error: str | None = None
    ex_error: str | None = None
    ves_error: str | None = None
    iterations: int = 0
    predicted_ms: float | None = None
    gold_ms: float | None = None
    ves_valid_match: bool | None = None
