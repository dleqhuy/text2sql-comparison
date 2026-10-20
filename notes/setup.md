# Cài môi trường bằng uv

Comparison, DIN-SQL, MAC-SQL và DAIL-SQL dùng Python 3.9; Codex MCP SQL dùng
Python 3.12. Mỗi repo có môi trường riêng. Chỉ cài các phương pháp cần chạy.

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

## Codex MCP SQL

Baseline này dùng Python 3.12 trong môi trường riêng. Cần repo
[codex-mcp-sql](https://github.com/dleqhuy/codex-mcp-sql) nằm cạnh comparison:

```bash
# Clone nếu workspace chưa có repo này
git clone https://github.com/dleqhuy/codex-mcp-sql.git ../codex-mcp-sql
uv sync --project ../codex-mcp-sql --locked
```

Dùng Codex login có `auth.json`, hoặc đặt `CODEX_API_KEY`/`OPENAI_API_KEY`.
Model lấy từ `--codex-model` hoặc `CODEX_MODEL` trong `.env` đã source.
`codex_mcp` không cần `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, Java hay CoreNLP;
comparison vẫn cần NLTK để phân loại độ khó gold khi chấm điểm.
Không cần cài SDK vào môi trường Python 3.9 của comparison.

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
