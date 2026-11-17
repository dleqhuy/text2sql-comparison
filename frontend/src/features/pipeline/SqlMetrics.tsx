import { useQuery } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { Loader2 } from "lucide-react"
import { LiveService } from "@/client"
import { Button } from "@/components/ui/button"
import type { Method } from "./flow-model"

const cmLabels: Record<string, string> = {
  select: "SELECT",
  "select(no AGG)": "SELECT (bỏ hàm tổng hợp)",
  where: "WHERE",
  "where(no OP)": "WHERE (bỏ toán tử)",
  "group(no Having)": "GROUP BY (bỏ HAVING)",
  group: "GROUP BY / HAVING",
  order: "ORDER BY",
  "and/or": "AND / OR",
  IUEN: "INTERSECT / UNION / EXCEPT",
  keywords: "KEYWORDS",
}
const primaryComponents = ["select", "where", "group", "order", "keywords"]

export default function SqlMetrics({
  runId,
  method,
  hasReference,
  running,
}: {
  runId: string
  method: Method
  hasReference: boolean
  running: boolean
}) {
  const query = useQuery({
    queryKey: ["sql-metrics-cm", runId, method],
    queryFn: async () =>
      (await LiveService.readMetrics({ path: { run_id: runId, method } })).data,
    enabled: false,
    retry: false,
    staleTime: Infinity,
  })
  const values = query.data
  const error =
    isAxiosError(query.error) &&
    typeof query.error.response?.data?.detail === "string"
      ? query.error.response.data.detail
      : query.error?.message
  return (
    <section className="sql-metrics" aria-label="Độ đo CM EM EX VES">
      <div className="sql-metrics-heading">
        <strong>Đánh giá câu hỏi này</strong>
        <Button
          size="sm"
          variant="outline"
          disabled={!hasReference || running || query.isFetching}
          onClick={() => void query.refetch()}
        >
          {query.isFetching && <Loader2 size={12} className="spin" />}
          {query.isFetching
            ? "Đang đo…"
            : values
              ? "Đo lại CM / EM / EX / VES"
              : "Tính CM / EM / EX / VES"}
        </Button>
      </div>
      {!hasReference ? (
        <p>
          Câu hỏi tự nhập không có SQL tham chiếu để tính CM, EM, EX và VES.
        </p>
      ) : running ? (
        <p>Chờ phiên chạy kết thúc trước khi đo tốc độ SQL.</p>
      ) : (
        <p>
          EM/EX là điểm 0 hoặc 1 của một câu, không phải tỷ lệ chính xác toàn bộ
          tập dữ liệu.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      {values && (
        <>
          <div className="sql-metrics-grid">
            <div title="Component Matching: F1 từng thành phần từ evaluator Spider; không gộp thành điểm trung bình.">
              <span>CM · F1 thành phần</span>
              {values.cm ? (
                <dl className="cm-values">
                  {primaryComponents.map((key) => {
                    const component = values.cm?.[key]
                    const used =
                      component &&
                      (component.pred_total > 0 || component.label_total > 0)
                    return (
                      <div key={key}>
                        <dt>{key === "group" ? "GROUP BY" : cmLabels[key]}</dt>
                        <dd>{used ? component.f1.toFixed(2) : "—"}</dd>
                      </div>
                    )
                  })}
                </dl>
              ) : (
                <strong>N/A</strong>
              )}
            </div>
            <div title="Exact Set Match theo parser và bộ đánh giá Spider; không so khớp chuỗi SQL.">
              <span>EM · cấu trúc SQL</span>
              <strong>{values.em ?? "N/A"}</strong>
            </div>
            <div title="Execution Accuracy theo SQLite EX của dự án: so sánh kết quả, giữ số lần lặp và thứ tự khi đáp án có ORDER BY.">
              <span>EX · kết quả truy vấn</span>
              <strong>{values.ex ?? "N/A"}</strong>
            </div>
            <div title="VES demo = 100 × √(trung bình tỷ số thời gian SQL đáp án / SQL dự đoán sau lọc 3σ), khi kết quả khớp theo quy tắc tập hợp của BIRD; không khớp thì bằng 0.">
              <span>VES · demo / một câu</span>
              <strong>
                {values.ves == null ? "N/A" : values.ves.toFixed(2)}
              </strong>
            </div>
          </div>
          {values.cm && (
            <details className="cm-details">
              <summary>Chi tiết CM theo thành phần SQL</summary>
              <div className="result-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Thành phần</th>
                      <th>Precision</th>
                      <th>Recall</th>
                      <th>F1</th>
                      <th>Dự đoán</th>
                      <th>Đáp án</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(values.cm).map(([key, component]) => {
                      const used =
                        component.pred_total > 0 || component.label_total > 0
                      return (
                        <tr key={key}>
                          <td>{cmLabels[key] ?? key}</td>
                          <td>{used ? component.acc.toFixed(2) : "—"}</td>
                          <td>{used ? component.rec.toFixed(2) : "—"}</td>
                          <td>{used ? component.f1.toFixed(2) : "—"}</td>
                          <td>{component.pred_total}</td>
                          <td>{component.label_total}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <p>
                Điểm theo thang 0–1 của câu đang xem. Dấu —: thành phần không
                xuất hiện trong cả dự đoán và đáp án. GROUP BY ở thẻ CM bao gồm
                kiểm tra HAVING.
              </p>
            </details>
          )}
          {values.ves_valid_match === false && (
            <p>
              VES = 0 vì kết quả không khớp theo BIRD hoặc SQL dự đoán không
              chạy được; không đo thời gian.
            </p>
          )}
          {values.em_error && values.em === 0 && (
            <p>
              EM = 0 vì parser Spider không phân tích được SQL dự đoán; xem chi
              tiết bên dưới.
            </p>
          )}
          <p>
            VES đo thời gian thực thi SQL, không gồm thời gian LLM. Đo{" "}
            {values.iterations ?? 0} cặp, lọc ngoại lệ 3σ; điểm có thể lớn hơn
            100 và dao động theo tải máy.
          </p>
          {values.predicted_ms != null && values.gold_ms != null && (
            <p>
              Trung bình trước lọc: SQL dự đoán {values.predicted_ms.toFixed(3)}{" "}
              ms · SQL đáp án {values.gold_ms.toFixed(3)} ms.
            </p>
          )}
          {(values.cm_error ||
            values.em_error ||
            values.ex_error ||
            values.ves_error) && (
            <details>
              <summary>Chi tiết tính điểm</summary>
              {values.cm_error && <p>CM: {values.cm_error}</p>}
              {values.em_error && <p>EM: {values.em_error}</p>}
              {values.ex_error && <p>EX: {values.ex_error}</p>}
              {values.ves_error && <p>VES: {values.ves_error}</p>}
            </details>
          )}
        </>
      )}
    </section>
  )
}
