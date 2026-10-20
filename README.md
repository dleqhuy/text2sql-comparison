# Text-to-SQL Comparison

So sánh DIN-SQL, MAC-SQL và DAIL-SQL trên **toàn bộ Spider 1.0 dev**:
1.034 câu, 20 database, cùng thứ tự và cùng model `cx/gpt-6-luna`.
Hỗ trợ thêm baseline `codex_mcp` qua Python SDK trong repo `codex-mcp-sql`.
Phương pháp này chọn riêng bằng `--methods codex_mcp`; mặc định vẫn chạy ba phương pháp trên.

## Chạy

1. [Cài môi trường và tài nguyên](notes/setup.md).
2. [Chạy full dev và chấm điểm](notes/full-dev.md).
3. [Cấu hình phương pháp và phiên bản](notes/versions.md).

Cần kiểm tra pipeline trước: [chạy thử 20 câu](notes/smoke20.md).

Mỗi phương pháp dùng repo và `.venv` riêng. Cấu hình endpoint, model và API key
trong `.env` theo `.env.example`.
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

Cả ba có đủ 1.034 prediction. Độ khó: 248 easy, 446 medium, 174 hard, 166 extra.
Xem [báo cáo EX](results/full_dev/report.md).

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
