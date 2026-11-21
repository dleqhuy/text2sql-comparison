import { useMemo } from "react"
import {
  Background,
  BackgroundVariant,
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  getSmoothStepPath,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useReactFlow,
  type NodeProps,
  type EdgeProps,
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
import { createFlow, type Task, type Lane, type Session } from "./flow-graph"
import "@xyflow/react/dist/style.css"
import "./flow.css"
import { flowSemantics } from "./method-stages"
import type { LabelPosition } from "./edge-labels"

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
      <Handle type="target" position={Position.Bottom} id="bottom-in" />
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
              : data.llmAttempts
                ? `LLM: ${data.llmAttempts} bản ghi`
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
function SessionNode({ data }: NodeProps<Session>) {
  return (
    <div
      className={`flow-session ${data.status} ${data.compact ? "compact" : ""} ${data.supplemental ? "supplemental" : ""}`}
      data-testid={data.supplemental ? "evaluation-frame" : "agent-session"}
    >
      <strong>{data.title}</strong>
      <p>{data.subtitle}</p>
      <small>
        {data.footer ??
          "Hai chiều của vòng lặp: yêu cầu → tool · kết quả / lỗi → agent. # là thứ tự gọi MCP trong trace."}
      </small>
    </div>
  )
}
const nodeTypes = { task: TaskNode, lane: LaneNode, session: SessionNode }

function ProviderRetryEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  style,
  label,
}: EdgeProps) {
  const path = `M ${sourceX} ${sourceY} C ${sourceX - 90} ${sourceY} ${sourceX - 90} ${targetY - 55} ${targetX} ${targetY - 55} C ${targetX + 35} ${targetY - 55} ${targetX} ${targetY - 15} ${targetX} ${targetY}`
  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          className="flow-retry-label nodrag nopan"
          data-testid="provider-retry-label"
          style={{
            transform: `translate(-50%, -50%) translate(${targetX - 15}px, ${targetY - 40}px)`,
          }}
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}
function PositionedLabelEdge(props: EdgeProps) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    markerEnd,
    style,
    label,
    data,
  } = props
  const args = {
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  }
  const [path, anchorX, anchorY] =
    data?.pathType === "default" ? getBezierPath(args) : getSmoothStepPath(args)
  const placement = data?.labelPosition as LabelPosition | undefined
  const center = placement
    ? {
        x: placement.x + placement.width / 2,
        y: placement.y + placement.height / 2,
      }
    : undefined
  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      {center && Math.hypot(center.x - anchorX, center.y - anchorY) > 24 && (
        <path
          d={`M ${anchorX} ${anchorY} L ${center.x} ${center.y}`}
          fill="none"
          stroke={String(style?.stroke ?? "#857160")}
          strokeWidth={1}
          strokeDasharray="3 3"
        />
      )}
      {placement && (
        <EdgeLabelRenderer>
          <div
            className="flow-edge-label nodrag nopan"
            data-testid="flow-edge-label"
            data-edge-id={id}
            style={{
              transform: `translate(${placement.x}px, ${placement.y}px)`,
              width: placement.width,
              color: String(style?.stroke ?? "#736254"),
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
const edgeTypes = {
  providerRetry: ProviderRetryEdge,
  positionedLabel: PositionedLabelEdge,
}

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
  onSelect: (index: number, detailId?: string) => void
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
      {flowSemantics[method] && (
        <aside className="flow-semantics" data-testid="flow-semantics">
          <strong>{flowSemantics[method].title}</strong>
          <p>{flowSemantics[method].flow}</p>
        </aside>
      )}
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
          edgeTypes={edgeTypes}
          onNodeClick={(_, node) => {
            if (
              (node.type === "task" || node.type === "session") &&
              node.data.stepIndex !== undefined
            )
              onSelect(
                node.data.stepIndex,
                node.type === "task" ? node.data.detailId : undefined,
              )
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
              if (
                (node?.type === "task" || node?.type === "session") &&
                node.data.stepIndex !== undefined
              )
                onSelect(
                  node.data.stepIndex,
                  node.type === "task" ? node.data.detailId : undefined,
                )
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
            color="#dfd9d4"
          />
          <Controls showInteractive={false} />
          <MiniMap
            position="bottom-left"
            style={{ marginLeft: 52, width: 130, height: 80 }}
            pannable
            zoomable
            nodeColor={(node) =>
              node.type === "lane"
                ? "#f1ede9"
                : node.data.status === "error"
                  ? "#cc8a77"
                  : node.data.status === "done"
                    ? "#ac927b"
                    : "#dfd9d4"
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
          {method === "mac_sql"
            ? "Selector → Decomposer → vòng lặp Refiner. Đỏ: SQL lỗi → LLM sửa; xanh dương: SQL đã sửa → chạy lại; xanh lá: chạy thành công → đánh giá với gold SQL. Nét đứt là nhánh chưa được ghi nhận. Bấm từng lần chạy / sửa để xem chi tiết."
            : method === "din_sql"
              ? "Không có vòng phản hồi SQLite. LLM tự kiểm tra một lần; vòng xanh (nếu có) chỉ là retry lời gọi LLM khi phát sinh lỗi."
              : method === "dail_sql"
                ? "Hai lượt cố định, không phải vòng sửa SQL theo lỗi thực thi. SQL sơ bộ → chọn lại ví dụ là phụ thuộc dữ liệu; vòng xanh (nếu có) chỉ là retry lời gọi LLM."
                : "Hai tool nằm trong phiên Codex. Mũi tên nâu: agent gọi tool; xanh: kết quả về agent; đỏ: lỗi về agent. Số # cho biết thứ tự gọi thực tế. Agent có thể gọi tiếp cho đến khi chốt SQL; chấm gold SQL ở ngoài phiên."}
        </small>
      </div>
    </div>
  )
}
