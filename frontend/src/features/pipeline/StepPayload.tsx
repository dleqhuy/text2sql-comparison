import {
  macAgents,
  evaluationDescription,
  record,
  stepDetails,
  type Step,
  type TableResult,
} from "./flow-model"
import MacStepPayload from "./MacStepPayload"
import CodexStepPayload from "./CodexStepPayload"
import MethodStepPayload from "./MethodStepPayload"
import { describeStep } from "./method-stages"
import RefinerCallPayload from "./RefinerCallPayload"

function format(value: unknown) {
  return typeof value === "string"
    ? value
    : (JSON.stringify(value, null, 2) ?? "")
}
export function TraceTable({ result }: { result: TableResult }) {
  return (
    <div className="trace-table-block">
      <div className="result-table-wrap">
        <table>
          <thead>
            <tr>
              {result.columns.map((column, i) => (
                <th key={`${i}-${column}`}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>
                    {cell === null
                      ? "NULL"
                      : typeof cell === "object"
                        ? format(cell)
                        : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="trace-caption">
        {result.rows.length} dòng hiển thị
        {result.truncated ? " · kết quả đã cắt bớt" : ""}
        {result.truncated_cells ? " · nội dung một số ô đã cắt bớt" : ""}
        {result.rows.length === 0 ? " · truy vấn trả về tập rỗng" : ""}
      </p>
      {result.evaluation && (
        <div
          className={`evaluation ${result.evaluation.correct ? "" : "wrong"}`}
        >
          {result.evaluation.correct ? "Khớp đáp án" : "Không khớp đáp án"} ·{" "}
          {result.evaluation.metric} trên 1 database
        </div>
      )}
    </div>
  )
}

export default function StepPayload({
  step,
  steps,
  mode,
}: {
  step: Step
  steps: Step[]
  mode: "input" | "output"
}) {
  const details = stepDetails(step, steps)
  const raw = step[mode]
  const description =
    step.stage === "SQLite execution"
      ? { purpose: evaluationDescription }
      : describeStep(step)
  if (
    step.id.startsWith("mac_sql-") &&
    ["Refiner · execution", "Refiner"].includes(step.stage)
  )
    return <RefinerCallPayload step={step} mode={mode} />
  if (
    step.id.startsWith("codex_mcp-") &&
    ["Codex turn", "search_objects", "execute_sql"].includes(step.stage)
  )
    return (
      <CodexStepPayload
        step={step}
        steps={steps}
        mode={mode}
        table={
          details.table ? <TraceTable result={details.table} /> : undefined
        }
      />
    )
  if (description && !["Input", "SQLite execution"].includes(step.stage))
    return <MethodStepPayload step={step} steps={steps} mode={mode} />
  if (step.calls !== undefined && macAgents[step.stage])
    return <MacStepPayload step={step} mode={mode} />
  if (mode === "input" && details.executionInput)
    return (
      <>
        {description && <p className="trace-caption">{description.purpose}</p>}
        <div className="trace-sql">
          <span className="trace-caption">SQL đã sinh</span>
          <div className="payload dark">
            <pre>{format(details.executionInput.sql)}</pre>
          </div>
        </div>
        <div className="trace-sql">
          <span className="trace-caption">Gold SQL · đáp án tham chiếu</span>
          <div className="payload dark">
            <pre>
              {details.executionInput.gold_sql == null
                ? "Không có gold SQL cho câu hỏi này."
                : format(details.executionInput.gold_sql)}
            </pre>
          </div>
        </div>
      </>
    )
  if (mode === "input")
    return (
      <>
        {description && <p className="trace-caption">{description.purpose}</p>}
        {details.prompt && (
          <div className="trace-caption">
            Prompt được ghi tại <strong>{details.promptSource}</strong>.
          </div>
        )}
        <div className="payload">
          <pre>
            {details.prompt ??
              (raw === undefined ? (
                <span className="empty">
                  Bước này không có input riêng được ghi lại.
                </span>
              ) : (
                format(raw)
              ))}
          </pre>
        </div>
        {details.prompt && typeof raw !== "string" && (
          <details className="trace-raw">
            <summary>Input gốc của bước</summary>
            <pre>{format(raw)}</pre>
          </details>
        )}
      </>
    )
  return (
    <>
      {description && <p className="trace-caption">{description.purpose}</p>}
      {details.sql && (
        <div className="trace-sql">
          <span className="trace-caption">SQL trong bản ghi thực tế</span>
          <div className="payload dark">
            <pre>{details.sql}</pre>
          </div>
        </div>
      )}
      {details.table && <TraceTable result={details.table} />}
      {details.executionInput && details.table && !details.table.evaluation && (
        <p className="trace-caption">
          Chưa có đánh giá SQLite EX
          {details.executionInput.gold_sql == null
            ? ": câu hỏi không có gold SQL để đối chiếu."
            : "."}
        </p>
      )}
      {details.examples && (
        <div className="trace-examples">
          <h4>{details.examples.length} ví dụ được chọn</h4>
          {details.examples.map((example, i) => {
            const item = record(example)
            return (
              <details key={i}>
                <summary>
                  <span>{i + 1}</span>
                  <strong>{String(item?.db_id ?? "Database")}</strong>{" "}
                  {String(item?.question ?? "")}
                </summary>
                <pre>{format(item?.query ?? example)}</pre>
              </details>
            )
          })}
          <p className="trace-caption">
            Mở tab Input / prompt để xem prompt đã ghép từ các ví dụ này.
          </p>
        </div>
      )}
      {details.response && !details.sql && (
        <div className="payload">
          <pre>{details.response}</pre>
        </div>
      )}
      {!details.sql &&
        !details.table &&
        !details.examples &&
        !details.response && (
          <div className="payload">
            <pre>
              {raw === undefined ? (
                <span className="empty">
                  {step.status === "running"
                    ? "Đang chờ phản hồi từ runner…"
                    : "Không có output riêng."}
                </span>
              ) : (
                format(raw)
              )}
            </pre>
          </div>
        )}
      {(details.sql ||
        details.table ||
        details.examples ||
        details.response) && (
        <details className="trace-raw">
          <summary>Output / response gốc</summary>
          <pre>{format(raw)}</pre>
        </details>
      )}
    </>
  )
}
