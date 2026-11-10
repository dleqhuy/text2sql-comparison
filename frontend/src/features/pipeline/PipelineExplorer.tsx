import { useEffect, useRef, useState } from "react"
import { isAxiosError } from "axios"
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Braces,
  Check,
  CheckCheck,
  ChevronRight,
  Circle,
  CircleCheck,
  Clock3,
  Code2,
  Copy,
  Database,
  FlaskConical,
  GitBranch,
  Layers3,
  Loader2,
  Maximize2,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Square,
  Terminal,
  TriangleAlert,
  Workflow,
  Trash2,
  Undo2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import {
  LiveService,
  type Bootstrap,
  type RunPublic as Run,
  type RunSnapshot as Snapshot,
  type TraceEvent as Event,
  type SchemaObject,
} from "@/client"
import { useQueryClient } from "@tanstack/react-query"
import { watchRun } from "./stream"

type Method = "din_sql" | "mac_sql" | "dail_sql" | "codex_mcp"
type Step = {
  stage: string
  input?: unknown
  output?: unknown
  status: string
  elapsed?: number
  time: number
}
type Result = {
  columns: string[]
  rows: unknown[][]
  truncated: boolean
  evaluation?: { correct: boolean; metric: string; gold_sql: string }
}
const methods: Method[] = ["din_sql", "mac_sql", "dail_sql", "codex_mcp"]
const info: Record<
  Method,
  { name: string; desc: string; stages: string[]; icon: typeof Layers3 }
> = {
  din_sql: {
    name: "DIN-SQL",
    desc: "Decompose · generate · correct",
    stages: [
      "Schema linking",
      "Classification",
      "SQL generation",
      "Self-correction",
    ],
    icon: Layers3,
  },
  mac_sql: {
    name: "MAC-SQL",
    desc: "Collaborative SQL agents",
    stages: ["Selector", "Decomposer", "Refiner"],
    icon: Workflow,
  },
  dail_sql: {
    name: "DAIL-SQL",
    desc: "Retrieve examples · two-pass SQL",
    stages: [
      "Preprocessing",
      "Example selection · pass 1",
      "SQL generation · pass 1",
      "Example selection · pass 2",
      "SQL generation · pass 2",
    ],
    icon: GitBranch,
  },
  codex_mcp: {
    name: "Codex MCP SQL",
    desc: "Agent + SQLite tools",
    stages: ["Codex turn", "search_objects", "execute_sql"],
    icon: Terminal,
  },
}
function format(value: unknown) {
  return typeof value === "string"
    ? value
    : (JSON.stringify(value, null, 2) ?? "")
}
function requestError(error: unknown) {
  if (isAxiosError(error) && typeof error.response?.data?.detail === "string")
    return error.response.data.detail
  return error instanceof Error ? error.message : "Không thể cập nhật lịch sử."
}
function buildSteps(events: Event[]): Step[] {
  const steps: Step[] = []
  for (const e of events) {
    if (e.kind === "queued") continue
    if (e.kind === "start") {
      steps.push({
        stage: e.stage,
        input: e.input,
        status: "running",
        time: e.time,
      })
      continue
    }
    const pending = [...steps]
      .reverse()
      .find((s) => s.stage === e.stage && s.status === "running")
    if (pending) {
      pending.output = e.output
      pending.elapsed = e.elapsed ?? undefined
      pending.status = e.kind === "error" ? "error" : "done"
    } else
      steps.push({
        stage: e.stage,
        input: e.input,
        output: e.output,
        status: ["error", "failed"].includes(e.kind) ? "error" : "done",
        elapsed: e.elapsed ?? undefined,
        time: e.time,
      })
  }
  return steps
}

export default function PipelineExplorer() {
  const queryClient = useQueryClient()
  const [boot, setBoot] = useState<Bootstrap | null>(null),
    [error, setError] = useState(""),
    [db, setDb] = useState("concert_singer"),
    [question, setQuestion] = useState("How many singers do we have?")
  const [chosen, setChosen] = useState<Method[]>(["din_sql", "mac_sql"]),
    [history, setHistory] = useState<Run[]>([]),
    [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [selectedMethod, setSelectedMethod] = useState<Method>("din_sql"),
    [selectedStep, setSelectedStep] = useState<number | null>(null),
    [tab, setTab] = useState("output"),
    [view, setView] = useState("trace")
  const [schema, setSchema] = useState<SchemaObject[]>([]),
    [busy, setBusy] = useState(false),
    [connected, setConnected] = useState(true),
    [copied, setCopied] = useState(false),
    [clock, setClock] = useState(Date.now())
  const [replay, setReplay] = useState<number | null>(null),
    [playing, setPlaying] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<
    { type: "one"; run: Run } | { type: "all" } | null
  >(null)
  const [historyBusy, setHistoryBusy] = useState(false)
  const [lastDeleted, setLastDeleted] = useState<string[]>([])
  const [historyNotice, setHistoryNotice] = useState("")
  const runViewVersion = useRef(0)
  const running = snapshot?.meta.status === "running"
  async function refreshHistory() {
    setHistory(
      await queryClient.fetchQuery({
        queryKey: ["pipeline-runs"],
        queryFn: async () => (await LiveService.listRuns()).data,
        staleTime: 0,
      }),
    )
  }
  useEffect(() => {
    queryClient
      .fetchQuery({
        queryKey: ["pipeline-bootstrap"],
        queryFn: async () => (await LiveService.bootstrap()).data,
      })
      .then((b) => {
        setBoot(b)
        setChosen((old) => old.filter((m) => b.readiness[m]?.ready))
      })
      .catch((e) => setError(`Không kết nối được backend: ${e.message}`))
    refreshHistory().catch((e) => setError(e.message))
  }, [])
  useEffect(() => {
    queryClient
      .fetchQuery({
        queryKey: ["pipeline-schema", db],
        queryFn: async () =>
          (await LiveService.readSchema({ path: { db_id: db } })).data,
      })
      .then(setSchema)
      .catch((e) => setError(e.message))
  }, [db])
  useEffect(() => {
    if (!running || !snapshot) return
    const controller = new AbortController()
    void watchRun(
      snapshot.meta.id,
      controller.signal,
      (data) => {
        setSnapshot(data)
        setConnected(true)
        if (data.meta.status !== "running")
          refreshHistory().catch((e) => setError(e.message))
      },
      () => setConnected(false),
    )
    return () => controller.abort()
  }, [snapshot?.meta.id, running])
  useEffect(() => {
    if (!running) return
    const t = setInterval(() => setClock(Date.now()), 500)
    return () => clearInterval(t)
  }, [running])
  useEffect(() => {
    if (!playing) return
    if (replay === null || replay >= (snapshot?.events.length ?? 0)) {
      setPlaying(false)
      return
    }
    const timer = setTimeout(() => setReplay(replay + 1), 600)
    return () => clearTimeout(timer)
  }, [playing, replay, snapshot?.events.length])
  const visibleEvents =
    replay === null
      ? (snapshot?.events ?? [])
      : (snapshot?.events ?? []).slice(0, replay)
  const steps = buildSteps(
    visibleEvents.filter((e) => e.method === selectedMethod),
  )
  const currentIndex =
    selectedStep === null
      ? steps.length - 1
      : Math.min(selectedStep, steps.length - 1)
  const step = steps[currentIndex]
  const methodEvents = visibleEvents.filter((e) => e.method === selectedMethod)
  const sql = methodEvents.find((e) => e.kind === "result")?.output
  const execution = methodEvents.find(
    (e) => e.stage === "SQLite execution" && e.kind === "finish",
  )?.output as Result | undefined
  const elapsed = snapshot
    ? (running
        ? clock / 1000
        : (snapshot.meta.finished_at ?? snapshot.meta.started_at)) -
      snapshot.meta.started_at
    : 0
  const matchingExample = boot?.examples.find(
    (e) => e.db_id === db && e.question === question,
  )
  async function start() {
    runViewVersion.current += 1
    setError("")
    setBusy(true)
    setReplay(null)
    setPlaying(false)
    try {
      const { data: meta } = await LiveService.createRun({
        body: {
          db_id: db,
          question,
          methods: chosen,
          example_index: matchingExample?.index ?? null,
        },
      })
      setSnapshot({ meta, events: [] })
      setSelectedMethod(chosen[0])
      setSelectedStep(null)
      setView("trace")
      await refreshHistory()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  async function openRun(run: Run) {
    const version = ++runViewVersion.current
    try {
      const { data } = await LiveService.readRun({ path: { run_id: run.id } })
      if (version !== runViewVersion.current) return
      setSnapshot(data)
      setDb(run.db_id)
      setQuestion(run.question)
      setChosen(run.methods.filter((m) => boot?.readiness[m]?.ready))
      setSelectedMethod(run.methods[0])
      setSelectedStep(null)
      setReplay(null)
      setPlaying(false)
      setView("trace")
      setError("")
    } catch (e) {
      if (version === runViewVersion.current) setError((e as Error).message)
    }
  }
  async function deleteHistory() {
    if (!pendingDelete) return
    setHistoryBusy(true)
    setError("")
    runViewVersion.current += 1
    try {
      const { data } =
        pendingDelete.type === "all"
          ? await LiveService.clearHistory()
          : await LiveService.deleteRun({
              path: { run_id: pendingDelete.run.id },
            })
      const skipped = data.skipped_ids?.length ?? 0
      setLastDeleted(data.changed_ids)
      setHistoryNotice(
        `Đã xóa ${data.changed_ids.length} phiên khỏi lịch sử.${skipped ? ` Giữ lại ${skipped} phiên đang chạy.` : ""}`,
      )
      const deleted = new Set(data.changed_ids)
      if (snapshot && deleted.has(snapshot.meta.id)) {
        setSnapshot(null)
        setSelectedStep(null)
        setReplay(null)
        setPlaying(false)
      }
      setPendingDelete(null)
      await refreshHistory()
    } catch (error) {
      setError(requestError(error))
    } finally {
      setHistoryBusy(false)
    }
  }
  async function undoDelete() {
    setHistoryBusy(true)
    setError("")
    try {
      const { data } = await LiveService.restoreHistory({
        body: { run_ids: lastDeleted },
      })
      setLastDeleted([])
      setHistoryNotice(`Đã khôi phục ${data.changed_ids.length} phiên.`)
      await refreshHistory()
    } catch (error) {
      setError(requestError(error))
    } finally {
      setHistoryBusy(false)
    }
  }
  async function cancel() {
    if (snapshot)
      try {
        await LiveService.cancelRun({ path: { run_id: snapshot.meta.id } })
      } catch (e) {
        setError((e as Error).message)
      }
  }
  function exportRun() {
    if (!snapshot) return
    const a = document.createElement("a")
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(snapshot, null, 2)], {
        type: "application/json",
      }),
    )
    a.download = `sql-lab-${snapshot.meta.id}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        format(
          view === "results"
            ? sql
            : step?.[tab === "input" ? "input" : "output"],
        ),
      )
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setError("Trình duyệt không cho phép sao chép clipboard.")
    }
  }
  function changeDb(value: string) {
    setDb(value)
    const first = boot?.examples.find((e) => e.db_id === value)
    if (first) setQuestion(first.question)
  }
  const statusText =
    replay !== null
      ? "REPLAY"
      : running
        ? connected
          ? "LIVE"
          : "RECONNECTING"
        : snapshot?.meta.status === "completed"
          ? "COMPLETED"
          : snapshot?.meta.status === "cancelled"
            ? "CANCELLED"
            : snapshot
              ? "FINISHED"
              : "READY"
  return (
    <div className="app">
      <aside className="rail">
        <div>
          <div className="logo">
            <span className="logo-icon">
              <Braces size={22} />
            </span>
            sql<span style={{ fontWeight: 350 }}> / lab</span>
          </div>
          <div className="rail-tag">TEXT-TO-SQL OBSERVATORY</div>
        </div>
        <div className="nav-current">
          <Activity size={15} /> Pipeline explorer
        </div>
        <div>
          <div className="label" style={{ padding: "0 9px" }}>
            Lịch sử chạy{" "}
            <span style={{ float: "right" }}>
              {history.length.toString().padStart(2, "0")}
            </span>
          </div>
          <div className="history-list">
            {history.length === 0 ? (
              <p className="tiny" style={{ padding: "0 9px", lineHeight: 1.8 }}>
                Các phiên chạy được lưu ở đây để xem lại từng bước.
              </p>
            ) : (
              history.slice(0, 14).map((r) => (
                <div className="history-row" key={r.id}>
                  <button
                    className={`history-item ${snapshot?.meta.id === r.id ? "active" : ""}`}
                    onClick={() => openRun(r)}
                    disabled={busy || historyBusy}
                  >
                    <span>{r.question}</span>
                    <small>
                      {r.db_id} ·{" "}
                      {new Date(r.started_at * 1000).toLocaleTimeString(
                        "vi-VN",
                        {
                          hour: "2-digit",
                          minute: "2-digit",
                        },
                      )}{" "}
                      {r.status === "running" ? "●" : ""}
                    </small>
                  </button>
                  <button
                    className="history-delete"
                    aria-label={`Xóa phiên ${r.id}`}
                    title={
                      r.status === "running"
                        ? "Phiên đang chạy"
                        : "Xóa phiên khỏi lịch sử"
                    }
                    disabled={r.status === "running" || historyBusy}
                    onClick={() => setPendingDelete({ type: "one", run: r })}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="rail-bottom">
          <div className="label" style={{ marginBottom: 8 }}>
            Trong workspace
          </div>
          <div>01 &nbsp; DIN-SQL</div>
          <div>02 &nbsp; MAC-SQL</div>
          <div>03 &nbsp; Codex MCP SQL</div>
          <div
            style={{
              marginTop: 16,
              display: "flex",
              gap: 6,
              alignItems: "center",
            }}
          >
            <span className="dot" /> Local environment
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            Workspace{" "}
            <span style={{ margin: "0 10px", color: "#b2b9ac" }}>/</span>{" "}
            <strong>Text2SQL comparison</strong>
          </span>
          <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span className="connection">
              <span className="dot" />
              {boot?.endpoint ?? "Connecting to local API…"}
            </span>
          </span>
        </header>
        <div className="hero">
          <div>
            <div className="label">OBSERVE. INSPECT. UNDERSTAND.</div>
            <h1>Từ câu hỏi đến SQL.</h1>
            <p className="subtitle">
              Theo dõi từng bước xử lý thật. Hiểu mỗi phương pháp đi đến câu trả
              lời như thế nào.
            </p>
          </div>
          <div className="hero-counter">
            03 METHODS{" "}
            <span style={{ margin: "0 12px", color: "#d0d7c7" }}>/</span> 01
            SHARED INPUT
          </div>
        </div>
        {error && (
          <div role="alert" className="error-banner">
            <TriangleAlert size={15} />
            {error}
            <button
              style={{ marginLeft: "auto", border: 0, background: "none" }}
              onClick={() => setError("")}
              aria-label="Đóng thông báo"
            >
              ×
            </button>
          </div>
        )}
        {snapshot?.meta.error && (
          <div role="alert" className="error-banner">
            {snapshot.meta.error}
          </div>
        )}
        {historyNotice && (
          <div className="history-notice" role="status">
            <span>{historyNotice}</span>
            {lastDeleted.length > 0 && (
              <Button
                size="sm"
                variant="ghost"
                disabled={historyBusy}
                onClick={undoDelete}
              >
                <Undo2 size={13} /> Hoàn tác
              </Button>
            )}
            <button
              aria-label="Đóng thông báo lịch sử"
              onClick={() => setHistoryNotice("")}
            >
              ×
            </button>
          </div>
        )}
        <section className="input-panel" aria-label="Cấu hình đầu vào">
          <div>
            <div className="input-top">
              <span className="section-heading">
                <Database size={14} /> Input chung
              </span>
              <select
                aria-label="Database"
                value={db}
                disabled={running}
                onChange={(e) => changeDb(e.target.value)}
              >
                {(boot?.databases ?? [db]).map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            <select
              className="example-picker"
              aria-label="Chọn câu hỏi Spider"
              disabled={running}
              value={matchingExample?.index ?? "custom"}
              onChange={(e) => {
                const found = boot?.examples.find(
                  (x) => x.index === Number(e.target.value),
                )
                if (found) setQuestion(found.question)
                else if (e.target.value === "custom") setQuestion("")
              }}
            >
              <option value="custom">Câu hỏi tùy chỉnh — không chấm EX</option>
              {boot?.examples
                .filter((e) => e.db_id === db)
                .map((e) => (
                  <option key={e.index} value={e.index}>
                    #{String(e.index).padStart(4, "0")} · {e.question}
                  </option>
                ))}
            </select>
            <textarea
              aria-label="Câu hỏi đầu vào"
              value={question}
              disabled={running}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={2000}
            />
            <div className="question-note">
              <GitBranch size={11} />
              {matchingExample
                ? `Spider dev · #${String(matchingExample.index).padStart(4, "0")} · Có đáp án để chấm SQLite EX`
                : "Custom input · Thực thi SQL, không có đáp án tham chiếu"}
            </div>
          </div>
          <div className="run-config">
            <div className="label" style={{ marginBottom: 3 }}>
              Phương pháp
            </div>
            {methods.map((m) => (
              <label
                key={m}
                className={`method-toggle ${boot && !boot.readiness[m]?.ready ? "disabled" : ""}`}
                title={boot?.readiness[m]?.reason}
              >
                <input
                  type="checkbox"
                  checked={chosen.includes(m)}
                  disabled={running || !boot?.readiness[m]?.ready}
                  onChange={(e) =>
                    setChosen((old) =>
                      e.target.checked
                        ? [...old, m]
                        : old.filter((x) => x !== m),
                    )
                  }
                />
                {info[m].name}
                <small>{m === "codex_mcp" ? "SDK + MCP" : "LLM API"}</small>
              </label>
            ))}
            <div className="run-action">
              <Button
                disabled={
                  !boot || busy || running || !chosen.length || !question.trim()
                }
                onClick={start}
              >
                {busy ? (
                  <Loader2 size={13} className="spin" />
                ) : (
                  <Play size={13} />
                )}{" "}
                Chạy pipeline <ArrowRight size={14} />
              </Button>
              {running && (
                <Button
                  variant="outline"
                  size="icon"
                  onClick={cancel}
                  title="Dừng phiên chạy"
                >
                  <Square size={13} />
                </Button>
              )}
            </div>
            <div className="tiny" style={{ fontSize: 9 }}>
              Mỗi phương pháp dùng runner gốc · {boot?.model ?? "…"}
            </div>
          </div>
        </section>
        <div className="toolbar">
          <span className="section-heading">
            <Radio size={14} />
            {replay !== null ? "Replay timeline" : "Live pipeline"}{" "}
            <Badge variant="secondary" className={running ? "pulse" : ""}>
              {statusText}
            </Badge>
          </span>
          <div className="toolbar-actions">
            <select
              aria-label="Mở lịch sử chạy"
              className="history-picker"
              disabled={busy || historyBusy}
              value={snapshot?.meta.id ?? ""}
              onChange={(e) => {
                const run = history.find((r) => r.id === e.target.value)
                if (run) openRun(run)
              }}
            >
              <option value="">Lịch sử chạy</option>
              {history.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id.slice(0, 6)} · {r.question}
                </option>
              ))}
            </select>
            <span
              className="tiny"
              style={{ fontFamily: "monospace", marginRight: 8 }}
            >
              {snapshot
                ? `${Math.max(0, elapsed).toFixed(1)}s · ${visibleEvents.length} events`
                : "Đang chờ input"}
            </span>
            <Button
              size="sm"
              variant="ghost"
              disabled={!snapshot || running}
              onClick={() => {
                setReplay(0)
                setPlaying(true)
                setSelectedStep(null)
              }}
            >
              <RotateCcw size={12} /> Phát lại
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={!snapshot}
              onClick={exportRun}
            >
              <ArrowDownToLine size={12} /> JSON
            </Button>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Xóa phiên đang xem"
              title="Xóa phiên đang xem"
              disabled={!snapshot || running || historyBusy}
              onClick={() =>
                snapshot &&
                setPendingDelete({ type: "one", run: snapshot.meta })
              }
            >
              <Trash2 size={14} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={
                historyBusy || !history.some((run) => run.status !== "running")
              }
              onClick={() => setPendingDelete({ type: "all" })}
            >
              <Trash2 size={12} /> Xóa lịch sử
            </Button>
          </div>
        </div>
        {replay !== null && (
          <div className="replay-strip">
            <button
              aria-label={playing ? "Tạm dừng phát lại" : "Tiếp tục phát lại"}
              onClick={() => setPlaying(!playing)}
              style={{ border: 0, background: "none" }}
            >
              {playing ? <Pause size={13} /> : <Play size={13} />}
            </button>
            <span>
              {replay}/{snapshot?.events.length} events
            </span>
            <input
              aria-label="Vị trí phát lại"
              type="range"
              min="0"
              max={snapshot?.events.length ?? 0}
              value={replay}
              onChange={(e) => {
                setReplay(+e.target.value)
                setPlaying(false)
                setSelectedStep(null)
              }}
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setReplay(null)
                setPlaying(false)
              }}
            >
              Xem toàn bộ
            </Button>
          </div>
        )}
        <section className="method-grid" aria-label="Các phương pháp">
          {methods.map((m, mi) => {
            const entries = visibleEvents.filter((e) => e.method === m),
              list = buildSteps(entries),
              hasError = entries.some(
                (e) =>
                  e.kind === "failed" ||
                  (e.stage === "SQLite execution" && e.kind === "error"),
              ),
              result = entries.find((e) => e.kind === "result"),
              query = entries.find(
                (e) => e.stage === "SQLite execution" && e.kind === "finish",
              )?.output as Result | undefined
            const MethodIcon = info[m].icon
            const selected = snapshot
              ? snapshot.meta.methods.includes(m)
              : chosen.includes(m)
            return (
              <article
                key={m}
                className={`method-card ${selectedMethod === m ? "selected" : ""}`}
              >
                <button
                  className="method-head"
                  onClick={() => {
                    setSelectedMethod(m)
                    setSelectedStep(null)
                    setView("trace")
                  }}
                >
                  <span className="method-symbol">
                    <MethodIcon size={15} />
                  </span>
                  <div>
                    <div className="method-name">{info[m].name}</div>
                    <div className="method-desc">{info[m].desc}</div>
                  </div>
                  <span
                    className="status-dot"
                    style={{
                      color: hasError
                        ? "#c5735f"
                        : result
                          ? "#6b8c4c"
                          : "#9da592",
                    }}
                  >
                    {hasError ? (
                      <TriangleAlert size={12} />
                    ) : result ? (
                      <CircleCheck size={12} />
                    ) : running && entries.length ? (
                      <Loader2 size={12} className="spin" />
                    ) : (
                      <Circle size={9} />
                    )}
                  </span>
                </button>
                <div className="method-steps">
                  {list.length ? (
                    list.map((s, i) => (
                      <button
                        key={`${s.stage}-${s.time}-${i}`}
                        className={`step ${s.status === "error" ? "error" : ""} ${selectedMethod === m && currentIndex === i ? "active" : ""}`}
                        onClick={() => {
                          setSelectedMethod(m)
                          setSelectedStep(i)
                          setTab(s.output === undefined ? "input" : "output")
                          setView("trace")
                        }}
                      >
                        <span className="step-icon">
                          {s.status === "running" ? (
                            running || replay !== null ? (
                              <Loader2 size={12} className="spin" />
                            ) : (
                              <TriangleAlert size={12} />
                            )
                          ) : s.status === "error" ? (
                            <TriangleAlert size={12} />
                          ) : (
                            <Check size={12} />
                          )}
                        </span>
                        <span>{s.stage}</span>
                        <small>
                          {s.elapsed !== undefined
                            ? `${s.elapsed.toFixed(1)}s`
                            : s.status === "running"
                              ? "…"
                              : String(i + 1).padStart(2, "0")}
                        </small>
                      </button>
                    ))
                  ) : (
                    <>
                      {info[m].stages.map((s, i) => (
                        <div className="step waiting" key={s}>
                          <Circle size={11} />
                          <span>{s}</span>
                          <small>0{i + 1}</small>
                        </div>
                      ))}
                      <div
                        className="tiny"
                        style={{
                          padding: "12px 8px",
                          fontSize: 10,
                          lineHeight: 1.7,
                        }}
                      >
                        {!boot?.readiness[m]?.ready
                          ? boot?.readiness[m]?.reason
                          : selected
                            ? "Sẵn sàng nhận câu hỏi."
                            : "Không được chọn trong phiên này."}
                      </div>
                    </>
                  )}
                </div>
                <div className="method-foot">
                  <span>
                    0{mi + 1} /{" "}
                    {m === "codex_mcp" ? boot?.codex_model : boot?.model}
                  </span>
                  <span>
                    {query?.evaluation
                      ? query.evaluation.correct
                        ? "EX MATCH"
                        : "EX MISMATCH"
                      : query
                        ? "EXECUTED"
                        : hasError
                          ? "FAILED"
                          : result
                            ? "SQL READY"
                            : running && entries.length
                              ? "RUNNING"
                              : "AWAITING"}
                  </span>
                </div>
              </article>
            )
          })}
        </section>
        <section className="inspector" aria-label="Chi tiết từng bước">
          <div className="inspector-head">
            <div className="inspector-title">
              <Maximize2 size={13} />
              {info[selectedMethod].name}
              <ChevronRight size={12} style={{ color: "#a4ae9b" }} />
              <span style={{ fontWeight: 450, color: "#85927a" }}>
                {view === "trace"
                  ? (step?.stage ?? "Step inspector")
                  : view === "schema"
                    ? "Database schema"
                    : "Final result"}
              </span>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              <Button
                size="sm"
                variant={view === "trace" ? "secondary" : "ghost"}
                onClick={() => setView("trace")}
              >
                <Code2 size={12} /> Trace
              </Button>
              <Button
                size="sm"
                variant={view === "schema" ? "secondary" : "ghost"}
                onClick={() => setView("schema")}
              >
                <Database size={12} /> Schema
              </Button>
              <Button
                size="sm"
                variant={view === "results" ? "secondary" : "ghost"}
                onClick={() => setView("results")}
              >
                <CheckCheck size={12} /> Result
              </Button>
            </div>
          </div>
          <div className="inspector-body">
            {view === "schema" ? (
              <div className="schema-list">
                {schema.map((t) => (
                  <div className="schema-table" key={t.name}>
                    <h3>{t.name}</h3>
                    <pre>{t.ddl}</pre>
                  </div>
                ))}
              </div>
            ) : view === "results" ? (
              sql ? (
                <>
                  <div className="inspect-intro">
                    <Database size={12} />
                    {snapshot?.meta.db_id} · SQLite read-only · tối đa 100 dòng
                    hiển thị
                  </div>
                  <div className="payload dark">
                    <pre>{format(sql)}</pre>
                  </div>
                  {execution ? (
                    <>
                      <div className="result-table-wrap">
                        <table>
                          <thead>
                            <tr>
                              {execution.columns.map((c, i) => (
                                <th key={i}>{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {execution.rows.map((r, i) => (
                              <tr key={i}>
                                {r.map((c, j) => (
                                  <td key={j}>
                                    {c === null ? "NULL" : String(c)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="tiny" style={{ marginTop: 9 }}>
                        {execution.rows.length} dòng
                        {execution.truncated ? " · kết quả đã cắt bớt" : ""}
                      </p>
                      {execution.evaluation ? (
                        <div
                          className={`evaluation ${execution.evaluation.correct ? "" : "wrong"}`}
                        >
                          <CircleCheck size={14} />
                          {execution.evaluation.correct
                            ? "Khớp đáp án"
                            : "Không khớp đáp án"}{" "}
                          · SQLite EX trên 1 database
                        </div>
                      ) : (
                        <div className="tiny">
                          Câu hỏi tùy chỉnh: không chấm đúng/sai.
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="tiny" style={{ marginTop: 12 }}>
                      {methodEvents.find(
                        (e) =>
                          e.stage === "SQLite execution" && e.kind === "error",
                      )
                        ? `Lỗi thực thi: ${format(methodEvents.find((e) => e.stage === "SQLite execution" && e.kind === "error")?.output)}`
                        : "Đang chờ thực thi SQLite…"}
                    </p>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    style={{ marginTop: 8 }}
                    onClick={copy}
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />} Copy SQL
                  </Button>
                </>
              ) : (
                <div className="empty-state">
                  <Database size={25} />
                  SQL cuối cùng và dữ liệu trả về sẽ xuất hiện ở đây.
                </div>
              )
            ) : step ? (
              <>
                <div className="inspect-intro">
                  <span className="dot" />
                  {step.status === "running"
                    ? running
                      ? "Đang xử lý…"
                      : "Bước chưa hoàn tất"
                    : step.status === "error"
                      ? "Bước có lỗi"
                      : "Đã nhận output"}{" "}
                  <span
                    style={{
                      marginLeft: "auto",
                      display: "flex",
                      alignItems: "center",
                      gap: 5,
                    }}
                  >
                    <Clock3 size={11} />
                    {new Date(step.time * 1000).toLocaleTimeString("vi-VN")}
                    {step.elapsed !== undefined
                      ? ` · ${step.elapsed.toFixed(2)}s`
                      : ""}
                  </span>
                </div>
                <Tabs
                  value={tab}
                  onValueChange={setTab}
                  className="inspect-tabs"
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <TabsList>
                      <TabsTrigger value="input">Input / prompt</TabsTrigger>
                      <TabsTrigger value="output">
                        Output / response
                      </TabsTrigger>
                    </TabsList>
                    <Button variant="ghost" size="sm" onClick={copy}>
                      {copied ? <Check size={12} /> : <Copy size={12} />} Copy
                    </Button>
                  </div>
                  <TabsContent value="input">
                    <div className="payload">
                      <pre>
                        {step.input === undefined ? (
                          <span className="empty">
                            Bước này không có input riêng được ghi lại.
                          </span>
                        ) : (
                          format(step.input)
                        )}
                      </pre>
                    </div>
                  </TabsContent>
                  <TabsContent value="output">
                    <div
                      className={`payload ${step.stage === "Final SQL" ? "dark" : ""}`}
                    >
                      <pre>
                        {step.output === undefined ? (
                          <span className="empty">
                            {step.status === "running"
                              ? "Đang chờ phản hồi từ runner…"
                              : "Không có output riêng."}
                          </span>
                        ) : (
                          format(step.output)
                        )}
                      </pre>
                    </div>
                  </TabsContent>
                </Tabs>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: 12,
                  }}
                >
                  <span className="tiny">
                    Phản hồi công khai từ runner gốc · không tạo bước giả lập
                  </span>
                  <div style={{ display: "flex", gap: 4 }}>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={currentIndex <= 0}
                      onClick={() => setSelectedStep(currentIndex - 1)}
                    >
                      ← Trước
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={currentIndex >= steps.length - 1}
                      onClick={() => setSelectedStep(currentIndex + 1)}
                    >
                      Tiếp →
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <FlaskConical size={27} />
                <div
                  style={{ fontSize: 14, color: "#647557", marginBottom: 5 }}
                >
                  Mỗi bước đều có một câu chuyện.
                </div>
                Chạy pipeline rồi chọn một bước để xem input và output thật.
                <br />
                Bạn có thể chuyển giữa 4 phương pháp để đối chiếu cách xử lý.
              </div>
            )}
          </div>
        </section>
        <footer className="footer">
          <span>
            SQL / LAB &nbsp; · &nbsp; SPIDER 1.0 &nbsp; · &nbsp; FASTAPI +
            POSTGRESQL
          </span>
          <span>React · FastAPI · PostgreSQL · shadcn/ui</span>
        </footer>
      </main>
      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !historyBusy) setPendingDelete(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {pendingDelete?.type === "all"
                ? "Xóa toàn bộ lịch sử đã kết thúc?"
                : "Xóa phiên này khỏi lịch sử?"}
            </DialogTitle>
            <DialogDescription>
              Bạn có thể hoàn tác ngay sau khi xóa. Phiên đang chạy sẽ được giữ
              lại.
            </DialogDescription>
          </DialogHeader>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {pendingDelete?.type === "one" && (
            <p className="text-sm break-words">{pendingDelete.run.question}</p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              disabled={historyBusy}
              onClick={() => setPendingDelete(null)}
            >
              Giữ lại
            </Button>
            <Button
              variant="destructive"
              disabled={historyBusy}
              onClick={deleteHistory}
            >
              {historyBusy ? (
                <Loader2 size={13} className="spin" />
              ) : (
                <Trash2 size={13} />
              )}{" "}
              {pendingDelete?.type === "all"
                ? "Xóa các phiên đã kết thúc"
                : "Xóa phiên"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
