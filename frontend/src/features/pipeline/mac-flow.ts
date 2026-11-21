import type { Edge } from "@xyflow/react"
import type { FlowNode, TaskData } from "./flow-graph.ts"
import { record, type Step, stageSpec } from "./flow-model.ts"
import { refinerOutcome } from "./mac-model.ts"

export function createMacFlow(
  steps: Step[],
  selectedId: string | undefined,
  preview: (s: Step, all: Step[]) => string,
) {
  const nodes: FlowNode[] = [],
    edges: Edge[] = []
  const root = "lane-mac",
    loop = "mac-refiner-loop"
  const indices = new Map(steps.map((s, i) => [s.id, i]))
  function task(
    step: Step | undefined,
    stage: string,
    parentId: string,
    x: number,
    y: number,
    title?: string,
    owner?: Step,
  ) {
    const id = step?.id ?? `planned-${stage}-${parentId}`
    const data: TaskData = {
      title: title ?? stageSpec("mac_sql", stage).title,
      stage,
      subtitle:
        step?.stage === "Refiner · execution" &&
        record(step.output)?.sqlite_error
          ? String(record(step.output)?.sqlite_error)
          : step
            ? preview(step, steps).replace(/\s+/g, " ").slice(0, 125)
            : "Chưa có bản ghi · nhánh dự kiến",
      status:
        step?.stage === "Refiner · execution" &&
        record(step.output)?.sqlite_error
          ? "error"
          : (step?.status ?? "planned"),
      stepIndex: step ? indices.get(owner?.id ?? step.id) : undefined,
      detailId: owner ? step?.id : undefined,
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
      ariaLabel: data.title,
    })
    return id
  }
  function connect(
    source: string,
    target: string,
    label: string,
    kind: "control" | "error" | "retry" | "success" | "legacy",
    planned: boolean,
    feedback = false,
  ) {
    const color = planned
      ? "#cfc8c2"
      : kind === "error"
        ? "#b75f4d"
        : kind === "success"
          ? "#3d8065"
          : kind === "retry"
            ? "#367b88"
            : "#857160"
    edges.push({
      id: `${kind}:${source}->${target}`,
      source,
      target,
      label,
      data: { kind },
      sourceHandle: feedback ? "left-out" : "right",
      targetHandle: feedback ? "bottom-in" : "left",
      type: feedback ? "default" : "smoothstep",
      style: {
        stroke: color,
        strokeWidth: planned ? 1.3 : 2,
        ...(planned || kind === "legacy" ? { strokeDasharray: "5 5" } : {}),
      },
      markerEnd: { type: "arrowclosed" as const, color },
      labelStyle: { fontSize: 10, fill: color },
      labelBgStyle: { fill: "#fff" },
      labelBgPadding: [5, 3],
    })
  }
  let previous: string | undefined
  const upstreamStages = ["Input", "Selector · state", "Decomposer · state"]
  // Leave room for transition labels between the 210px task cards.
  const upstreamColumnWidth = 390
  for (const [column, stage] of upstreamStages.entries()) {
    const actual = steps.filter((s) => s.stage === stage)
    for (const [i, step] of (actual.length ? actual : [undefined]).entries()) {
      const id = task(
        step,
        stage,
        root,
        35 + column * upstreamColumnWidth,
        70 + i * 140,
      )
      if (previous)
        connect(
          previous,
          id,
          stage === "Decomposer · state"
            ? "Schema → sinh SQL"
            : "Câu hỏi + database",
          "control",
          !step || previous.startsWith("planned-"),
        )
      previous = id
    }
  }
  const rounds = steps.filter((s) => s.stage === "Refiner · state")
  const entries = rounds.length ? rounds : [undefined]
  // Move the loop below any repeated upstream records rather than overlap them.
  const loopY = Math.max(
    260,
    95 +
      Math.max(
        ...upstreamStages.map(
          (stage) => steps.filter((s) => s.stage === stage).length,
        ),
      ) *
        140,
  )
  const loopHeight = 150 + entries.length * 235
  nodes.push({
    id: loop,
    type: "session",
    parentId: root,
    extent: "parent",
    position: { x: 280, y: loopY },
    width: 1060,
    height: loopHeight,
    style: { width: 1060, height: loopHeight },
    selectable: false,
    focusable: false,
    draggable: false,
    data: {
      title: "REFINER · CHẠY THỬ ↔ SỬA SQL",
      subtitle:
        "SQL lỗi → LLM sửa → chạy lại. SQL đã chạy thành công → đánh giá với gold SQL.",
      status: rounds[rounds.length - 1]?.status ?? "planned",
      footer:
        "Đỏ: lỗi SQLite → sửa · xanh dương: SQL đã sửa → chạy lại · xanh lá: chạy thành công → đánh giá. Tối đa 3 lượt Refiner.",
    },
  })
  const layout: {
    check: string
    repair?: string
    round?: Step
    outcome: string
    y: number
  }[] = []
  for (const [i, round] of entries.entries()) {
    const nested = !!(round?.checks?.length || round?.calls?.length)
    const groupId = nested ? round!.id : `mac-round-${round?.id ?? "planned"}`
    const height = Math.max(
      210,
      75 +
        Math.max(round?.checks?.length ?? 1, round?.calls?.length ?? 1) * 135,
    )
    const y = 105 + layout.reduce((sum, entry) => sum + entry.y, 0)
    const outcome = round ? refinerOutcome(round) : "pending"
    nodes.push({
      id: groupId,
      type: "session",
      parentId: loop,
      extent: "parent",
      position: { x: 15, y },
      width: 1030,
      height,
      style: { width: 1030, height },
      selected: round?.id === selectedId,
      selectable: nested,
      focusable: nested,
      draggable: false,
      data: {
        title: `LƯỢT REFINER ${i + 1}`,
        subtitle:
          outcome === "success"
            ? "SQL đã chạy thành công"
            : outcome === "repair"
              ? "Đã sinh SQL sửa, cần chạy lại"
              : outcome === "unverified"
                ? "Trace chưa có xác nhận chạy thành công"
                : "Xem kết quả chạy SQL và phản hồi sửa lỗi",
        status: round?.status ?? "planned",
        stepIndex: nested ? indices.get(round!.id) : undefined,
        footer: "",
        compact: true,
      },
    })
    const checks = round?.checks?.length ? round.checks : [undefined]
    let checkId = ""
    for (const [j, check] of checks.entries()) {
      checkId = task(
        check ?? (!nested ? round : undefined),
        check?.stage ??
          (round && !nested ? round.stage : "Refiner · execution"),
        groupId,
        25,
        70 + j * 135,
        check
          ? `#${i + 1} · Chạy thử SQL`
          : round && !nested
            ? "Refiner · Trạng thái"
            : "Chạy thử SQL",
        check ? round : undefined,
      )
    }
    let repairId: string | undefined
    for (const [j, call] of (round?.calls ?? []).entries()) {
      repairId = task(
        call,
        "Refiner",
        groupId,
        740,
        70 + j * 135,
        `#${i + 1} · LLM sửa SQL`,
        round,
      )
      const errorCheck = round?.checks?.find(
        (c) => record(c.output)?.sqlite_error || c.status === "error",
      )
      connect(
        errorCheck?.id ?? checkId,
        repairId,
        errorCheck
          ? "SQL lỗi → gửi lỗi & SQL cho LLM"
          : "Có lời gọi sửa trong trace",
        "error",
        !errorCheck,
      )
    }
    if (!round) {
      repairId = task(undefined, "Refiner", groupId, 740, 70, "LLM sửa SQL")
      connect(checkId, repairId, "Nếu SQL lỗi → LLM sửa", "error", true)
    }
    layout.push({
      check: checkId,
      repair: repairId,
      round,
      outcome,
      y: height + 25,
    })
  }
  // Accommodate long traces without clipping nested calls.
  const requiredHeight = 125 + layout.reduce((sum, entry) => sum + entry.y, 0)
  const loopNode = nodes.find((n) => n.id === loop)!
  loopNode.height = requiredHeight
  loopNode.style = { width: 1060, height: requiredHeight }
  if (previous)
    connect(
      previous,
      layout[0].check,
      "SQL ứng viên → Refiner",
      "control",
      !rounds.length || previous.startsWith("planned-"),
    )
  for (const [i, entry] of layout.entries()) {
    const next = layout[i + 1]
    if (entry.repair)
      connect(
        entry.repair,
        next?.check ?? entry.check,
        next ? "SQL đã sửa → chạy lại" : "SQL sửa chưa được chạy lại",
        "retry",
        !next,
        true,
      )
  }
  const last = layout[layout.length - 1]
  const evaluationY =
    loopY +
    105 +
    layout.slice(0, -1).reduce((sum, entry) => sum + entry.y, 0) +
    70
  const evaluations = steps.filter((s) => s.stage === "SQLite execution")
  for (const [i, evaluation] of (evaluations.length
    ? evaluations
    : [undefined]
  ).entries()) {
    const id = task(
      evaluation,
      "SQLite execution",
      root,
      1395,
      evaluationY + i * 140,
    )
    const success = last.outcome === "success"
    connect(
      last.check,
      id,
      success
        ? "Chạy thành công → chấm với gold SQL"
        : evaluation
          ? "Chuyển SQL theo trace · chưa xác nhận chạy thành công"
          : "Chỉ chuyển khi SQL đã chạy thành công",
      success ? "success" : evaluation ? "legacy" : "control",
      !evaluation,
    )
  }
  const other = steps.filter(
    (s) =>
      !upstreamStages.includes(s.stage) &&
      s.stage !== "Refiner · state" &&
      s.stage !== "SQLite execution",
  )
  for (const [i, step] of other.entries()) {
    const id = task(step, step.stage, root, 1395, evaluationY + 150 + i * 140)
    connect(
      last.repair ?? last.check,
      id,
      "Dừng / hết lượt / lỗi",
      "error",
      false,
    )
  }
  const rootHeight = Math.max(
    loopY + requiredHeight + 35,
    ...nodes
      .filter((n) => n.parentId === root)
      .map((n) => n.position.y + (n.height ?? 0) + 40),
  )
  nodes.unshift({
    id: root,
    type: "lane",
    position: { x: 0, y: 0 },
    width: 1660,
    height: rootHeight,
    style: { width: 1660, height: rootHeight },
    data: {
      title: "MAC-SQL · CHỌN SCHEMA → SINH SQL → VÒNG LẶP REFINER → ĐÁNH GIÁ",
    },
    selectable: false,
    focusable: false,
    draggable: false,
  })
  return { nodes, edges }
}
