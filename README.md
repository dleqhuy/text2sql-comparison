# Text-to-SQL Comparison

So sánh DIN-SQL, MAC-SQL và DAIL-SQL trên cùng một subset Spider 1.0.
Mỗi phương pháp chạy trong repo riêng; comparison chỉ chuẩn bị dữ liệu,
chuẩn hóa prediction và chấm Execution Accuracy (EX) bằng evaluator Spider gốc.

## Cấu trúc

```text
text2sql/
├── text2sql-comparison/
│   ├── data/subset.json
│   ├── scripts/
│   ├── tests/
│   ├── notes/
│   └── results/
│       ├── raw/
│       ├── predictions/
│       └── summary.csv
├── Few-shot-NL2SQL-with-prompting/  # DIN-SQL
├── MAC-SQL/
├── DAIL-SQL/
└── spider/                        # evaluator gốc
```

## Cài đặt và chạy

Dùng `uv`, giữ mỗi repo một `.venv` riêng. Xem:

- [Cài đặt](notes/setup.md).
- [Các lệnh chạy](notes/commands.md).
- [Chạy DAIL-SQL](notes/dail-sql.md).
- [Phiên bản và cấu hình thí nghiệm](notes/versions.md).

Sau khi cài môi trường và có dữ liệu, chạy từ repo comparison:

```bash
uv run --no-project python scripts/prepare_data.py --spider-data downloads/spider_data
```

`data/subset.json` cố định 20 câu đầu dev. Script tạo `data/dev.json`,
`data/examples.json`, `data/tables.json` và `data/gold.txt` cho các bước tiếp theo.
Dùng cùng phiên bản dữ liệu, database và thứ tự câu hỏi cho cả ba phương pháp.

Đặt cấu hình LLM trong `.env` theo `.env.example`; file chứa API key được Git bỏ qua.
Lệnh inference và môi trường của từng phương pháp nằm trong hướng dẫn chạy.
Các script comparison không gọi LLM.

## Chuẩn hóa và đánh giá

Lưu output gốc trong `results/raw/`, rồi chạy ba script `normalize_*.py`.
Mỗi file JSONL trong `results/predictions/` có một record cho mỗi câu:

```json
{"example_id": "dev_0000", "db_id": "concert_singer", "question": "How many singers do we have?", "predicted_sql": "SELECT COUNT(*) FROM singer"}
```

Cả ba phương pháp dùng chung quy tắc chuẩn hóa:

- Bỏ backtick quanh tên đơn giản không trùng từ khóa SQLite.
- Bỏ comment ngoài chuỗi trước khi dồn SQL thành một dòng.
- Giữ giá trị literal, output raw và vị trí các prediction thiếu.

`scripts/evaluate.py` kiểm tra ID, thứ tự và dữ liệu, xuất input cho
[Spider evaluator](https://github.com/taoyds/spider), gọi `evaluation.py --etype exec`
và ghi `results/summary.csv`. Evaluator được giữ nguyên.
Prediction rỗng được biểu diễn bằng SQL không hợp lệ khi chấm để vẫn tính là sai.

## Kết quả chạy thử

Model `cx/gpt-6-luna`, cùng 20 câu `dev_0000`–`dev_0019`:

| Phương pháp | Đúng / tổng | EX |
|---|---:|---:|
| DIN-SQL | 16/20 | 80% |
| MAC-SQL | 17/20 | 85% |
| DAIL-SQL, hai lượt, n=1 | 19/20 | 95% |

Xem [summary.csv](results/summary.csv). Cả 20 câu thuộc `concert_singer`, nên kết quả
này dùng để kiểm tra pipeline, chưa đại diện cho toàn bộ Spider.
MAC còn hai lỗi parser do alias cột; `dev_0016` chạy được nhưng khác gold.

## Format và kiểm thử

```bash
uv run --no-project ruff format .
uv run --no-project ruff format --check .
uv run --no-project python -m unittest discover -s tests -v
```

Khi chạy test, đặt `NLTK_DATA` theo [hướng dẫn](notes/commands.md).
Repo này không quản lý inference hay môi trường chung cho các phương pháp.
