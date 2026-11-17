import {
  Background,
  Controls,
  type Edge,
  Handle,
  MarkerType,
  MiniMap,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from "@xyflow/react"
import { Database } from "lucide-react"
import { useMemo } from "react"
import type { SchemaObject } from "@/client"
import "@xyflow/react/dist/style.css"
import "./schema.css?versioned"

type TableNode = Node<{ table: SchemaObject }, "schemaTable">
function TableCard({ data }: NodeProps<TableNode>) {
  const { table } = data
  return (
    <div className="erd-table">
      <h3>
        <Database size={15} />
        {table.name}
      </h3>
      {table.columns.map((column, index) => {
        const foreign = table.foreign_keys.some(
          (key) => key.column === column.name,
        )
        return (
          <div
            className="erd-column"
            key={column.name}
            title={`${column.name} · ${column.type || "untyped"}${column.not_null ? " · NOT NULL" : ""}`}
          >
            <Handle
              type="target"
              position={Position.Left}
              id={`in-${index}`}
              isConnectable={false}
            />
            <span className="erd-key">
              {column.primary_key ? "PK" : ""}
              {column.primary_key && foreign ? "/" : ""}
              {foreign ? "FK" : ""}
            </span>
            <span className="erd-column-name">{column.name}</span>
            <span className="erd-type">{column.type || "—"}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={`out-${index}`}
              isConnectable={false}
            />
          </div>
        )
      })}
    </div>
  )
}
const nodeTypes = { schemaTable: TableCard }

export default function SchemaDiagram({
  schema,
  database,
  loading,
  error,
  onRetry,
}: {
  schema: SchemaObject[]
  database: string
  loading: boolean
  error: string
  onRetry: () => void
}) {
  const { nodes, edges } = useMemo(() => {
    const incoming = new Map<string, SchemaObject[]>()
    for (const table of schema) {
      for (const key of table.foreign_keys) {
        if (key.target_table.toLowerCase() === table.name.toLowerCase())
          continue
        const name = key.target_table.toLowerCase()
        incoming.set(name, [...(incoming.get(name) ?? []), table])
      }
    }
    const depths = new Map<string, number>()
    function depth(table: SchemaObject, visiting = new Set<string>()): number {
      if (visiting.has(table.name)) return 0
      const cached = depths.get(table.name)
      if (cached !== undefined) return cached
      const next = new Set(visiting).add(table.name)
      const targets = incoming.get(table.name.toLowerCase()) ?? []
      const value = targets.length
        ? 1 + Math.max(...targets.map((target) => depth(target, next)))
        : 0
      depths.set(table.name, value)
      return value
    }
    const maxDepth = Math.max(0, ...schema.map((table) => depth(table)))
    const heights = new Map<number, number>()
    const nodes: TableNode[] = schema.map((table, index) => {
      const lane = maxDepth ? (depths.get(table.name) ?? 0) : index % 3
      const y = heights.get(lane) ?? 0
      heights.set(lane, y + 48 + table.columns.length * 30 + 100)
      return {
        id: table.name,
        type: "schemaTable",
        position: { x: lane * 460, y },
        data: { table },
      }
    })
    const edges: Edge[] = schema.flatMap((table) =>
      table.foreign_keys.flatMap((key) => {
        const target = schema.find(
          (other) =>
            other.name.toLowerCase() === key.target_table.toLowerCase(),
        )
        const sourceColumn = table.columns.findIndex(
          (column) => column.name.toLowerCase() === key.column.toLowerCase(),
        )
        const targetColumn =
          target?.columns.findIndex(
            (column) =>
              column.name.toLowerCase() === key.target_column?.toLowerCase(),
          ) ?? -1
        if (!target || sourceColumn < 0 || targetColumn < 0) return []
        return [
          {
            id: `${table.name}-${key.id}-${key.sequence}`,
            source: table.name,
            target: target.name,
            sourceHandle: `out-${sourceColumn}`,
            targetHandle: `in-${targetColumn}`,
            type: "smoothstep",
            markerEnd: { type: MarkerType.ArrowClosed, color: "#7e654e" },
            style: { stroke: "#866b53", strokeWidth: 1.7 },
            label: `${key.column} → ${key.target_column}`,
            labelStyle: { fontSize: 10, fill: "#554435" },
            labelBgStyle: { fill: "#f7f5f3" },
          },
        ]
      }),
    )
    return { nodes, edges }
  }, [schema])
  return (
    <section className="schema-screen" aria-label="Sơ đồ lược đồ CSDL">
      <div className="schema-heading">
        <div>
          <h2>{database}</h2>
          <p>
            PK: khóa chính · FK: khóa ngoại · Mũi tên từ FK đến cột được tham
            chiếu.
          </p>
        </div>
        <span>
          {schema.length} bảng ·{" "}
          {schema.reduce(
            (count, table) =>
              count +
              table.foreign_keys.filter((key) => key.sequence === 0).length,
            0,
          )}{" "}
          quan hệ
        </span>
      </div>
      {loading ? (
        <div className="empty-state" role="status">
          Đang tải lược đồ CSDL…
        </div>
      ) : error ? (
        <div className="empty-state" role="alert">
          {error}
          <button type="button" onClick={onRetry}>
            Thử lại
          </button>
        </div>
      ) : !schema.length ? (
        <div className="empty-state">Database chưa có bảng để hiển thị.</div>
      ) : (
        <>
          <p className="schema-hint">
            Kéo nền để di chuyển · Cuộn để phóng to/thu nhỏ · Kéo bảng để sắp
            xếp · Nút vừa khung nằm ở góc dưới trái.
          </p>
          {!edges.length && (
            <p className="schema-hint">
              Database không khai báo liên kết khóa ngoại giữa các cột hiển thị.
            </p>
          )}
          <div className="schema-canvas">
            <ReactFlow
              key={database}
              defaultNodes={nodes}
              defaultEdges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.15, maxZoom: 1 }}
              minZoom={0.08}
              maxZoom={1.8}
              nodesConnectable={false}
              deleteKeyCode={null}
              aria-label={`Lược đồ database ${database}`}
            >
              <Background color="#dfd8d1" gap={22} />
              <Controls showInteractive={false} />
              <MiniMap pannable zoomable nodeColor="#e3d8ce" />
            </ReactFlow>
          </div>
          <details className="schema-ddl">
            <summary>Xem DDL gốc</summary>
            {schema.map((table) => (
              <div key={table.name}>
                <h3>{table.name}</h3>
                <pre>{table.ddl}</pre>
              </div>
            ))}
          </details>
        </>
      )}
    </section>
  )
}
