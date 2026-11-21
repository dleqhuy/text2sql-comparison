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
  calls?: Step[]
  checks?: Step[]
}

/** Pair each completion with its own pending start, retaining nested calls/retries. */
export function buildSteps(events: TraceEvent[], terminal = false): Step[] {
  const steps: Step[] = []
  const attempts = new Map<string, number>()
  events.forEach((e, index) => {
    if (e.kind === "queued" || e.stage === "Final SQL") return
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
  // Older Codex traces closed the SDK turn before the runner validated it.
  for (const step of steps) {
    if (
      !step.id.startsWith("codex_mcp-") ||
      step.stage !== "Codex turn" ||
      step.status !== "done"
    )
      continue
    const output = record(step.output)
    if (
      output?.error ||
      output?.runner_status === "failed" ||
      /(?:^|\.)(failed|cancelled|interrupted)$/.test(String(output?.status))
    )
      step.status = "error"
  }
  // Agent state encloses its LLM calls and SQL checks. Show one node per
  // invocation while retaining the nested records in its detail panel.
  const children = new Set<Step>()
  for (const parent of steps) {
    if (
      parent.id.startsWith("dail_sql-") &&
      parent.stage.startsWith("SQL generation · pass ")
    ) {
      const next = steps.find(
        (s) => s.stage === parent.stage && s.time > parent.time,
      )
      const end = Math.min(parent.endTime ?? Infinity, next?.time ?? Infinity)
      parent.calls = steps.filter(
        (s) =>
          s.id.startsWith("dail_sql-") &&
          s.stage === parent.stage.replace("SQL generation", "LLM response") &&
          s.time >= parent.time &&
          s.time < end,
      )
      for (const child of parent.calls) children.add(child)
      continue
    }
    if (!parent.id.startsWith("mac_sql-") || !macAgents[parent.stage]) continue
    const agent = parent.stage.replace(" · state", "")
    const next = steps.find(
      (s) => s.stage === parent.stage && s.time > parent.time,
    )
    const end = Math.min(parent.endTime ?? Infinity, next?.time ?? Infinity)
    const nested = steps.filter(
      (s) =>
        s.time >= parent.time &&
        s.time < end &&
        (s.stage === agent || s.stage === `${agent} · execution`),
    )
    parent.calls = nested.filter((s) => s.stage === agent)
    parent.checks = nested.filter((s) => s.stage === `${agent} · execution`)
    for (const child of nested) children.add(child)
  }
  return groupDinRetries(steps.filter((s) => !children.has(s)))
}

/** Consecutive failed calls with the same prompt are retries of one DIN stage. */
function groupDinRetries(steps: Step[]): Step[] {
  const grouped: Step[] = []
  const llmStages = [
    "Schema linking",
    "Classification",
    "SQL generation",
    "Self-correction",
  ]
  for (const step of steps) {
    const previous = grouped[grouped.length - 1]
    const prompt = (s: Step) =>
      typeof s.input === "string" ? s.input : record(s.input)?.prompt
    if (
      step.id.startsWith("din_sql-") &&
      llmStages.includes(step.stage) &&
      previous?.stage === step.stage &&
      previous.status === "error" &&
      typeof prompt(step) === "string" &&
      prompt(step) === prompt(previous)
    ) {
      previous.calls ??= [{ ...previous }]
      previous.calls.push(step)
      previous.output = step.output
      previous.status = step.status
      previous.endTime = step.endTime
      previous.elapsed =
        step.endTime === undefined ? undefined : step.endTime - previous.time
    } else grouped.push(step)
  }
  return grouped
}

export const macAgents: Record<string, { title: string; purpose: string }> = {
  "Selector · state": {
    title: "Selector · Chọn schema",
    purpose:
      "Chuẩn bị mô tả bảng, cột và khóa ngoại cho Decomposer. Với schema lớn, gọi LLM để chọn phần liên quan; schema nhỏ có thể được giữ nguyên mà không gọi LLM.",
  },
  "Decomposer · state": {
    title: "Decomposer · Sinh SQL",
    purpose:
      "Nhận câu hỏi và schema từ Selector, ghép prompt để LLM phân rã bài toán và sinh SQL. SQL được trích từ phản hồi rồi chuyển cho Refiner.",
  },
  "Refiner · state": {
    title: "Refiner · Kiểm tra SQL",
    purpose:
      "Chạy thử SQL trên SQLite. Với Spider, chỉ gọi LLM sửa khi thực thi lỗi; kết quả rỗng hoặc NULL không tự kích hoạt sửa. SQL sửa quay lại bước chạy thử, tối đa 3 lượt Refiner. Chỉ SQL đã chạy thành công mới được chuyển sang đánh giá với gold SQL. Hết lượt mà chưa kiểm tra được SQL sửa thì dừng, không chấm gold.",
  },
}

export type StageSpec = {
  stage: string
  title: string
  lane: number
  column: number
}
export const evaluationNodeTitle = "Đánh giá SQL (bổ sung)"
export const evaluationFrameTitle = "HỆ THỐNG ĐÁNH GIÁ BỔ SUNG"
export const evaluationDescription =
  "Bước do hệ thống thực nghiệm thêm, không thuộc luồng xử lý gốc của phương pháp: thực thi SQL và đối chiếu toàn bộ kết quả với gold SQL bằng SQLite EX khi có đáp án tham chiếu."
export const laneTitles: Record<Method, string[]> = {
  dail_sql: ["ĐIỀU PHỐI", "DỮ LIỆU & VÍ DỤ", "LLM", "SQLITE / ĐÁNH GIÁ"],
  din_sql: ["ĐIỀU PHỐI", "SCHEMA & PHÂN LOẠI", "LLM", "SQLITE / ĐÁNH GIÁ"],
  mac_sql: ["ĐIỀU PHỐI", "CHỌN SCHEMA", "SINH SQL", "SQLITE / ĐÁNH GIÁ"],
  codex_mcp: [
    "ĐIỀU PHỐI",
    "KHÁM PHÁ SCHEMA",
    "PHIÊN AGENT CODEX",
    "CHẠY THỬ / ĐÁNH GIÁ",
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
    spec(
      "Example selection · pass 1",
      "Lượt 1 · Chọn ví dụ & ghép prompt",
      1,
      1,
    ),
    spec("SQL generation · pass 1", "Lượt 1 · Sinh SQL sơ bộ", 2, 1),
    spec(
      "Example selection · pass 2",
      "Lượt 2 · Chọn lại ví dụ & ghép prompt",
      1,
      2,
    ),
    spec("SQL generation · pass 2", "Lượt 2 · Sinh SQL cuối", 2, 2),
    spec("SQLite execution", evaluationNodeTitle, 3, 3),
  ],
  din_sql: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Schema linking", "Liên kết schema", 1, 0),
    spec("Classification", "Phân loại & chọn nhánh", 1, 1),
    spec("SQL generation", "Sinh SQL", 2, 2),
    spec("Self-correction", "LLM tự kiểm tra · 1 lần", 2, 3),
    spec("SQLite execution", evaluationNodeTitle, 3, 3),
  ],
  mac_sql: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Selector · state", macAgents["Selector · state"].title, 1, 0),
    spec("Decomposer · state", macAgents["Decomposer · state"].title, 2, 1),
    spec("Refiner · state", macAgents["Refiner · state"].title, 3, 2),
    spec("SQLite execution", evaluationNodeTitle, 3, 3),
  ],
  codex_mcp: [
    spec("Input", "Câu hỏi đầu vào", 0, 0),
    spec("Codex turn", "Codex · Prompt & SQL", 2, 0),
    spec("search_objects", "MCP · Khám phá schema", 1, 1),
    spec("execute_sql", "MCP · Chạy thử SQL", 3, 2),
    spec("SQLite execution", evaluationNodeTitle, 3, 3),
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
    [
      "Selector",
      "Decomposer",
      "Refiner",
      "Connection check",
      "Refiner · execution",
    ].includes(stage)
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
  const cleaned = value
    .trim()
    .replace(/^SQL\s*:\s*/i, "")
    .replace(/^`([^`]+)`$/, "$1")
  if (/^(SELECT|WITH)\b/i.test(cleaned)) return cleaned
  return undefined
}
export type TableResult = {
  columns: string[]
  rows: unknown[][]
  truncated?: boolean
  truncated_cells?: boolean
  evaluation?: { correct: boolean; metric: string; gold_sql?: string }
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
  const executionInput =
    step.stage === "SQLite execution"
      ? {
          sql: typeof step.input === "string" ? step.input : input?.sql,
          // Saved traces used to store only the predicted SQL in the input.
          gold_sql:
            input?.gold_sql ?? record(output?.evaluation)?.gold_sql ?? null,
        }
      : undefined
  const nextInvocation = steps.find(
    (s) => s.stage === step.stage && s.time > step.time,
  )
  const endTime = Math.min(
    step.endTime ?? Infinity,
    nextInvocation?.time ?? Infinity,
  )
  const child =
    step.calls?.[0] ??
    (step.stage.startsWith("SQL generation · pass ")
      ? steps.find(
          (s) =>
            s.stage === step.stage.replace("SQL generation", "LLM response") &&
            s.time >= step.time &&
            s.time < endTime,
        )
      : undefined)
  const childInput = record(child?.input)
  const prompt =
    typeof input?.prompt === "string"
      ? input.prompt
      : typeof output?.prompt === "string"
        ? output.prompt
        : typeof childInput?.prompt === "string"
          ? childInput.prompt
          : typeof child?.input === "string"
            ? child.input
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
  const sql = executionInput
    ? undefined
    : typeof output?.sql === "string"
      ? output.sql
      : (sqlText(step.output) ??
        sqlText(output?.pred) ??
        sqlText(output?.sql) ??
        sqlText(output?.final_sql) ??
        sqlText(record(finalResponse)?.sql) ??
        sqlText(finalResponse) ??
        sqlText(input?.sql) ??
        sqlText(step.input))
  const examples = Array.isArray(output?.examples) ? output.examples : undefined
  const response = output?.response
  return {
    prompt,
    sql,
    executionInput,
    table: tableResult(step.output),
    examples,
    response:
      typeof response === "string"
        ? response
        : Array.isArray(response)
          ? response.join("\n\n")
          : undefined,
    promptSource:
      child &&
      (typeof child.input === "string" ||
        typeof childInput?.prompt === "string")
        ? child.stage
        : step.stage,
  }
}

export function classification(steps: Step[]) {
  const latest = [...steps]
    .reverse()
    .find((s) => s.stage === "Classification" && s.status === "done")
  const label = record(latest?.output)?.label
  if (
    typeof label === "string" &&
    ["EASY", "NON-NESTED", "NESTED"].includes(label)
  )
    return label
  const response =
    typeof latest?.output === "string"
      ? latest.output
      : record(latest?.output)?.response
  return typeof response === "string"
    ? response
        .match(/Label\s*:\s*["']?(NON-NESTED|NESTED|EASY)\b/i)?.[1]
        ?.toUpperCase()
    : undefined
}

/** Context recorded by the runner; legacy traces use only preceding successful records. */
export function methodContext(step: Step, steps: Step[]) {
  const method = step.id.split("-")[0]
  const prior = steps.filter(
    (s) =>
      s.id.startsWith(`${method}-`) &&
      s.time < step.time &&
      (s.endTime ?? s.time) <= step.time,
  )
  const previous = (stage: string) =>
    [...prior].reverse().find((s) => s.stage === stage && s.status === "done")
  const input = record(step.input)
  const output = record(step.output)
  const source = previous("Input")
  const question = record(source?.output) ?? record(source?.input)
  const schema = previous("Schema linking")
  const selection = previous(
    step.stage.replace("SQL generation", "Example selection"),
  )
  const preliminary = previous("SQL generation · pass 1")
  const candidate = previous("SQL generation")
  const schemaResponse =
    typeof schema?.output === "string"
      ? schema.output
      : record(schema?.output)?.response
  const details = stepDetails(step, steps)
  const args = Array.isArray(input?.arguments) ? input.arguments : []
  const option = (name: string) => {
    const index = args.indexOf(name)
    return index >= 0 ? args[index + 1] : undefined
  }
  return {
    question: input?.question ?? question?.question,
    db_id: input?.db_id ?? question?.db_id,
    schema_links:
      input?.schema_links ??
      record(schema?.output)?.schema_links ??
      (typeof schemaResponse === "string"
        ? schemaResponse.split("Schema_links: ")[1]
        : undefined),
    branch: input?.branch ?? classification(prior),
    sql_before:
      input?.sql ??
      (step.stage === "Self-correction"
        ? details.prompt?.match(
            /#### SQLite SQL QUERY\n([\s\S]*?)\n#### SQLite FIXED SQL QUERY/,
          )?.[1]
        : undefined) ??
      (candidate ? stepDetails(candidate, steps).sql : undefined),
    preliminary_sql:
      input?.preliminary_sql ??
      (preliminary ? stepDetails(preliminary, steps).sql : undefined),
    selection: record(selection?.output),
    label: classification([step]),
    selector: input?.selector ?? option("--selector_type"),
    k_shot: input?.k_shot ?? option("--k_shot"),
    schema_output:
      output?.schema_links ??
      (typeof step.output === "string"
        ? step.output.split("Schema_links: ")[1]
        : undefined),
    ...details,
  }
}
