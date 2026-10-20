# Cài môi trường bằng uv

Dùng Python 3.9 để tương thích với thư viện của các phương pháp.
Mỗi repo có môi trường riêng.

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
test -f .env || cp .env.example .env
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

## Tài nguyên DAIL-SQL

Cài Java 11 và giải nén CoreNLP 2018-10-05 vào
`../DAIL-SQL/third_party/stanford-corenlp-full-2018-10-05/` theo
[README DAIL-SQL](../../DAIL-SQL/README.md).
Script tự đặt đường dẫn tài nguyên theo layout repo. Nếu cài ở nơi khác, đặt
`JAVA_HOME` và `CORENLP_HOME` theo [hướng dẫn chạy](full-dev.md#dail-sql).

DAIL cần checkpoint `sentence-transformers/all-mpnet-base-v2`.
`HF_HOME` và `SENTENCE_TRANSFORMERS_HOME` trỏ vào `.cache/` của repo DAIL;
lần đầu sử dụng cần kết nối mạng để tải model nếu cache chưa có.

Tiếp tục với [chạy full dev](full-dev.md).
