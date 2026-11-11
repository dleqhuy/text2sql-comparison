import { record, stepDetails, type Step, type TableResult } from "./flow-model"

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
  if (mode === "input")
    return (
      <>
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
      {details.sql && (
        <div className="trace-sql">
          <span className="trace-caption">SQL trong bản ghi thực tế</span>
          <div className="payload dark">
            <pre>{details.sql}</pre>
          </div>
        </div>
      )}
      {details.table && <TraceTable result={details.table} />}
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
