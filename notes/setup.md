# Cài môi trường bằng uv

Máy hiện tại đã có bốn `.venv`. Các lệnh tạo môi trường dưới đây dành cho workspace
mới; dùng Python 3.9 để tương thích với thư viện cũ của các phương pháp.

Chạy từ `text2sql-comparison/`, với `uv` đã được cài:

```bash
uv venv --python 3.9 .venv
uv pip install --python .venv/bin/python -r notes/dependencies/comparison.txt
uv pip install --python .venv/bin/python --group dev

uv venv --python 3.9 ../Few-shot-NL2SQL-with-prompting/.venv
uv pip install --python ../Few-shot-NL2SQL-with-prompting/.venv/bin/python -r notes/dependencies/din-sql.txt

uv venv --python 3.9 ../MAC-SQL/.venv
uv pip install --python ../MAC-SQL/.venv/bin/python -r notes/dependencies/mac-sql.txt

uv venv --python 3.9 ../DAIL-SQL/.venv
uv pip install --python ../DAIL-SQL/.venv/bin/python -r notes/dependencies/dail-sql.txt
```

Các file trên ghi phiên bản runtime cần dùng từ lượt chạy trên macOS Apple Silicon;
chúng không phải bộ lock đa nền tảng. Mỗi repo giữ môi trường riêng.
`uv pip` dùng được với `.venv` và requirements hiện có; xem
[tài liệu uv](https://docs.astral.sh/uv/pip/environments/).

## Tokenizer và API

```bash
uv run --no-project python -m nltk.downloader \
  -d /private/tmp/text2sql-nltk punkt punkt_tab stopwords
cp .env.example .env
```

Chỉ copy `.env.example` khi chưa có `.env`, rồi điền API key. Không ghi đè cấu hình
đang dùng. Tokenizer nằm trong thư mục tạm; tải lại nếu máy đã dọn thư mục này.

## Dữ liệu

Tải [Spider 1.0 chính thức](https://yale-lily.github.io/spider), giải nén để có:

```text
downloads/spider_data/
  dev.json
  tables.json
  database/
  train_spider.json
  train_others.json
  train_gold.sql
```

DAIL còn cần Java, CoreNLP và model embedding; xem [dail-sql.md](dail-sql.md).
Sau đó làm theo [commands.md](commands.md).
