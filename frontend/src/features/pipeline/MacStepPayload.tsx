import { macAgents, record, type Step } from "./flow-model"
import { refinerOutcome } from "./mac-model"

function format(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2)
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

export default function MacStepPayload({
  step,
  mode,
}: {
  step: Step
  mode: "input" | "output"
}) {
  const agent = macAgents[step.stage]
  const state = record(step[mode])
  const calls = step.calls ?? []
  return (
    <>
      <p className="trace-caption">
        <strong>{agent.title}.</strong> {agent.purpose}
      </p>
      {mode === "input" ? (
        <>
          <Block title="Câu hỏi" value={state?.query} />
          <Block title="Database" value={state?.db_id} />
          <Block title="Thông tin bổ sung" value={state?.evidence} />
          <Block title="Schema đầu vào" value={state?.desc_str} />
          <Block title="Khóa ngoại đầu vào" value={state?.fk_str} />
          {step.stage === "Refiner · state" && (
            <Block
              title="SQL cần chạy thử"
              value={state?.pred ?? state?.final_sql}
            />
          )}
          {calls.map((call, i) => (
            <Block
              key={call.id}
              title={`Prompt thực tế gửi LLM${calls.length > 1 ? ` · lần ${i + 1}` : ""}`}
              value={record(call.input)?.prompt ?? call.input}
            />
          ))}
          {calls.length === 0 && (
            <p className="trace-caption">
              {step.status === "running"
                ? "Chưa ghi nhận lời gọi LLM ở lượt này."
                : step.stage === "Selector · state" &&
                    record(step.output)?.pruned === false
                  ? "Không gọi LLM ở lượt này: Selector giữ schema, nên không có prompt gửi LLM."
                  : step.stage === "Refiner · state" && step.status === "done"
                    ? "Không có lời gọi LLM sửa SQL trong lượt kiểm tra này."
                    : "Trace chưa ghi nhận prompt LLM cho lượt này."}
            </p>
          )}
        </>
      ) : (
        <>
          {step.status === "error" && (
            <Block title="Lỗi của agent" value={step.output} />
          )}
          {step.stage === "Selector · state" && (
            <>
              <Block
                title="Chế độ chọn schema"
                value={
                  state?.pruned === false
                    ? "Giữ schema, không gọi LLM chọn bảng/cột."
                    : state?.pruned === true
                      ? "Đã chạy nhánh chọn schema bằng LLM; xem phản hồi và schema thực tế bên dưới."
                      : undefined
                }
              />
              <Block
                title="Bảng và cột chuyển cho Decomposer"
                value={state?.chosen_db_schem_dict}
              />
              <Block
                title="Mô tả schema cho Decomposer"
                value={state?.desc_str}
              />
              <Block title="Khóa ngoại" value={state?.fk_str} />
            </>
          )}
          {step.stage !== "Selector · state" && (
            <Block
              title={
                step.stage === "Decomposer · state"
                  ? "SQL trích xuất từ phản hồi LLM"
                  : "SQL sau lượt Refiner"
              }
              value={state?.pred ?? state?.final_sql}
            />
          )}
          {step.stage === "Decomposer · state" && calls.length === 0 && (
            <Block
              title="Phân rã bài toán / phản hồi LLM (qa_pairs)"
              value={state?.qa_pairs}
            />
          )}
          {calls.map((call, i) => (
            <Block
              key={call.id}
              title={`${call.status === "error" ? "Lỗi gọi LLM" : step.stage === "Decomposer · state" ? "Phân rã bài toán / phản hồi LLM" : "Phản hồi LLM"}${calls.length > 1 ? ` · lần ${i + 1}` : ""}`}
              value={call.output}
            />
          ))}
          {step.stage === "Refiner · state" && (
            <>
              {(step.checks ?? []).map((check) => (
                <div key={check.id}>
                  <Block
                    title="SQL đã chạy thử"
                    value={record(check.input)?.sql}
                  />
                  <Block
                    title="Kết quả chạy thử · tối đa 5 dòng / lỗi SQLite"
                    value={check.output}
                  />
                </div>
              ))}
              {!step.checks?.length && (
                <p className="trace-caption">
                  Chưa có bản ghi kết quả chạy thử riêng trong trace này. Trace
                  cũ chỉ lưu trạng thái agent.
                </p>
              )}
              <Block
                title="Hướng xử lý tiếp theo"
                value={
                  state?.send_to === "Refiner"
                    ? "Chuyển SQL đã sửa sang lượt Refiner tiếp theo để chạy thử lại."
                    : refinerOutcome(step) === "success"
                      ? "SQL đã chạy thành công; chuyển sang đánh giá SQLite EX với gold SQL. Chạy thành công chưa khẳng định đúng đáp án."
                      : "Chưa có xác nhận SQL trả về đã chạy thành công. Trace cũ có thể thiếu kết quả chạy thử; trace mới sẽ dừng nếu hết lượt mà chưa xác nhận được SQL."
                }
              />
            </>
          )}
          <Block title="Chuyển tiếp cho (send_to)" value={state?.send_to} />
          {step.status === "running" && (
            <p className="trace-caption">Đang chờ agent hoàn tất.</p>
          )}
        </>
      )}
      <details className="trace-raw">
        <summary>
          Trạng thái {mode === "input" ? "đầu vào" : "đầu ra"} đầy đủ
        </summary>
        <pre>{format(step[mode]) ?? "Chưa có trạng thái được ghi lại."}</pre>
      </details>
    </>
  )
}
