# Cách chạy

Chạy từ thư mục `text2sql-comparison/`. Máy hiện tại đã có dữ liệu và môi trường.
Nếu cài lại từ đầu, xem [setup.md](setup.md).

## 1. Nạp cấu hình

```bash
export COMPARISON="$PWD"
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a
```

`.env` chứa endpoint, model và API key; file này được Git bỏ qua.
Mỗi lệnh bên dưới dùng `uv` để chạy đúng `.venv` của repo đó.

## 2. Chuẩn bị 20 câu

```bash
uv run --no-project python scripts/prepare_data.py \
  --spider-data downloads/spider_data
```

Danh sách cố định ở `data/subset.json`. Không đổi subset giữa các phương pháp.

## 3. Sinh SQL

Chỉ cần bước này khi muốn chạy inference mới. Để chấm lại output hiện có, sang bước 4.
Dùng đường dẫn output mới nếu muốn giữ một lượt inference cũ; MAC tự tiếp tục file
đang có, còn DIN/DAIL có thể ghi đè output.

### DIN-SQL

```bash
(
  cd ../Few-shot-NL2SQL-with-prompting
  uv run --no-project python DIN-SQL.py \
    --dataset "$COMPARISON/data/" \
    --output "$COMPARISON/results/raw/few_shot.txt"
)
```

Dấu `/` cuối `--dataset` là bắt buộc.

### MAC-SQL

```bash
(
  cd ../MAC-SQL
  uv run --no-project python run.py \
    --dataset_name spider --dataset_mode dev \
    --input_file "$COMPARISON/data/dev.json" \
    --db_path "$COMPARISON/downloads/spider_data/database" \
    --tables_json_path "$COMPARISON/data/tables.json" \
    --output_file "$COMPARISON/results/raw/mac_sql.jsonl" \
    --log_file "$COMPARISON/results/raw/mac_sql_trace/log.txt"
)
```

### DAIL-SQL

Xem [dail-sql.md](dail-sql.md). Phương pháp này cần CoreNLP và chạy hai lượt.

## 4. Chuẩn hóa và chấm điểm

```bash
uv run --no-project python scripts/normalize_few_shot.py --raw results/raw/few_shot.txt
uv run --no-project python scripts/normalize_mac_sql.py --raw results/raw/mac_sql.jsonl
uv run --no-project python scripts/normalize_dail_sql.py --raw results/raw/dail_sql.txt
uv run --no-project python scripts/evaluate.py \
  --db downloads/spider_data/database --table data/tables.json \
  --prediction few_shot=results/predictions/few_shot.jsonl \
  --prediction mac_sql=results/predictions/mac_sql.jsonl \
  --prediction dail_sql=results/predictions/dail_sql.jsonl
```

- Điểm: `results/summary.csv`.
- SQL đã chuẩn hóa: `results/predictions/`.
- Input và log evaluator: `results/evaluation/`.
- Thông tin phiên bản và các sửa đổi: [versions.md](versions.md).

Bước này giữ nguyên raw, bỏ backtick an toàn và comment ngoài chuỗi. Câu thiếu vẫn
được tính sai. Evaluator gốc được giữ nguyên; alias cột vẫn có thể bị parser từ chối.

## 5. Kiểm thử

```bash
uv run --no-project python -m unittest discover -s tests -v
```

## Format code

```bash
uv run --no-project ruff format .
uv run --no-project ruff format --check .
```

Ruff chỉ format mã trong repo comparison; bỏ qua dữ liệu, kết quả và downloads.
