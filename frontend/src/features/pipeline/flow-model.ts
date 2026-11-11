import type { TraceEvent } from "@/client"

export type Method = TraceEvent["method"]
export type StepStatus = "running" | "done" | "error" | "interrupted"
export type Step = {
  id: string
  stage: string
  input?: unknown
  output?: unknown
  status: StepStatus
  elapsed?: number
  time: number
  endTime?: number
  attempt: number
}

/** Pair each completion with its own pending start, retaining nested calls/retries. */
export function buildSteps(events: TraceEvent[], terminal = false): Step[] {
  const steps: Step[] = []
  const attempts = new Map<string, number>()
  events.forEach((e, index) => {
    if (e.kind === "queued") return
    if (e.kind === "failed") {
      for (const pending of steps) {
        if (pending.status === "running" && pending.stage !== e.stage) {
          pending.status = "interrupted"
          pending.endTime = e.time
        }
      }
    }
    if (e.kind !== "start") {
      const pending = [...steps]
        .reverse()
        .find((s) => s.stage === e.stage && s.status === "running")
      if (pending) {
        pending.output = e.output
        pending.endTime = e.time
        pending.elapsed = e.elapsed ?? undefined
        pending.status = ["error", "failed"].includes(e.kind) ? "error" : "done"
        return
      }
    }
    const attempt = (attempts.get(e.stage) ?? 0) + 1
    attempts.set(e.stage, attempt)
    steps.push({
      id: `${e.method}-${index}`,
      stage: e.stage,
      input: e.input ?? undefined,
      output: e.output ?? undefined,
      status:
        e.kind === "start"
          ? "running"
          : ["error", "failed"].includes(e.kind)
            ? "error"
            : "done",
      elapsed: e.elapsed ?? undefined,
      time: e.time,
      endTime: e.kind === "start" ? undefined : e.time,
      attempt,
    })
  })
  if (terminal)
    for (const step of steps)
      if (step.status === "running") step.status = "interrupted"
  return steps
}

export type StageSpec = {
  stage: string
  title: string
  lane: number
  column: number
}
export const laneTitles: Record<Method, string[]> = {
  dail_sql: ["ĐIỀU PHỐI", "DỮ LIỆU & VÍ DỤ", "LLM", "SQLITE / ĐÁNH GIÁ"],
  din_sql: ["ĐIỀU PHỐI", "SCHEMA & PHÂN LOẠI", "LLM", "SQLITE / ĐÁNH GIÁ"],
  mac_sql: ["ĐIỀU PHỐI", "TRẠNG THÁI AGENT", "LLM", "SQLITE / REFINER"],
  codex_mcp: [
    "ĐIỀU PHỐI",
    "KHÁM PHÁ SCHEMA",
    "AGENT CODEX",
    "SQLITE / CÔNG CỤ",
  ],
}
const spec = (
  stage: string,
  title: string,
  lane: number,
  column: number,
): StageSpec => ({ stage, title, lane, column })
export const blueprints: Record<Method, StageSpec[]> = {
  dail_sql: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Preprocessing", "Tiền xử lý", 1, 0),
    spec("Example selection · pass 1", "Lượt 1 · Chọn ví dụ", 1, 1),
    spec("SQL generation · pass 1", "Lượt 1 · Sinh SQL sơ bộ", 2, 1),
    spec("Example selection · pass 2", "Lượt 2 · Chọn lại ví dụ", 1, 2),
    spec("SQL generation · pass 2", "Lượt 2 · Sinh SQL cuối", 2, 2),
    spec("Final SQL", "SQL cuối", 0, 3),
    spec("SQLite execution", "Thực thi & đánh giá", 3, 3),
  ],
  din_sql: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Schema linking", "Liên kết schema", 1, 0),
    spec("Classification", "Phân loại câu hỏi", 1, 1),
    spec("SQL generation", "Sinh SQL", 2, 2),
    spec("Self-correction", "Kiểm tra & sửa SQL", 2, 3),
    spec("Final SQL", "SQL cuối", 0, 3),
    spec("SQLite execution", "Thực thi & đánh giá", 3, 3),
  ],
  mac_sql: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Selector · state", "Selector · trạng thái", 1, 0),
    spec("Decomposer · state", "Decomposer · trạng thái", 1, 1),
    spec("Decomposer", "Decomposer · gọi LLM", 2, 1),
    spec("Refiner · state", "Refiner · trạng thái", 3, 2),
    spec("Final SQL", "SQL cuối", 0, 3),
    spec("SQLite execution", "Thực thi & đánh giá", 3, 3),
  ],
  codex_mcp: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Codex turn", "Phiên Codex", 2, 0),
    spec("search_objects", "Tìm bảng / cột", 1, 1),
    spec("execute_sql", "Thử SQL qua MCP", 3, 2),
    spec("Final SQL", "SQL cuối", 0, 3),
    spec("SQLite execution", "Thực thi & đánh giá", 3, 3),
  ],
}

export function stageSpec(method: Method, stage: string): StageSpec {
  const known = blueprints[method].find((s) => s.stage === stage)
  if (known) return known
  if (method === "dail_sql" && stage.startsWith("LLM response")) {
    const pass = stage.endsWith("1") ? 1 : 2
    return spec(stage, `Lượt ${pass} · Phản hồi LLM`, 2, pass)
  }
  if (
    method === "mac_sql" &&
    ["Selector", "Refiner", "Connection check"].includes(stage)
  ) {
    return spec(stage, `${stage} · gọi LLM`, 2, stage === "Refiner" ? 2 : 0)
  }
  return spec(stage, stage, 0, 4)
}

export function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}
const sqlText = (value: unknown): string | undefined => {
  if (typeof value !== "string") return undefined
  const fence = value.match(/```(?:sql)?\s*([\s\S]*?)```/i)?.[1]?.trim()
  if (fence && /^(SELECT|WITH)\b/i.test(fence)) return fence
  if (/^\s*(SELECT|WITH)\b/i.test(value)) return value
  return undefined
}
export type TableResult = {
  columns: string[]
  rows: unknown[][]
  truncated?: boolean
  evaluation?: { correct: boolean; metric: string }
}
export function tableResult(value: unknown): TableResult | undefined {
  const data = record(value)
  if (
    !Array.isArray(data?.columns) ||
    !data.columns.every((c) => typeof c === "string") ||
    !Array.isArray(data.rows) ||
    !data.rows.every(Array.isArray)
  )
    return undefined
  return data as unknown as TableResult
}

/** Details only from the selected record or a child call within its time interval. */
export function stepDetails(step: Step, steps: Step[]) {
  const input = record(step.input),
    output = record(step.output)
  const nextInvocation = steps.find(
    (s) => s.stage === step.stage && s.time > step.time,
  )
  const endTime = step.endTime ?? nextInvocation?.time
  const child = step.stage.startsWith("SQL generation · pass ")
    ? steps.find(
        (s) =>
          s.stage === step.stage.replace("SQL generation", "LLM response") &&
          s.time >= step.time &&
          (endTime === undefined || s.time <= endTime),
      )
    : undefined
  const childInput = record(child?.input)
  const prompt =
    typeof input?.prompt === "string"
      ? input.prompt
      : typeof output?.prompt === "string"
        ? output.prompt
        : typeof childInput?.prompt === "string"
          ? childInput.prompt
          : typeof step.input === "string" && !sqlText(step.input)
            ? step.input
            : undefined
  let finalResponse = output?.final_response
  if (typeof finalResponse === "string") {
    try {
      finalResponse = JSON.parse(finalResponse)
    } catch {
      /* Public response may be plain SQL. */
    }
  }
  const sql =
    sqlText(step.output) ??
    sqlText(output?.pred) ??
    sqlText(output?.sql) ??
    sqlText(record(finalResponse)?.sql) ??
    sqlText(finalResponse) ??
    sqlText(input?.sql) ??
    sqlText(step.input)
  const examples = Array.isArray(output?.examples) ? output.examples : undefined
  const response = record(step.output)?.response
  return {
    prompt,
    sql,
    table: tableResult(step.output),
    examples,
    response:
      typeof response === "string"
        ? response
        : Array.isArray(response)
          ? response.join("\n\n")
          : undefined,
    promptSource:
      child && typeof childInput?.prompt === "string"
        ? child.stage
        : step.stage,
  }
}

export function classification(steps: Step[]) {
  const latest = [...steps]
    .reverse()
    .find((s) => s.stage === "Classification" && typeof s.output === "string")
  return typeof latest?.output === "string"
    ? latest.output
        .match(/Label\s*:\s*["']?(NON-NESTED|NESTED|EASY)\b/i)?.[1]
        ?.toUpperCase()
    : undefined
}
