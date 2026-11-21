import { methodContext, record, type Step } from "./flow-model"
import { describeStep } from "./method-stages"

function format(value: unknown): string {
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

export default function MethodStepPayload({
  step,
  steps,
  mode,
}: {
  step: Step
  steps: Step[]
  mode: "input" | "output"
}) {
  const info = describeStep(step)!
  const context = methodContext(step, steps)
  const input = record(step.input)
  const output = record(step.output)
  const dail = step.id.startsWith("dail_sql-")
  const selection = step.stage.startsWith("Example selection")
  const generation = step.stage.startsWith("SQL generation")
  const calls = step.calls ?? []
  const response =
    typeof step.output === "string" ? step.output : context.response
  return (
    <>
      <p className="trace-caption">{info.purpose}</p>
      {calls.length > 1 && (
        <p className="trace-caption">
          Có {calls.length} lần gọi LLM với cùng prompt do lần trước phát sinh
          lỗi (tối đa 3 lần). Đây là retry lời gọi, không phải vòng sửa theo lỗi
          SQLite.
        </p>
      )}
      {dail &&
        generation &&
        calls.length === 1 &&
        record(calls[0].input)?.max_attempts === undefined && (
          <p className="trace-caption">
            Trace cũ chỉ lưu bản ghi bao ngoài lời gọi LLM, chưa tách riêng các
            lần retry bên trong. Không suy ra số lần thử từ một bản ghi này.
          </p>
        )}
      {mode === "input" ? (
        <>
          <Block title="Câu hỏi" value={context.question} />
          <Block title="Database" value={context.db_id} />
          {!dail && step.stage !== "Schema linking" && (
            <Block title="Schema links đầu vào" value={context.schema_links} />
          )}
          {!dail && generation && (
            <>
              <Block title="Nhánh prompt sinh SQL" value={context.branch} />
              <Block title="Câu hỏi con" value={input?.sub_questions} />
            </>
          )}
          {step.stage === "Self-correction" && (
            <Block
              title="SQL ứng viên cần kiểm tra"
              value={context.sql_before}
            />
          )}
          {selection && (
            <>
              <Block title="Bộ chọn ví dụ" value={context.selector} />
              <Block
                title="Số ví dụ tối đa được cấu hình (k-shot)"
                value={context.k_shot}
              />
              {step.stage.endsWith("2") && (
                <Block
                  title="SQL sơ bộ dùng để chọn lại ví dụ"
                  value={context.preliminary_sql}
                />
              )}
              <p className="trace-caption">
                Bước này chưa gọi LLM. Xem ví dụ được chọn và prompt đã ghép ở
                tab Output.
              </p>
            </>
          )}
          {generation && dail && context.selection && (
            <Block
              title="Số ví dụ trong prompt được chuẩn bị ở bước trước"
              value={context.selection.n_examples}
            />
          )}
          {calls.map((call, i) => (
            <div key={call.id}>
              <Block
                title={`Prompt thực tế gửi LLM${calls.length > 1 ? ` · lần ${i + 1}` : ""}`}
                value={record(call.input)?.prompt ?? call.input}
              />
              <Block
                title="Cấu hình lời gọi LLM"
                value={
                  record(call.input) && {
                    model: record(call.input)?.model,
                    temperature: record(call.input)?.temperature,
                    n: record(call.input)?.n,
                    attempt: record(call.input)?.attempt,
                    max_attempts: record(call.input)?.max_attempts,
                  }
                }
              />
            </div>
          ))}
          {!selection && calls.length === 0 && context.prompt && (
            <Block title="Prompt thực tế gửi LLM" value={context.prompt} />
          )}
          {generation && dail && calls.length === 0 && !context.prompt && (
            <>
              <Block
                title="Prompt đã chuẩn bị ở bước chọn ví dụ (chưa có bản ghi gửi LLM)"
                value={context.selection?.prompt}
              />
              <p className="trace-caption">
                Chưa ghi nhận lời gọi LLM trong lượt sinh SQL này.
              </p>
            </>
          )}
          {step.stage === "Preprocessing" && (
            <p className="trace-caption">
              Tiền xử lý dữ liệu, không có prompt gửi LLM.
            </p>
          )}
        </>
      ) : (
        <>
          {step.status === "error" && (
            <Block title="Lỗi của bước" value={step.output} />
          )}
          {step.stage === "Schema linking" && (
            <Block title={info.output} value={context.schema_output} />
          )}
          {step.stage === "Classification" && (
            <>
              <Block
                title="Nhãn phân loại / nhánh sinh SQL"
                value={context.label}
              />
              <Block
                title="Câu hỏi con chuyển sang sinh SQL"
                value={output?.sub_questions}
              />
              {output?.label !== undefined && (
                <p className="trace-caption">
                  Nhãn được runner trích từ phản hồi để chọn nhánh. Parser có
                  thể dùng nhánh mặc định NESTED khi không tìm được nhãn; xem
                  phản hồi gốc bên dưới.
                </p>
              )}
              {!context.label && step.status === "done" && (
                <p className="trace-caption">
                  Trace chưa ghi nhãn phân loại rõ ràng. Giữ nguyên phản hồi bên
                  dưới để đối chiếu.
                </p>
              )}
            </>
          )}
          {(generation || step.stage === "Self-correction") &&
            step.status === "done" && (
              <Block
                title={info.output}
                value={
                  context.sql ??
                  (dail && typeof step.output === "string"
                    ? step.output
                    : undefined)
                }
              />
            )}
          {!dail && generation && step.status === "done" && !context.sql && (
            <p className="trace-caption">
              Trace chưa có SQL ứng viên được tách riêng. Xem đầy đủ phản hồi
              LLM gốc bên dưới.
            </p>
          )}
          {step.stage === "Preprocessing" && output && (
            <>
              <Block
                title="Số câu hỏi đích được xử lý"
                value={output.target_count ?? output.examples}
              />
              <Block title="Token của câu hỏi" value={output.question_tokens} />
              <Block title="Nguồn ví dụ train" value={output.training_data} />
              <Block
                title="Cache dữ liệu train"
                value={
                  output.training_cache_reused === true
                    ? "Đã tái sử dụng cache train; câu hỏi mới vẫn được xử lý."
                    : output.training_cache_reused === false
                      ? "Đã xử lý dữ liệu train trong lượt này."
                      : undefined
                }
              />
            </>
          )}
          {selection && output && (
            <>
              <h4>
                {String(output.n_examples ?? context.examples?.length ?? 0)} ví
                dụ được chọn
              </h4>
              {context.examples?.map((example, i) => {
                const item = record(example)
                return (
                  <details className="trace-raw" key={i}>
                    <summary>
                      {i + 1}. {String(item?.db_id ?? "Database")} ·{" "}
                      {String(item?.question ?? "")}
                    </summary>
                    <pre>{format(item?.query ?? example)}</pre>
                  </details>
                )
              })}
              <Block
                title="Prompt đã ghép để chuyển sang bước sinh SQL"
                value={output.prompt}
              />
              <p className="trace-caption">
                SQL trong các ví dụ thuộc tập train, không phải SQL dự đoán cho
                câu hỏi đích.
              </p>
            </>
          )}
          {calls.map((call, i) => (
            <div key={call.id}>
              <Block
                title={`${call.status === "error" ? "Lỗi gọi LLM" : "Phản hồi LLM gốc"}${calls.length > 1 ? ` · lần ${i + 1}` : ""}`}
                value={record(call.output)?.response ?? call.output}
              />
              <details className="trace-raw">
                <summary>Bản ghi lời gọi LLM đầy đủ</summary>
                <pre>{format(call)}</pre>
              </details>
            </div>
          ))}
          {!dail && step.status === "done" && calls.length === 0 && (
            <Block title="Phản hồi LLM gốc" value={response} />
          )}
          {step.status === "running" && (
            <p className="trace-caption">Đang chờ bước xử lý hoàn tất.</p>
          )}
          {step.status === "interrupted" && (
            <p className="trace-caption">
              Bước đã bị gián đoạn; chưa có output hoàn tất.
            </p>
          )}
        </>
      )}
      <details className="trace-raw">
        <summary>
          {mode === "input"
            ? "Input gốc / tham số chạy"
            : "Output gốc của bước"}
        </summary>
        <pre>{format(step[mode]) || "Chưa có bản ghi."}</pre>
      </details>
    </>
  )
}
