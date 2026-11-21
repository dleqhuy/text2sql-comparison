import type { ReactNode } from "react"
import { codexContext } from "./codex-model"
import { record, type Step } from "./flow-model"
import { describeStep } from "./method-stages"

function format(value: unknown) {
  return typeof value === "string"
    ? value
    : (JSON.stringify(value, null, 2) ?? "")
}
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

export default function CodexStepPayload({
  step,
  steps,
  mode,
  table,
}: {
  step: Step
  steps: Step[]
  mode: "input" | "output"
  table?: ReactNode
}) {
  const context = codexContext(step, steps)
  const input = record(step.input)
  const output = record(step.output)
  const agent = step.stage === "Codex turn"
  const objects = Array.isArray(output?.objects) ? output.objects : undefined
  return (
    <>
      <p className="trace-caption">{describeStep(step)?.purpose}</p>
      {!agent && (
        <p className="trace-caption">
          Lời gọi MCP thứ {context.callNumber} trong trace của phiên. Agent có
          thể gọi lại công cụ với tham số khác; mỗi lần có input/output riêng.
        </p>
      )}
      {mode === "input" ? (
        agent ? (
          <>
            <Block
              title="Prompt người dùng gửi agent (JSON)"
              value={context.request?.prompt}
            />
            <Block
              title="Instructions dành cho agent"
              value={context.request?.instructions}
            />
            <Block
              title="Cấu hình và giới hạn của phiên"
              value={context.runtime}
            />
            <Block
              title="Định dạng output yêu cầu"
              value={context.request?.output_schema}
            />
            <p className="trace-caption">
              Agent khám phá schema qua MCP trong phiên. Gold SQL không nằm
              trong prompt.
            </p>
          </>
        ) : step.stage === "search_objects" ? (
          <>
            <Block
              title="Từ khóa tìm tên đối tượng hoặc tên cột (query)"
              value={
                input?.query === ""
                  ? "Chuỗi rỗng: liệt kê các đối tượng phù hợp với bộ lọc loại."
                  : input?.query
              }
            />
            <Block
              title="Loại đối tượng (object_type)"
              value={input?.object_type}
            />
            <Block
              title="Số đối tượng tối đa mỗi trang (limit)"
              value={input?.limit}
            />
            <Block title="Vị trí bắt đầu (offset)" value={input?.offset} />
            <p className="trace-caption">
              Đây là tham số gọi công cụ do agent chọn; không có prompt LLM
              riêng cho node này.
            </p>
          </>
        ) : (
          <>
            <Block title="SQL agent gửi MCP để chạy thử" value={input?.sql} />
            <Block
              title="Số dòng hiển thị tối đa (max_rows)"
              value={
                input?.max_rows ??
                context.runtime?.max_rows ??
                "Dùng giới hạn mặc định của phiên MCP."
              }
            />
            <Block
              title="Giới hạn thời gian truy vấn (giây)"
              value={context.runtime?.query_timeout_seconds}
            />
            <p className="trace-caption">
              SQL là input. Không có gold SQL hoặc prompt LLM riêng trong lời
              gọi công cụ này.
            </p>
          </>
        )
      ) : agent ? (
        <>
          <Block title="Trạng thái runner" value={output?.runner_status} />
          <Block title="Trạng thái phiên do SDK báo" value={output?.status} />
          <Block
            title={
              output?.audit_verified === true
                ? "SQL cuối được runner chấp nhận"
                : "SQL trong phản hồi cuối của agent (chưa có xác nhận audit trong trace)"
            }
            value={
              output?.audit_verified === true
                ? output.sql
                : (context.returnedSql ??
                  (typeof context.finalResponse === "string"
                    ? context.finalResponse
                    : undefined))
            }
          />
          {output?.audit_verified === true ? (
            <p className="trace-caption">
              Runner đã xác nhận có lần khám phá schema thành công và SQL cuối
              khớp một lần execute_sql thành công. Đây là kiểm tra audit, chưa
              phải đánh giá đúng/sai bằng gold SQL.
            </p>
          ) : (
            <p className="trace-caption">
              {step.status === "running"
                ? "Phiên đang xử lý hoặc chờ runner xác nhận audit."
                : output?.runner_status === "failed"
                  ? "Runner chưa chấp nhận SQL. Xem lỗi bên dưới; không xem phản hồi của agent là SQL đã được xác nhận."
                  : "Trace này chưa ghi xác nhận audit riêng từ runner. Trạng thái SDK hoàn tất chưa đủ để kết luận SQL đúng đáp án."}
            </p>
          )}
          <Block
            title="Tổng lời gọi MCP được runner ghi nhận"
            value={output?.tool_calls}
          />
          <Block
            title="Lời gọi công cụ đang có trong trace"
            value={{
              total: context.tools.length,
              successful: context.tools.filter((s) => s.status === "done")
                .length,
              errors: context.tools.filter((s) => s.status === "error").length,
            }}
          />
          <Block
            title="Lỗi phiên / xác nhận của runner"
            value={
              output?.error ??
              (typeof step.output === "string" ? step.output : undefined)
            }
          />
          <Block title="Usage do SDK trả về" value={output?.usage} />
          <details className="trace-raw">
            <summary>Phản hồi công khai gốc của agent</summary>
            <pre>{format(output?.final_response) || "Chưa có phản hồi."}</pre>
          </details>
        </>
      ) : (
        <>
          {step.status === "error" && (
            <Block title="Lỗi MCP trả lại cho agent" value={step.output} />
          )}
          {objects && (
            <>
              <Block
                title="Thông tin trang kết quả"
                value={{
                  displayed: objects.length,
                  total: output?.total,
                  offset: output?.offset,
                  has_more: output?.has_more,
                }}
              />
              {objects.length === 0 && (
                <p className="trace-caption">
                  Không tìm thấy đối tượng phù hợp. Agent có thể đổi từ khóa
                  hoặc bộ lọc rồi tìm tiếp.
                </p>
              )}
              {objects.map((object, i) => {
                const item = record(object)
                return (
                  <details className="trace-raw" key={i}>
                    <summary>
                      {String(item?.name ?? `Đối tượng ${i + 1}`)} ·{" "}
                      {String(item?.type ?? "")}
                    </summary>
                    <Block title="Bảng liên quan" value={item?.tbl_name} />
                    <Block title="DDL của đối tượng" value={item?.sql} />
                    <Block
                      title="Cột và thuộc tính (pk: thứ tự trong khóa chính)"
                      value={item?.columns}
                    />
                    <Block title="Khóa ngoại" value={item?.foreign_keys} />
                    <Block title="Index" value={item?.indexes} />
                    <Block title="Cột của index" value={item?.index_columns} />
                  </details>
                )
              })}
              {output?.has_more === true && (
                <p className="trace-caption">
                  Còn đối tượng ở trang tiếp theo; kết quả này chưa chứa toàn bộ
                  schema tìm thấy.
                </p>
              )}
            </>
          )}
          {table && (
            <>
              {table}
              <p className="trace-caption">
                Kết quả chạy thử được trả lại cho agent. Chưa đối chiếu gold
                SQL; chạy thành công chưa khẳng định đúng đáp án.
              </p>
            </>
          )}
          <Block
            title="Thời gian công cụ thực thi (giây)"
            value={output?.elapsed_seconds ?? step.elapsed}
          />
        </>
      )}
      <details className="trace-raw">
        <summary>
          {mode === "input" ? "Input gốc đầy đủ" : "Output gốc đầy đủ"}
        </summary>
        <pre>{format(step[mode]) || "Chưa có bản ghi."}</pre>
      </details>
    </>
  )
}
