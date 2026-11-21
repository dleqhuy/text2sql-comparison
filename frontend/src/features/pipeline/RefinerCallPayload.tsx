import { record, type Step } from "./flow-model"

const format = (value: unknown) =>
  typeof value === "string" ? value : (JSON.stringify(value, null, 2) ?? "")
function Block({ title, value }: { title: string; value: unknown }) {
  if (value === undefined || value === null || value === "") return null
  return (
    <div className="trace-sql">
      <h4>{title}</h4>
      <div className="payload">
        <pre>{format(value)}</pre>
      </div>
    </div>
  )
}
export default function RefinerCallPayload({
  step,
  mode,
}: {
  step: Step
  mode: "input" | "output"
}) {
  const execution = step.stage === "Refiner · execution",
    input = record(step.input),
    output = record(step.output)
  return (
    <>
      <p className="trace-caption">
        {execution
          ? "Refiner chạy SQL ứng viên trên SQLite. Kết quả hoặc lỗi được dùng để quyết định có gọi LLM sửa; chưa so sánh với gold SQL."
          : "Refiner gửi câu hỏi, schema, SQL lỗi và thông báo lỗi SQLite cho LLM để sinh SQL sửa. SQL sửa phải được chạy lại ở lượt kế tiếp trước khi chuyển sang đánh giá."}
      </p>
      {mode === "input" ? (
        <>
          <Block
            title={
              execution
                ? "SQL gửi SQLite để chạy thử"
                : "Prompt thực tế gửi LLM sửa SQL"
            }
            value={execution ? input?.sql : (input?.prompt ?? step.input)}
          />
          {execution && <Block title="Database" value={input?.db_id} />}
        </>
      ) : (
        <>
          {execution ? (
            <>
              <Block title="SQL đã chạy" value={output?.sql} />
              <Block
                title="Lỗi SQLite"
                value={
                  output?.sqlite_error ??
                  (step.status === "error" ? step.output : undefined)
                }
              />
              <Block title="Loại lỗi" value={output?.exception_class} />
              <Block
                title="Dữ liệu chạy thử · tối đa 5 dòng"
                value={output?.data}
              />
              {Array.isArray(output?.data) && !output?.sqlite_error && (
                <p className="trace-caption">
                  SQL chạy thành công. Chưa kết luận đúng đáp án; bước tiếp theo
                  đánh giá với gold SQL.
                </p>
              )}
            </>
          ) : (
            <Block
              title={
                step.status === "error"
                  ? "Lỗi gọi LLM"
                  : "Phản hồi LLM / SQL sửa"
              }
              value={step.output}
            />
          )}
          {step.status === "running" && (
            <p className="trace-caption">Đang chờ kết quả.</p>
          )}
        </>
      )}
      <details className="trace-raw">
        <summary>Bản ghi {mode === "input" ? "input" : "output"} gốc</summary>
        <pre>{format(step[mode]) || "Chưa có bản ghi."}</pre>
      </details>
    </>
  )
}
