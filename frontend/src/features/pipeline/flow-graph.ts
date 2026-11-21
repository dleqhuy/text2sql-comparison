import type { Edge, MarkerType, Node } from "@xyflow/react"
import {
  blueprints,
  classification,
  laneTitles,
  macAgents,
  record,
  stageSpec,
  stepDetails,
  type Method,
  type Step,
} from "./flow-model.ts"
import { describeStep, methodStages } from "./method-stages.ts"
import { createCodexFlow } from "./codex-flow.ts"
import { createMacFlow } from "./mac-flow.ts"
import { placeEdgeLabels } from "./edge-labels.ts"
import { separateEvaluation } from "./evaluation-frame.ts"

export type TaskData = {
  title: string
  subtitle: string
  stage: string
  status: string
  stepIndex?: number
  detailId?: string
  attempt?: number
  elapsed?: number
  llmAttempts?: number
  gateway?: boolean
  branch?: string
}
export type Task = Node<TaskData, "task">
export type Lane = Node<{ title: string }, "lane">
export type Session = Node<
  {
    title: string
    subtitle: string
    status: string
    stepIndex?: number
    footer?: string
    compact?: boolean
    supplemental?: boolean
  },
  "session"
>
export type FlowNode = Task | Lane | Session

function preview(step: Step, steps: Step[]) {
  const details = stepDetails(step, steps)
  if (step.status === "error")
    return typeof step.output === "string"
      ? step.output
      : "Mở bản ghi để xem lỗi"
  if (macAgents[step.stage]) {
    const output = record(step.output)
    if (step.stage === "Selector · state")
      return step.status === "running"
        ? "Đang chuẩn bị schema…"
        : step.calls?.length
          ? "Đã gọi LLM chọn schema · mở xem prompt"
          : output?.pruned === false
            ? "Giữ schema · không gọi LLM"
            : "Mở xem schema và trạng thái"
    if (step.stage === "Refiner · state")
      return step.status === "running"
        ? "Đang chạy thử / sửa SQL…"
        : output?.send_to === "Refiner"
          ? "Đã sinh SQL sửa · cần chạy thử lại"
          : "Kết thúc kiểm tra · chưa đối chiếu gold SQL"
  }
  if (details.table)
    return `${details.table.rows.length} dòng hiển thị${details.table.truncated ? " · đã cắt bớt" : ""}${details.table.evaluation ? (details.table.evaluation.correct ? " · EX khớp" : " · EX không khớp") : ""}`
  if (
    step.stage === "search_objects" &&
    Array.isArray(record(step.output)?.objects)
  ) {
    const output = record(step.output)!
    return `${(output.objects as unknown[]).length} đối tượng · tổng ${output.total}${output.has_more ? " · còn trang tiếp" : ""}`
  }
  if (step.stage === "Codex turn")
    return step.status === "running"
      ? "Agent đang khám phá schema / thử SQL / chờ xác nhận…"
      : record(step.output)?.audit_verified === true
        ? "SQL đã được runner chấp nhận · chưa chấm EX"
        : "Mở xem SQL trả về và trạng thái phiên"
  if (step.stage === "Classification")
    return classification([step])
      ? `${classification([step])} · chọn prompt sinh SQL tương ứng`
      : step.status === "running"
        ? "Đang phân loại câu hỏi…"
        : "Mở xem phản hồi phân loại; chưa có nhãn rõ ràng"
  if (details.examples)
    return `${details.examples.length} ví dụ được chọn · bấm xem prompt`
  if (details.sql) return details.sql
  if (details.response) return details.response
  return step.status === "running"
    ? "Đang chờ phản hồi thực tế…"
    : (describeStep(step)?.output ?? "Bấm để xem input và output")
}

export function createFlow(method: Method, steps: Step[], selectedId?: string) {
  if (method === "codex_mcp")
    return placeEdgeLabels(
      separateEvaluation(createCodexFlow(steps, selectedId, preview)),
    )
  if (method === "mac_sql")
    return placeEdgeLabels(
      separateEvaluation(createMacFlow(steps, selectedId, preview)),
    )
  const bins = new Map<string, number>()
  const placements: {
    id: string
    data: TaskData
    lane: number
    column: number
    offset: number
  }[] = []
  function place(id: string, data: TaskData, lane: number, column: number) {
    const key = `${lane}-${column}`,
      offset = bins.get(key) ?? 0
    bins.set(key, offset + 1)
    placements.push({ id, data, lane, column, offset })
  }
  steps.forEach((step, i) => {
    const location = stageSpec(method, step.stage)
    place(
      step.id,
      {
        title: location.title,
        stage: step.stage,
        subtitle: preview(step, steps).replace(/\s+/g, " ").slice(0, 125),
        status: step.status,
        stepIndex: i,
        attempt: step.attempt,
        elapsed: step.elapsed,
        llmAttempts: step.calls?.length,
        branch:
          step.stage === "Classification" ? classification([step]) : undefined,
      },
      location.lane,
      location.column,
    )
  })
  const anchors = new Map<string, string>()
  for (const step of steps)
    if (!anchors.has(step.stage)) anchors.set(step.stage, step.id)
  for (const expected of blueprints[method]) {
    if (anchors.has(expected.stage)) continue
    const id = `planned-${expected.stage}`
    anchors.set(expected.stage, id)
    place(
      id,
      {
        title: expected.title,
        stage: expected.stage,
        subtitle:
          macAgents[expected.stage]?.purpose ??
          methodStages[method]?.[expected.stage]?.purpose ??
          "Bước dự kiến của phương pháp",
        status: "planned",
      },
      expected.lane,
      expected.column,
    )
  }
  const columns = Math.max(4, ...placements.map((p) => p.column + 1))
  const columnWidth = 390
  const laneHeights = laneTitles[method].map((_, lane) =>
    Math.max(
      205,
      ...[...bins.entries()]
        .filter(([key]) => +key.split("-")[0] === lane)
        .map(([, count]) => count * 132 + 65),
    ),
  )
  let top = 0
  const nodes: FlowNode[] = laneTitles[method].map((title, lane) => {
    const node: Lane = {
      id: `lane-${lane}`,
      type: "lane",
      data: { title },
      position: { x: 0, y: top },
      width: columns * columnWidth + 70,
      height: laneHeights[lane],
      style: { width: columns * columnWidth + 70, height: laneHeights[lane] },
      selectable: false,
      focusable: false,
      draggable: false,
    }
    top += laneHeights[lane]
    return node
  })
  for (const p of placements)
    nodes.push({
      id: p.id,
      type: "task",
      parentId: `lane-${p.lane}`,
      extent: "parent",
      position: { x: 35 + p.column * columnWidth, y: 55 + p.offset * 132 },
      data: p.data,
      width: 210,
      height: p.data.gateway ? 172 : 114,
      style: { width: 210, height: p.data.gateway ? 172 : 114 },
      selected: p.id === selectedId,
      draggable: false,
      selectable: p.data.stepIndex !== undefined,
      focusable: p.data.stepIndex !== undefined,
      ariaRole: p.data.stepIndex !== undefined ? "button" : "group",
      ariaLabel: `${p.data.title}${p.data.attempt ? ` · lần ${p.data.attempt}` : ""}${p.data.status === "planned" ? " · chưa có trace" : ""}`,
    })
  const edges: Edge[] = []
  function connect(
    source: string,
    target: string,
    planned = false,
    label?: string,
    kind = "forward",
  ) {
    const a = placements.find((p) => p.id === source),
      b = placements.find((p) => p.id === target)
    if (!a || !b) return
    const same = a.column === b.column,
      backwards = b.column < a.column
    edges.push({
      id: `${source}->${target}`,
      source,
      target,
      sourceHandle: same ? "bottom" : backwards ? "left-out" : "right",
      targetHandle: same ? "top" : backwards ? "right-in" : "left",
      type: "smoothstep",
      label,
      data: { kind },
      animated: !planned && b.data.status === "running",
      style: {
        stroke: planned
          ? "#cfc8c2"
          : b.data.status === "error"
            ? "#c36a54"
            : "#857160",
        strokeWidth: planned ? 1.3 : 2,
        ...(planned ? { strokeDasharray: "5 5" } : {}),
      },
      markerEnd: {
        type: "arrowclosed" as MarkerType,
        color: planned ? "#cfc8c2" : "#857160",
      },
      labelStyle: { fontSize: 11, fill: "#736254" },
      labelBgStyle: { fill: "#fff" },
      labelBgPadding: [5, 3],
    })
  }
  function transition(previous: string, current: string, step?: Step) {
    if (current === "Run failed")
      return { label: "Dừng do lỗi", kind: "failure" }
    if (method === "din_sql") {
      if (previous === "Schema linking" && current === "Classification")
        return { label: "Schema links", kind: "forward" }
      if (previous === "Classification" && current === "SQL generation")
        return {
          label: step ? classification([step]) : "Theo nhãn phân loại",
          kind: "branch",
        }
      if (previous === "SQL generation" && current === "Self-correction")
        return { label: "SQL ứng viên · chưa thực thi", kind: "forward" }
      if (previous === "Self-correction" && current === "SQLite execution")
        return { label: "SQL sau tự kiểm tra → chấm gold", kind: "evaluation" }
    }
    if (method === "dail_sql") {
      if (
        previous === "SQL generation · pass 1" &&
        current === "Example selection · pass 2"
      )
        return {
          label: "SQL sơ bộ → chọn lại ví dụ (lượt 2)",
          kind: "data-dependency",
        }
      if (
        previous.startsWith("Example selection") &&
        current.startsWith("SQL generation")
      )
        return {
          label: `Prompt đã ghép · lượt ${current.endsWith("1") ? 1 : 2}`,
          kind: "forward",
        }
      if (
        previous === "SQL generation · pass 2" &&
        current === "SQLite execution"
      )
        return { label: "SQL lượt 2 → chấm gold", kind: "evaluation" }
    }
    return { label: undefined, kind: "forward" }
  }
  steps.slice(1).forEach((step, i) => {
    const previous = steps[i]
    const link = transition(previous.stage, step.stage, previous)
    connect(previous.id, step.id, false, link.label, link.kind)
  })
  const blueprint = blueprints[method]
  blueprint.slice(1).forEach((current, i) => {
    const source = anchors.get(blueprint[i].stage)!,
      target = anchors.get(current.stage)!
    if (source.startsWith("planned-") || target.startsWith("planned-")) {
      const link = transition(blueprint[i].stage, current.stage)
      connect(source, target, true, link.label, link.kind)
    }
  })
  for (const step of steps) {
    const calls = step.calls ?? []
    if (!calls.slice(0, -1).some((c) => c.status === "error")) continue
    edges.push({
      id: `provider-retry:${step.id}`,
      source: step.id,
      target: step.id,
      sourceHandle: "left-out",
      targetHandle: "top",
      type: "providerRetry",
      label: `Retry gọi LLM · ${calls.length}/3 lần`,
      data: { kind: "provider-retry" },
      animated: step.status === "running",
      style: { stroke: "#367b88", strokeWidth: 2 },
      markerEnd: { type: "arrowclosed" as MarkerType, color: "#367b88" },
      labelStyle: { fontSize: 10, fill: "#367b88" },
      labelBgStyle: { fill: "#fff" },
      labelBgPadding: [5, 3],
    })
  }
  return placeEdgeLabels(separateEvaluation({ nodes, edges }))
}
