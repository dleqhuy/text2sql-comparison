# Codex MCP SQL (`codex_mcp`)

[Tổng quan các phương pháp](methods.md) · [Cấu hình và phiên bản](versions.md)

## Luồng xử lý

```text
Câu hỏi + db_id
    |
    v
Thread Codex ephemeral mới cho mỗi câu
    |
    +--> search_objects: tìm bảng/cột, đọc DDL, PK/FK
    |          |
    |          v
    +--> execute_sql: thử SQL read-only trên đúng database
    |          |
    |          +-- Kết quả/lỗi -> tiếp tục khám phá hoặc sửa SQL
    |          |
    |          +-- Đủ thông tin -> trả {"sql": "..."}
    |                                  |
    |                                  v
    |                  Runner đối chiếu audit thực thi thành công
    |                                  |
    +-- Hết ngân sách/lỗi               v
           |                       Lưu prediction
           v
     Lưu trạng thái lỗi/checkpoint
```

Model tự quyết định thứ tự và số lần dùng tool trong ngân sách, không đi qua
các prompt cố định như DIN-SQL. Mặc định: effort `low`, 20 tool calls/câu,
180 giây/câu, 5 giây/SQL, tối đa 100 dòng mỗi tool result. SQL cuối phải khớp
SQL đã chạy thành công trong audit, bỏ qua dấu `;` cuối và khoảng trắng cuối.
Điều kiện này kiểm tra khả năng thực thi; evaluator chung mới kiểm tra EX.

## Chuẩn bị

Chạy từ `text2sql-comparison/`, sau khi [cài môi trường và dữ liệu](setup.md).
Cần Python 3.12 và xác thực Codex/OpenAI theo [setup.md](setup.md#codex-mcp-sql).
Model lấy từ `--codex-model` hoặc `CODEX_MODEL`; tên model trong ví dụ là
cấu hình thí nghiệm đã lưu, có thể thay bằng model tài khoản hỗ trợ.

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a
```

Lệnh mẫu dùng 20 câu đầu. Để chạy toàn bộ dev, bỏ `--count 20` và chọn
`--output` mới. Runner tự chuẩn hóa và chấm sau inference; raw đã có sẽ khiến
lượt inference mới bị từ chối.

## Chạy riêng và output

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna \
  --count 20 --workers 4 --output results/codex_guide20

# Tiếp tục đúng lượt trên sau khi bị ngắt hoặc hết usage
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna \
  --count 20 --workers 4 --output results/codex_guide20 --resume
```

`--workers` chỉ áp dụng cho Codex, mặc định 1. Resume chỉ dùng khi chọn riêng
`codex_mcp`; giữ input, model, effort và ngân sách như lần đầu. Có thể đổi số
worker. Nếu còn câu chưa chạy hoặc hết usage, comparison dừng trước bước chấm.

- Output/checkpoint: `raw/codex_mcp/`; log: `raw/codex_mcp.log`.
- Cấu hình: `raw/codex_mcp/metadata.json`; tiến độ: `raw/codex_mcp/summary.json`.
- Audit từng câu: `raw/codex_mcp/traces/<index>/tools.jsonl`.
- SQL chuẩn hóa: `predictions/codex_mcp.jsonl`.
- Chi tiết runner/tool/resume: [README Codex MCP SQL](../../codex-mcp-sql/README.md).

## Chấm lại và đọc kết quả

Sau khi mọi câu đã được thử và lượt chạy không còn bị dừng do usage/pending,
chấm lại raw của đúng lượt chạy trên, không gọi model:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --count 20 --output results/codex_guide20 --evaluate-only
```

Mọi đường dẫn `raw/`, `predictions/`, `evaluation/` ở trên tính từ `--output`.
Mở `report.md` để xem điểm EX và `evaluation/codex_mcp.details.json` để xem
đúng/sai, lỗi từng câu. Dùng `index` để đối chiếu SQL ở
`predictions/codex_mcp.jsonl` với gold trong `examples.json` của input chung.
SQL chạy được vẫn có thể sai nghĩa; xem [quy tắc chấm](full-dev.md#đọc-kết-quả).

Thêm `--dry-run` vào lệnh inference để xem trước các bước, không gọi model hoặc
ghi output. Xem [tùy chọn chung và xử lý lỗi](methods.md#chạy-và-kiểm-tra-kết-quả).
