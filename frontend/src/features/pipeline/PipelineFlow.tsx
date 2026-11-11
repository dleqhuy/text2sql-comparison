import { useMemo } from "react"
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useReactFlow,
  type NodeProps,
} from "@xyflow/react"
import {
  Check,
  Circle,
  Focus,
  GitBranch,
  Loader2,
  TriangleAlert,
} from "lucide-react"
import type { Method, Step } from "./flow-model"
import { createFlow, type Task, type Lane } from "./flow-graph"
import "@xyflow/react/dist/style.css"
import "./flow.css"

function LaneNode({ data }: NodeProps<Lane>) {
  return (
    <div className="flow-lane">
      <span>{data.title}</span>
    </div>
  )
}
function TaskNode({ data, selected }: NodeProps<Task>) {
  const StatusIcon = data.gateway
    ? GitBranch
    : data.status === "running"
      ? Loader2
      : data.status === "error" || data.status === "interrupted"
        ? TriangleAlert
        : data.status === "done"
          ? Check
          : Circle
  return (
    <div
      className={`flow-task ${data.status} ${selected ? "is-selected" : ""} ${data.gateway ? "flow-gateway" : ""}`}
      data-testid="pipeline-node"
      data-stage={data.stage}
    >
      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="target" position={Position.Left} id="left" />
      <Handle type="target" position={Position.Right} id="right-in" />
      {data.gateway && (
        <svg
          className="flow-gateway-shape"
          viewBox="0 0 210 140"
          aria-hidden="true"
        >
          <title>Quyết định chọn prompt</title>
          <polygon points="105,2 207,70 105,138 3,70" />
        </svg>
      )}
      <div className="flow-task-heading">
        <StatusIcon
          size={16}
          className={data.status === "running" ? "spin" : ""}
        />
        <span>{data.gateway ? "Chọn prompt" : data.title}</span>
      </div>
      <p>{data.gateway ? (data.branch ?? "Chưa có nhãn") : data.subtitle}</p>
      {data.gateway && (
        <div className="flow-branches">
          {["EASY", "NON-NESTED", "NESTED"].map((label) => (
            <span className={data.branch === label ? "chosen" : ""} key={label}>
              {label}
            </span>
          ))}
        </div>
      )}
      <div className="flow-task-meta">
        <span>
          {data.gateway
            ? "Nhánh prompt"
            : data.status === "planned"
              ? "Chưa có trace"
              : `Lần ${data.attempt}`}
        </span>
        <span>
          {data.elapsed !== undefined
            ? `${data.elapsed.toFixed(2)}s`
            : data.status === "running"
              ? "Đang chạy"
              : data.status === "interrupted"
                ? "Chưa hoàn tất"
                : data.status === "error"
                  ? "Có lỗi"
                  : ""}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" />
      <Handle type="source" position={Position.Right} id="right" />
      <Handle type="source" position={Position.Left} id="left-out" />
    </div>
  )
}
const nodeTypes = { task: TaskNode, lane: LaneNode }

function FocusStep({ id }: { id?: string }) {
  const flow = useReactFlow()
  return (
    <button
      className="flow-focus"
      type="button"
      disabled={!id}
      onClick={() =>
        id &&
        void flow.fitView({
          nodes: [{ id }],
          padding: 1.2,
          maxZoom: 1.1,
          duration: 250,
        })
      }
    >
      <Focus size={14} /> Tập trung bước
    </button>
  )
}

type Props = {
  title: string
  method: Method
  steps: Step[]
  selectedId?: string
  onSelect: (index: number) => void
  runId?: string
}
export default function PipelineFlow({
  title,
  method,
  steps,
  selectedId,
  onSelect,
  runId,
}: Props) {
  const graph = useMemo(
    () => createFlow(method, steps, selectedId),
    [method, steps, selectedId],
  )
  return (
    <div className="pipeline-flow-panel">
      <div className="flow-heading">
        <div>
          <span className="flow-kicker">PROCESS MAP</span>
          <strong>{title} · Luồng xử lý thực tế</strong>
        </div>
        <span>
          {steps.length} bản ghi ·{" "}
          {steps.filter((s) => s.status === "done").length} hoàn tất
        </span>
      </div>
      <section
        className="flow-canvas"
        data-testid="pipeline-flow"
        aria-label="Sơ đồ pipeline tương tác"
      >
        <ReactFlow
          key={`${runId ?? "preview"}-${method}`}
          nodes={graph.nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => {
            if (node.type === "task" && node.data.stepIndex !== undefined)
              onSelect(node.data.stepIndex)
          }}
          onNodesChange={(changes) => {
            for (const change of changes) {
              if (
                change.type !== "select" ||
                !change.selected ||
                change.id === selectedId
              )
                continue
              const node = graph.nodes.find(
                (candidate) => candidate.id === change.id,
              )
              if (node?.type === "task" && node.data.stepIndex !== undefined)
                onSelect(node.data.stepIndex)
            }
          }}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesFocusable={false}
          deleteKeyCode={null}
          fitView
          fitViewOptions={{ padding: 0.08, minZoom: 0.45, maxZoom: 0.9 }}
          minZoom={0.25}
          maxZoom={1.5}
          proOptions={{ hideAttribution: false }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={18}
            size={1}
            color="#d9dfd4"
          />
          <Controls showInteractive={false} />
          <MiniMap
            position="bottom-left"
            style={{ marginLeft: 52, width: 130, height: 80 }}
            pannable
            zoomable
            nodeColor={(node) =>
              node.type === "lane"
                ? "#edf1e9"
                : node.data.status === "error"
                  ? "#cc8a77"
                  : node.data.status === "done"
                    ? "#90ac7b"
                    : "#d9dfd4"
            }
          />
          <FocusStep id={selectedId} />
        </ReactFlow>
      </section>
      <div className="flow-legend">
        <span>
          <i className="done" /> Đã chạy
        </span>
        <span>
          <i className="running" /> Đang chạy
        </span>
        <span>
          <i className="error" /> Lỗi / gián đoạn
        </span>
        <span>
          <i className="planned" /> Chưa có trace
        </span>
        <small>
          Bấm một bước để xem dữ liệu · kéo để di chuyển · dùng + / − để thu
          phóng.
        </small>
      </div>
    </div>
  )
}
