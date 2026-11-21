import type { Edge } from "@xyflow/react"
import { codexContext } from "./codex-model.ts"
import type { FlowNode, TaskData } from "./flow-graph.ts"
import { type Step, stageSpec } from "./flow-model.ts"

/** A session owns its tool invocations; results return to the same agent. */
export function createCodexFlow(
  steps: Step[],
  selectedId: string | undefined,
  preview: (step: Step, steps: Step[]) => string,
) {
  const nodes: FlowNode[] = []
  const edges: Edge[] = []
  const sessions = steps.filter((s) => s.stage === "Codex turn")
  const orphanTools = steps.filter(
    (s) =>
      ["search_objects", "execute_sql"].includes(s.stage) &&
      s.time < (sessions[0]?.time ?? Infinity),
  )
  const groups: (Step | undefined)[] = sessions.length
    ? [...(orphanTools.length ? [undefined] : []), ...sessions]
    : [undefined]
  const indices = new Map(steps.map((s, i) => [s.id, i]))
  const rootId = "lane-codex"
  let top = 65
  const hubs: { id: string; step?: Step; center: number }[] = []

  function task(
    step: Step | undefined,
    stage: string,
    parentId: string,
    x: number,
    y: number,
    title?: string,
  ) {
    const id = step?.id ?? `planned-${stage}-${parentId}`
    const data: TaskData = {
      title: title ?? stageSpec("codex_mcp", stage).title,
      stage,
      subtitle: step
        ? preview(step, steps).replace(/\s+/g, " ").slice(0, 125)
        : "Chưa có bản ghi · luồng dự kiến",
      status: step?.status ?? "planned",
      stepIndex: step ? indices.get(step.id) : undefined,
      attempt: step?.attempt,
      elapsed: step?.elapsed,
    }
    nodes.push({
      id,
      type: "task",
      parentId,
      extent: "parent",
      position: { x, y },
      data,
      width: 210,
      height: 114,
      style: { width: 210, height: 114 },
      selected: id === selectedId,
      draggable: false,
      selectable: !!step,
      focusable: !!step,
      ariaRole: step ? "button" : "group",
      ariaLabel: `${data.title}${step ? ` · lần ${step.attempt}` : " · chưa có trace"}`,
    })
    return id
  }
  function edge(
    source: string,
    target: string,
    label: string,
    kind: "call" | "feedback" | "control",
    planned: boolean,
    error = false,
  ) {
    const feedback = kind === "feedback"
    const color = planned
      ? "#cfc8c2"
      : error
        ? "#b75f4d"
        : feedback
          ? "#367b88"
          : "#857160"
    edges.push({
      id: `${kind}:${source}->${target}`,
      source,
      target,
      sourceHandle: feedback ? "left-out" : "right",
      targetHandle: feedback ? "bottom-in" : "left",
      type: feedback ? "default" : "smoothstep",
      label,
      data: { kind },
      style: {
        stroke: color,
        strokeWidth: planned ? 1.3 : 2,
        ...(planned ? { strokeDasharray: "5 5" } : {}),
      },
      markerEnd: { type: "arrowclosed" as const, color },
      labelStyle: { fontSize: 10, fill: color },
      labelBgStyle: { fill: "#fff" },
      labelBgPadding: [5, 3],
    })
  }

  for (const [index, session] of groups.entries()) {
    const groupId = `codex-session-${session?.id ?? "planned"}`
    const tools = session ? codexContext(session, steps).tools : orphanTools
    const entries: { step?: Step; stage: string }[] = tools.map((step) => ({
      step,
      stage: step.stage,
    }))
    for (const stage of ["search_objects", "execute_sql"])
      if (!tools.some((s) => s.stage === stage)) entries.push({ stage })
    const height = 155 + entries.length * 170
    const hubY = 115 + (entries.length - 1) * 85
    nodes.push({
      id: groupId,
      type: "session",
      parentId: rootId,
      extent: "parent",
      position: { x: 300, y: top },
      width: 820,
      height,
      style: { width: 820, height },
      selectable: false,
      focusable: false,
      draggable: false,
      data: {
        title: `PHIÊN CODEX MCP SQL${groups.length > 1 ? ` · ${index + 1}` : ""}`,
        subtitle:
          "Agent gọi tool → nhận schema / kết quả / lỗi → chọn bước tiếp theo hoặc chốt SQL.",
        status: session?.status ?? "planned",
      },
    })
    const hub = task(
      session,
      "Codex turn",
      groupId,
      35,
      hubY,
      "Codex · Điều phối & SQL",
    )
    hubs.push({ id: hub, step: session, center: top + hubY })
    for (const [i, entry] of entries.entries()) {
      const number = entry.step ? tools.indexOf(entry.step) + 1 : undefined
      const tool = task(
        entry.step,
        entry.stage,
        groupId,
        535,
        115 + i * 170,
        `${number ? `#${number} · ` : ""}${entry.stage === "search_objects" ? "Khám phá schema" : "Chạy thử SQL"}`,
      )
      const planned = !session || !entry.step
      edge(
        hub,
        tool,
        `${number ? `#${number} · ` : ""}Gọi ${entry.stage}`,
        "call",
        planned,
      )
      if (!entry.step || ["done", "error"].includes(entry.step.status))
        edge(
          tool,
          hub,
          `${number ? `#${number} · ` : ""}${entry.step?.status === "error" ? "Lỗi → agent" : entry.stage === "search_objects" ? "Schema → agent" : "Kết quả → agent"}`,
          "feedback",
          planned,
          entry.step?.status === "error",
        )
    }
    top += height + 40
  }

  const inputs = steps.filter((s) => s.stage === "Input")
  const inputEntries = inputs.length ? inputs : [undefined]
  for (const [i, input] of inputEntries.entries()) {
    const id = task(input, "Input", rootId, 35, hubs[0].center + i * 145)
    edge(
      id,
      hubs[0].id,
      "Câu hỏi + database",
      "control",
      !input || !hubs[0].step,
    )
  }
  for (let i = 1; i < hubs.length; i++)
    edge(hubs[i - 1].id, hubs[i].id, "Phiên tiếp theo", "control", false)
  const last = hubs[hubs.length - 1]
  const outside = steps.filter(
    (s) =>
      !["Input", "Codex turn", "search_objects", "execute_sql"].includes(
        s.stage,
      ),
  )
  if (!outside.some((s) => s.stage === "SQLite execution")) {
    const id = task(undefined, "SQLite execution", rootId, 1180, last.center)
    edge(last.id, id, "Khi runner chấp nhận SQL", "control", true)
  }
  for (const [i, step] of outside.entries()) {
    const offset = outside.some((s) => s.stage === "SQLite execution")
      ? i
      : i + 1
    const id = task(step, step.stage, rootId, 1180, last.center + offset * 145)
    edge(
      last.id,
      id,
      step.stage === "SQLite execution"
        ? "SQL được chấp nhận → chấm EX"
        : "Trạng thái kết thúc",
      "control",
      !last.step,
      step.status === "error",
    )
  }
  const height = Math.max(
    top + 15,
    ...nodes
      .filter((n) => n.parentId === rootId)
      .map((n) => n.position.y + (n.height ?? 0) + 30),
  )
  nodes.unshift({
    id: rootId,
    type: "lane",
    position: { x: 0, y: 0 },
    width: 1430,
    height,
    style: { width: 1430, height },
    data: { title: "ĐẦU VÀO → PHIÊN AGENT VÀ VÒNG LẶP MCP → ĐÁNH GIÁ" },
    selectable: false,
    focusable: false,
    draggable: false,
  })
  return { nodes, edges }
}
