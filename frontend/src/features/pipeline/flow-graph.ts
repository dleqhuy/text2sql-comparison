import type { Edge, MarkerType, Node } from "@xyflow/react"
import {
  blueprints,
  classification,
  laneTitles,
  stageSpec,
  stepDetails,
  type Method,
  type Step,
} from "./flow-model.ts"

export type TaskData = {
  title: string
  subtitle: string
  stage: string
  status: string
  stepIndex?: number
  attempt?: number
  elapsed?: number
  gateway?: boolean
  branch?: string
}
export type Task = Node<TaskData, "task">
export type Lane = Node<{ title: string }, "lane">
export type FlowNode = Task | Lane

function preview(step: Step, steps: Step[]) {
  const details = stepDetails(step, steps)
  if (step.status === "error")
    return typeof step.output === "string"
      ? step.output
      : "Mở bản ghi để xem lỗi"
  if (details.table)
    return `${details.table.rows.length} dòng hiển thị${details.table.truncated ? " · đã cắt bớt" : ""}${details.table.evaluation ? (details.table.evaluation.correct ? " · EX khớp" : " · EX không khớp") : ""}`
  if (details.examples)
    return `${details.examples.length} ví dụ được chọn · bấm xem prompt`
  if (details.sql) return details.sql
  if (details.response) return details.response
  return step.status === "running"
    ? "Đang chờ phản hồi thực tế…"
    : "Bấm để xem input và output"
}

export function createFlow(method: Method, steps: Step[], selectedId?: string) {
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
        subtitle: "Bước dự kiến của phương pháp",
        status: "planned",
      },
      expected.lane,
      expected.column,
    )
  }
  if (method === "din_sql") {
    const index = steps.map((s) => s.stage).lastIndexOf("Classification")
    place(
      "classification-gateway",
      {
        title: "Chọn nhánh prompt",
        subtitle: classification(steps)
          ? `Label ghi trong trace: ${classification(steps)}`
          : "Chờ nhãn phân loại trong trace",
        stage: "Classification gateway",
        status: classification(steps) ? "done" : "planned",
        gateway: true,
        branch: classification(steps),
        stepIndex: index >= 0 ? index : undefined,
      },
      2,
      1,
    )
  }
  const columns = Math.max(4, ...placements.map((p) => p.column + 1))
  const laneHeights = laneTitles[method].map((_, lane) =>
    Math.max(
      205,
      method === "din_sql" && lane === 2 ? 250 : 0,
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
      width: columns * 245 + 70,
      height: laneHeights[lane],
      style: { width: columns * 245 + 70, height: laneHeights[lane] },
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
      position: { x: 35 + p.column * 245, y: 55 + p.offset * 132 },
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
      label: label ?? (backwards && !planned ? "Quay lại" : undefined),
      animated: !planned && b.data.status === "running",
      style: {
        stroke: planned
          ? "#c6cfc2"
          : b.data.status === "error"
            ? "#c36a54"
            : "#6a8560",
        strokeWidth: planned ? 1.3 : 2,
        ...(planned ? { strokeDasharray: "5 5" } : {}),
      },
      markerEnd: {
        type: "arrowclosed" as MarkerType,
        color: planned ? "#c6cfc2" : "#6a8560",
      },
      labelStyle: { fontSize: 11, fill: "#617354" },
      labelBgStyle: { fill: "#fff" },
      labelBgPadding: [5, 3],
    })
  }
  steps.slice(1).forEach((step, i) => {
    const previous = steps[i]
    if (
      method === "din_sql" &&
      previous.stage === "Classification" &&
      step.stage === "SQL generation"
    ) {
      connect(previous.id, "classification-gateway")
      connect("classification-gateway", step.id, false, classification(steps))
    } else connect(previous.id, step.id)
  })
  const blueprint = blueprints[method]
  blueprint.slice(1).forEach((current, i) => {
    const source = anchors.get(blueprint[i].stage)!,
      target = anchors.get(current.stage)!
    if (method === "din_sql" && current.stage === "SQL generation") return
    if (source.startsWith("planned-") || target.startsWith("planned-"))
      connect(source, target, true)
  })
  if (method === "din_sql") {
    const source = anchors.get("Classification")!,
      target = anchors.get("SQL generation")!
    if (!edges.some((e) => e.target === "classification-gateway"))
      connect(source, "classification-gateway", source.startsWith("planned-"))
    if (!edges.some((e) => e.source === "classification-gateway"))
      connect(
        "classification-gateway",
        target,
        target.startsWith("planned-"),
        classification(steps),
      )
  }
  return { nodes, edges }
}
