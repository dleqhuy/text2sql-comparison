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
Các bước inference gọi endpoint LLM trong `.env`.

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

Tên phương pháp cho `--methods`: `few_shot` (DIN-SQL), `mac_sql`, `dail_sql`.
Điểm của lượt chạy chỉ gồm các phương pháp đã chọn.

Để xem trước luồng chạy:

```bash
uv run --no-project python scripts/run_comparison.py --dry-run
```

Script không ghi đè raw inference đã có. Để chạy mới, chọn `--output` khác:

```bash
uv run --no-project python scripts/run_comparison.py --output results/full_dev_new
```

Chấm lại kết quả hiện có:

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
