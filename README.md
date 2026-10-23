# Text-to-SQL Comparison

So sánh DIN-SQL, MAC-SQL, DAIL-SQL và Codex MCP SQL trên **toàn bộ Spider 1.0 dev**:
1.034 câu, 20 database, cùng ID và thứ tự. Cả bốn dùng chung luồng chuẩn hóa và
chấm SQLite EX. Cấu hình model/backend nằm trong [báo cáo so sánh](results/full_dev/report.md).
Mặc định CLI chạy DIN-SQL, MAC-SQL và DAIL-SQL; chọn cả bốn bằng
`--methods few_shot mac_sql dail_sql codex_mcp`.

## Chạy

Giới thiệu dữ liệu: [Spider 1.0, cấu trúc mẫu, train/dev và cách chấm](notes/dataset.md).

1. [Cài môi trường và tài nguyên](notes/setup.md).
2. [Chạy full dev và chấm điểm](notes/full-dev.md).
3. [Tổng quan luồng xử lý](notes/methods.md) và hướng dẫn riêng:
   [DIN-SQL](notes/din-sql.md), [MAC-SQL](notes/mac-sql.md),
   [DAIL-SQL](notes/dail-sql.md), [Codex MCP SQL](notes/codex-mcp-sql.md).
4. [Cấu hình phương pháp và phiên bản](notes/versions.md).

Cần kiểm tra pipeline trước: [chạy thử 20 câu](notes/smoke20.md).

Mỗi phương pháp dùng repo và `.venv` riêng. Ba phương pháp gốc đọc `LLM_*`
từ `.env`; Codex dùng xác thực Codex/OpenAI và `CODEX_MODEL` hoặc `--codex-model`.
Xem `.env.example` và [hướng dẫn cài đặt](notes/setup.md).
Script chung: `scripts/run_comparison.py`; mặc định full dev, dùng `--count 20`
để chạy thử. Các tùy chọn nằm trong [hướng dẫn chạy](notes/full-dev.md).

Chạy riêng Codex trên 3 câu, sau khi [cài môi trường Codex](notes/setup.md#codex-mcp-sql):

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna \
  --count 3 --output results/codex_smoke3
```

Thêm `--resume` vào cùng lệnh để chạy tiếp khi hết usage; xem
[cách chạy Codex và chấm cùng các phương pháp khác](notes/full-dev.md#codex-mcp-sql).
Thêm `--workers 4` để Codex xử lý đồng thời 4 câu, kể cả khi resume.

```text
text2sql/
├── text2sql-comparison/
│   ├── data/dev_full/           # Input chung cho 1.034 câu
│   ├── scripts/                 # Chạy, chuẩn hóa và chấm điểm
│   ├── tests/
│   ├── notes/
│   └── results/full_dev/
│       ├── raw/                 # Output phương pháp
│       ├── predictions/         # SQL chuẩn hóa, cùng ID và thứ tự
│       ├── evaluation/          # Input, log và kết quả SQLite từng câu
│       ├── summary.csv
│       ├── by_difficulty.csv
│       └── report.md
├── Few-shot-NL2SQL-with-prompting/
├── MAC-SQL/
├── DAIL-SQL/
├── codex-mcp-sql/
└── spider/
```

## Kết quả full dev

| Phương pháp | SQLite EX |
|---|---:|
| DIN-SQL | 82,01% |
| MAC-SQL | 81,43% |
| DAIL-SQL | 82,79% |
| Codex MCP SQL | 76,69% |

Cả bốn có đủ 1.034 prediction không rỗng. Độ khó: 248 easy, 446 medium,
174 hard, 166 extra. Xem [báo cáo so sánh](results/full_dev/report.md) để đọc
cấu hình, EX theo độ khó và phạm vi kiểm tra prediction.

SQLite EX thực thi trực tiếp, giữ DISTINCT, literal và số dòng trùng;
cho phép hoán vị cột nhất quán, xét thứ tự dòng khi gold có ORDER BY ngoài cùng.
Đây là EX trên một database cho mỗi câu, không phải test-suite accuracy.
Mã Spider chỉ được dùng để phân loại độ khó của gold SQL; prediction được thực thi
trực tiếp bằng SQLite.

## Kiểm thử

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
uv run --no-project python -m unittest discover -s tests -v
uv run --no-project ruff format --check .
```
