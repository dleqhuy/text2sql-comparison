import type { Edge } from "@xyflow/react"
import type { FlowNode, Session, Task } from "./flow-graph.ts"
import { evaluationFrameTitle, evaluationNodeTitle } from "./flow-model.ts"

/** Keep the evaluator outside agent/refiner groups, including planned and error nodes. */
export function separateEvaluation(graph: {
  nodes: FlowNode[]
  edges: Edge[]
}) {
  const nodes = graph.nodes.map((n) => ({
    ...n,
    position: { ...n.position },
    data: { ...n.data },
    style: { ...n.style },
  })) as FlowNode[]
  const evaluations = nodes.filter(
    (n): n is Task => n.type === "task" && n.data.stage === "SQLite execution",
  )
  if (!evaluations.length) return graph
  const parentId = evaluations[0].parentId
  const parent = nodes.find((n) => n.id === parentId)
  const dedicated =
    parent?.type === "lane" &&
    nodes
      .filter((n) => n.parentId === parentId)
      .every((n) => n.type === "task" && n.data.stage === "SQLite execution")
  const data: Session["data"] = {
    title: evaluationFrameTitle,
    subtitle:
      "Bước bổ sung của hệ thống thực nghiệm; không thuộc phương pháp gốc.",
    status: evaluations.some((n) => n.data.status === "running")
      ? "running"
      : evaluations.every((n) => n.data.status === "planned")
        ? "planned"
        : "done",
    supplemental: true,
    footer: "",
  }
  let frame: Session
  if (dedicated) {
    frame = {
      ...parent,
      type: "session",
      data,
      height: (parent.height ?? 205) + 65,
    } as Session
    for (const node of evaluations) node.position.y += 65
    nodes[nodes.findIndex((n) => n.id === parent.id)] = frame
  } else {
    const x = Math.min(...evaluations.map((n) => n.position.x)) - 25
    const y = Math.max(
      55,
      Math.min(...evaluations.map((n) => n.position.y)) - 110,
    )
    frame = {
      id: "supplemental-evaluation",
      type: "session",
      parentId,
      extent: "parent",
      position: { x, y },
      width: 350,
      height: 254,
      style: { width: 350, height: 254 },
      data,
      selectable: false,
      focusable: false,
      draggable: false,
    }
    for (const node of evaluations) {
      node.parentId = frame.id
      node.position = { x: node.position.x - x, y: node.position.y - y }
    }
    nodes.splice(
      nodes.findIndex((n) => n.id === evaluations[0].id),
      0,
      frame,
    )
  }
  frame.height = Math.max(
    frame.height ?? 0,
    ...evaluations.map((n) => n.position.y + (n.height ?? 114) + 30),
  )
  frame.style = { ...frame.style, height: frame.height }
  for (const node of evaluations)
    if (node.type === "task") {
      node.data.title = evaluationNodeTitle
      node.ariaLabel = `${evaluationNodeTitle}${node.data.status === "planned" ? " · chưa có trace" : ""}`
    }
  let child: FlowNode | undefined = frame
  while (child?.parentId) {
    const ancestor = nodes.find((n) => n.id === child!.parentId)
    if (!ancestor) break
    ancestor.width = Math.max(
      ancestor.width ?? 0,
      child.position.x + (child.width ?? 0) + 30,
    )
    ancestor.height = Math.max(
      ancestor.height ?? 0,
      child.position.y + (child.height ?? 0) + 30,
    )
    ancestor.style = {
      ...ancestor.style,
      width: ancestor.width,
      height: ancestor.height,
    }
    child = ancestor
  }
  return { nodes, edges: graph.edges }
}
