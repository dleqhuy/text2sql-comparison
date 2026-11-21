cd ~/Documents/master/text2sql

# Tạo tên thư mục kết quả cho lượt chạy này
demo_run=$(date +%Y%m%d-%H%M%S)

# 1. DIN-SQL
./run-comparison.sh --count 1 --methods few_shot --output "results/demo-$demo_run/din"

# 2. MAC-SQL
./run-comparison.sh --count 1 --methods mac_sql --output "results/demo-$demo_run/mac"

# 3. DAIL-SQL
./run-comparison.sh --count 1 --methods dail_sql --output "results/demo-$demo_run/dail"

# 4. Codex MCP SQL
./run-comparison.sh --count 1 --methods codex_mcp --codex-model gpt-6-luna --output "results/demo-$demo_run/codex"

## Nhập câu hỏi riêng qua terminal

Không cần bật app. Chạy các lệnh sau từ thư mục `text2sql`:

```bash
cd ~/Documents/master/text2sql
question="What are the names of all singers?"
db_id="concert_singer"
demo_run=$(date +%Y%m%d-%H%M%S)

# 1. DIN-SQL
./run-comparison.sh --question "$question" --db-id "$db_id" --methods few_shot --output "results/custom-$demo_run/din"

# 2. MAC-SQL
./run-comparison.sh --question "$question" --db-id "$db_id" --methods mac_sql --output "results/custom-$demo_run/mac"

# 3. DAIL-SQL
./run-comparison.sh --question "$question" --db-id "$db_id" --methods dail_sql --output "results/custom-$demo_run/dail"

# 4. Codex MCP SQL
./run-comparison.sh --question "$question" --db-id "$db_id" --methods codex_mcp --codex-model gpt-6-luna --output "results/custom-$demo_run/codex"
```

Thay `question` và `db_id` theo nhu cầu. Hai tùy chọn này phải đi cùng nhau;
không thêm `--count`. Tên phương pháp DIN-SQL trong CLI vẫn là `few_shot`.
Codex cần xác thực và model tài khoản hỗ trợ; ba phương pháp còn lại đọc `LLM_*` trong `.env`.

Có thể chạy cả bốn trong một lệnh (các phương pháp chạy lần lượt):

```bash
./run-comparison.sh --question "$question" --db-id "$db_id" --methods few_shot mac_sql dail_sql codex_mcp --codex-model gpt-6-luna
```

Nếu bỏ `--output`, runner tự tạo thư mục `text2sql-comparison/results/custom-...` mới.
Terminal in đường dẫn output, SQL và tối đa 100 dòng dữ liệu. Kết quả tổng hợp
nằm trong `results.json`; mỗi thư mục phương pháp chứa `result.json`,
`events.jsonl` (trace) và `process.log`. Câu tự nhập không có điểm CM/EM/EX/VES
vì không có SQL đáp án. Lỗi thực thi SQL được lưu trong `execution_error`.

Thêm `--dry-run` để xem lệnh mà không gọi model hoặc ghi file.
Không dùng chế độ câu hỏi tự nhập cùng `--data-dir`, `--evaluate-only`,
`--resume`, hoặc `--workers` khác 1. Nếu chỉ muốn chạy dữ liệu Spider như trước,
giữ cách dùng `--count` ở phần trên và không truyền `--question`/`--db-id`.
