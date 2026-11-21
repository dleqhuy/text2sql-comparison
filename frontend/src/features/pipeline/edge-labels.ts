import {
  type Edge,
  getBezierPath,
  getSmoothStepPath,
  Position,
} from "@xyflow/react"
import type { FlowNode } from "./flow-graph.ts"

type Box = { x: number; y: number; width: number; height: number }
export type LabelPosition = Box
const overlaps = (a: Box, b: Box, margin = 8) =>
  a.x < b.x + b.width + margin &&
  a.x + a.width + margin > b.x &&
  a.y < b.y + b.height + margin &&
  a.y + a.height + margin > b.y

function labelSize(label: string) {
  const content = [...label].length * 7
  const width = Math.min(200, Math.max(48, content + 18))
  return { width, height: Math.ceil(content / (width - 18)) * 14 + 10 }
}

/** Position labels in graph space, excluding cards, group headings and other labels. */
export function placeEdgeLabels(graph: { nodes: FlowNode[]; edges: Edge[] }) {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]))
  const boxes = new Map<string, Box>()
  function box(id: string): Box {
    const cached = boxes.get(id)
    if (cached) return cached
    const node = byId.get(id)!
    const parent = node.parentId ? box(node.parentId) : { x: 0, y: 0 }
    const result = {
      x: parent.x + node.position.x,
      y: parent.y + node.position.y,
      width: node.width ?? 210,
      height: node.height ?? 114,
    }
    boxes.set(id, result)
    return result
  }
  const blocked: Box[] = []
  for (const node of graph.nodes) {
    const bounds = box(node.id)
    if (node.type === "task") blocked.push(bounds)
    else {
      const text =
        node.type === "lane"
          ? node.data.title
          : `${node.data.title} ${node.data.subtitle}`
      blocked.push({
        ...bounds,
        width: Math.min(bounds.width, text.length * 6 + 44),
        height: node.type === "lane" ? 40 : node.data.compact ? 62 : 95,
      })
      if (node.type === "session" && node.data.footer !== "")
        blocked.push({
          x: bounds.x + 16,
          y: bounds.y + bounds.height - 37,
          width: bounds.width - 32,
          height: 28,
        })
    }
  }
  const maxX = Math.max(...[...boxes.values()].map((b) => b.x + b.width))
  const maxY = Math.max(...[...boxes.values()].map((b) => b.y + b.height))
  const position = (handle: string | null | undefined, source: boolean) =>
    handle?.includes("bottom")
      ? Position.Bottom
      : handle === "top"
        ? Position.Top
        : handle?.includes("left")
          ? Position.Left
          : handle?.includes("right")
            ? Position.Right
            : source
              ? Position.Right
              : Position.Left
  const port = (bounds: Box, side: Position) => ({
    x:
      bounds.x +
      (side === Position.Left
        ? 0
        : side === Position.Right
          ? bounds.width
          : bounds.width / 2),
    y:
      bounds.y +
      (side === Position.Top
        ? 0
        : side === Position.Bottom
          ? bounds.height
          : bounds.height / 2),
  })
  const occupied: Box[] = []
  for (const edge of graph.edges.filter((e) => e.type === "providerRetry")) {
    const target = box(edge.target),
      size = labelSize(String(edge.label))
    occupied.push({
      x: target.x + target.width / 2 - 15 - size.width / 2,
      y: target.y - 40 - size.height / 2,
      ...size,
    })
  }
  const edges = graph.edges.map((edge) => {
    if (!edge.label || edge.type === "providerRetry") return edge
    const sourcePosition = position(edge.sourceHandle, true),
      targetPosition = position(edge.targetHandle, false)
    const source = port(box(edge.source), sourcePosition),
      target = port(box(edge.target), targetPosition)
    const args = {
      sourceX: source.x,
      sourceY: source.y,
      targetX: target.x,
      targetY: target.y,
      sourcePosition,
      targetPosition,
    }
    const [, anchorX, anchorY] =
      edge.type === "default" ? getBezierPath(args) : getSmoothStepPath(args)
    const size = labelSize(String(edge.label))
    const candidates: { x: number; y: number; score: number }[] = []
    for (const dx of [0, -60, 60, -120, 120, -200, 200, -320, 320, -480, 480])
      for (const dy of [
        0, -32, 32, -64, 64, -100, 100, -150, 150, -220, 220, -320, 320,
      ])
        candidates.push({
          x: anchorX + dx - size.width / 2,
          y: anchorY + dy - size.height / 2,
          score: dx * dx + dy * dy,
        })
    candidates.sort((a, b) => a.score - b.score)
    const safe = (candidate: Box) =>
      candidate.x >= 8 &&
      candidate.y >= 8 &&
      candidate.x + candidate.width <= maxX - 8 &&
      candidate.y + candidate.height <= maxY - 8 &&
      !blocked.some((b) => overlaps(candidate, b)) &&
      !occupied.some((b) => overlaps(candidate, b, 6))
    let chosen = candidates.find((c) => safe({ ...c, ...size }))
    if (!chosen) {
      const fallback = []
      for (let y = 48; y < maxY - size.height; y += 32)
        for (let x = 16; x < maxX - size.width; x += 40)
          if (safe({ x, y, ...size }))
            fallback.push({
              x,
              y,
              score:
                (x + size.width / 2 - anchorX) ** 2 +
                (y + size.height / 2 - anchorY) ** 2,
            })
      chosen = fallback.sort((a, b) => a.score - b.score)[0]
    }
    if (!chosen) return edge
    const labelPosition = { x: chosen.x, y: chosen.y, ...size }
    occupied.push(labelPosition)
    return {
      ...edge,
      type: "positionedLabel",
      data: { ...edge.data, pathType: edge.type, labelPosition },
    }
  })
  return { ...graph, edges }
}
