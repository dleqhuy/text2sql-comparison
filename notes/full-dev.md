# Chạy toàn bộ Spider dev

Sau khi [cài môi trường](setup.md), chạy từ `text2sql-comparison/`:

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a

uv run --no-project python scripts/run_comparison.py
```

Script mặc định dùng toàn bộ 1.034 câu Spider dev, chạy DIN-SQL, MAC-SQL và
DAIL-SQL theo thứ tự, rồi chuẩn hóa và chấm SQLite EX.
Ba phương pháp này gọi endpoint LLM trong `.env`. Để chạy mới cả bốn phương pháp:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods few_shot mac_sql dail_sql codex_mcp \
  --codex-model gpt-6-luna --workers 4 --output results/all_methods_new
```

## Chọn lượt chạy

| Tùy chọn | Ý nghĩa |
|---|---|
| Không có `--count` | Toàn bộ dev; input `data/dev_full/`, output `results/full_dev/` |
| `--count N` | N câu đầu; input `data/smokeN/`, output `results/smokeN/` |
| `--methods mac_sql` | Chỉ chạy MAC-SQL; có thể chọn nhiều phương pháp |
| `--output PATH` | Thư mục kết quả riêng cho một lượt chạy |
| `--data-dir PATH` | Đường dẫn input đã chuẩn bị hoặc cần xuất |
| `--spider-data PATH` | Bộ Spider gốc; mặc định `downloads/spider_data/` |
| `--evaluate-only` | Chuẩn hóa và chấm lại raw có sẵn, không gọi LLM |
| `--dry-run` | In các bước, không ghi file hay gọi LLM |
| `--codex-model MODEL` | Model Codex; mặc định lấy từ `CODEX_MODEL` |
| `--codex-reasoning-effort low` | Reasoning effort Codex, mặc định `low` |
| `--resume` | Chạy tiếp một lượt `--methods codex_mcp` |
| `--workers 4` | Chạy đồng thời tối đa 4 câu Codex; mặc định 1 |

Tên phương pháp cho `--methods`: `few_shot` (DIN-SQL), `mac_sql`, `dail_sql`, `codex_mcp`.
Nếu không truyền `--methods`, chỉ chạy ba phương pháp gốc.
Điểm của lượt chạy chỉ gồm các phương pháp đã chọn.

Để xem trước luồng chạy:

```bash
uv run --no-project python scripts/run_comparison.py --dry-run
```

Script không ghi đè raw inference đã có. Để chạy mới, chọn `--output` khác:

```bash
uv run --no-project python scripts/run_comparison.py --output results/full_dev_new
```

Chấm lại raw của ba phương pháp mặc định:

```bash
uv run --no-project python scripts/run_comparison.py --evaluate-only
```

## DAIL-SQL

Mỗi lượt dùng `dail_work/` trong thư mục output để stage dữ liệu, schema linking
và prompt. Script dùng `.venv` của DAIL-SQL và giữ riêng workspace giữa các lượt.
Lượt đầu sinh SQL sơ bộ; lượt cuối chọn 9 ví dụ QA từ câu hỏi và cấu trúc SQL sơ bộ
vừa sinh, rồi tạo SQL cuối. Mỗi lượt inference dùng `n=1` và đúng số câu đã chọn.

Script tự đặt đường dẫn tài nguyên theo layout trong repo DAIL-SQL. Nếu Java hoặc
CoreNLP được cài ở vị trí khác, đặt `JAVA_HOME` và `CORENLP_HOME` trước khi chạy.
`HF_HOME` và `SENTENCE_TRANSFORMERS_HOME` mặc định dùng `.cache/` của DAIL.
Bước preprocessing dùng `--tokenize-only`, vẫn xử lý cả dữ liệu train để chọn ví dụ.

## Codex MCP SQL

Sau khi [cài môi trường riêng](setup.md#codex-mcp-sql), chạy full dev:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna \
  --codex-reasoning-effort low --workers 4 --output results/codex_full_dev
```

Model Codex dùng xác thực Codex/OpenAI, không dùng proxy `LLM_BASE_URL` của ba
phương pháp gốc. Khi model hoặc cấu hình inference khác nhau, đây là so sánh
hệ thống, không chỉ cách prompting. Model, effort và ngân sách được lưu trong
`raw/codex_mcp/metadata.json`; mặc định mỗi câu 20 tool calls, 180 giây toàn phiên,
5 giây mỗi SQL và tối đa 100 dòng tool trả về.

Runner nhận `examples.json` đã chọn đúng số câu và database chung. Output và
checkpoint nằm trong `raw/codex_mcp/`, log ở `raw/codex_mcp.log`.
Comparison chuẩn hóa thành `predictions/codex_mcp.jsonl`, rồi chấm cùng evaluator
SQLite. Nếu mọi câu đã được thử nhưng có câu lỗi, prediction rỗng vẫn tính sai.
Nếu còn câu chưa chạy hoặc hết usage, script dừng trước bước chuẩn hóa/chấm;
`--evaluate-only` cũng từ chối run chưa hoàn tất.

Sau khi usage được cấp lại, dùng cùng lệnh và thêm `--resume`. Chỉ chọn
`--methods codex_mcp` khi resume để không chạy lại các phương pháp khác.
Input, model, effort và ngân sách phải khớp lượt đầu. Log được nối tiếp và runner
giữ trace cũ trong `raw/codex_mcp/attempts/`.
Số worker có thể thay đổi khi resume. Mỗi worker dùng SDK/MCP và thư mục tạm
riêng; kết quả vẫn giữ đúng thứ tự câu. Khi hết usage, runner ngừng nhận câu
mới, chờ các câu đang chạy lưu kết quả rồi dừng. Ctrl+C hủy các câu đang chạy
và giữ checkpoint để tiếp tục sau.

Có thể thêm Codex vào kết quả ba phương pháp đã có tại `results/full_dev/`:

```bash
# Chỉ inference Codex; tái sử dụng input/database chung
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna --output results/full_dev

# Chấm lại cả bốn từ raw đã có; không chạy lại inference ba phương pháp gốc
uv run --no-project python scripts/run_comparison.py \
  --methods few_shot mac_sql dail_sql codex_mcp \
  --output results/full_dev --evaluate-only
```

Mỗi lần chấm thay báo cáo bằng các phương pháp được chọn; lệnh cuối tạo bảng đủ
bốn phương pháp. Nếu muốn inference mới cả bốn, truyền cùng danh sách `--methods`
và chọn một `--output` mới.

## Đọc kết quả

Các đường dẫn dưới đây tính từ thư mục output:

| Nội dung | Đường dẫn |
|---|---|
| Output phương pháp và log inference | `raw/` |
| SQL chuẩn hóa, cùng ID và thứ tự | `predictions/` |
| Điểm SQLite EX | `summary.csv` |
| EX theo độ khó | `report.md`, `by_difficulty.csv` |
| Input, log và lệnh chấm SQLite | `evaluation/` |
| Đúng/sai và lỗi SQLite từng câu | `evaluation/<method>.details.json` |

Input chung gồm `dev.json`, `examples.json`, `tables.json`, `gold.txt`,
`subset.json` (đủ ID được chọn) và `source.json` (checksum dữ liệu/database).
Script từ chối input có danh sách ID khác số câu yêu cầu.

Chuẩn hóa bỏ backtick an toàn và comment ngoài literal, giữ giá trị và thứ tự.
Prediction thiếu vẫn tính sai. Mã Spider chỉ phân loại độ khó của gold SQL;
prediction được thực thi trực tiếp bằng SQLite.
SQLite chạy query read-only, mặc định giới hạn 10 giây mỗi query, giữ DISTINCT,
literal và số dòng trùng; cho phép hoán vị cột nhất quán và xét thứ tự khi gold
có ORDER BY ngoài cùng. UTF-8 lỗi được bỏ qua khi giải mã; lỗi gold làm lượt chấm
thất bại. Đây là EX trên một database cho mỗi câu, không phải test-suite accuracy.

[Báo cáo đã công bố](../results/full_dev/report.md) và hai CSV cạnh nó tổng hợp
ba phương pháp gốc từ `results/full_dev/` với Codex từ `results/codex_full_dev/`.
Đó là hai thư mục raw riêng. Chạy `--evaluate-only` mặc định chỉ chấm ba phương
pháp và sẽ thay báo cáo bằng ba dòng; chọn output khác nếu muốn giữ bản tổng hợp.
Lệnh chấm cả bốn trong một output ở trên chỉ dùng khi output đó đã có raw cả bốn.
Phạm vi audit bổ sung được mô tả trong [ghi chú kiểm tra prediction](prediction-audit.md).
