# Chạy DAIL-SQL

Nạp cấu hình ở bước 1 của [commands.md](commands.md), rồi chạy từ `DAIL-SQL/`.
Workspace hiện tại đã có dữ liệu, Java, CoreNLP và model embedding.

Nếu tạo workspace mới, tải CoreNLP theo [README gốc](../../DAIL-SQL/README.md),
cài Java 11 và đặt các đường dẫn môi trường bên dưới theo máy của bạn.
DAIL dùng checkpoint `sentence-transformers/all-mpnet-base-v2`.

## Chuẩn bị dữ liệu khi cài mới

Trong `dataset/spider/`, liên kết/copy `dev.json`, `tables.json` từ
`text2sql-comparison/data/`, và `gold.txt` thành `dev_gold.sql`.
Liên kết `database/`, `train_spider.json`, `train_others.json`, `train_gold.sql`
từ bộ Spider đã tải. Tạo `mini_dev_index.json` chứa mảng các số từ 0 đến 19.
Giữ đúng subset và thứ tự; không dùng cache của toàn bộ dev cho subset này.

## Lệnh chạy trên máy hiện tại

```bash
cd ../DAIL-SQL
export JAVA_HOME="$PWD/third_party/java11/jdk-11.0.32.1+1-jre/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
export CORENLP_HOME="$PWD/third_party/stanford-corenlp-full-2018-10-05"
export HF_HOME="$PWD/.cache/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$PWD/.cache/sentence-transformers"
export TOKENIZERS_PARALLELISM=false
export DAIL_CACHE_CELL_MATCHES=1

uv run --no-project python data_preprocess.py --tokenize-only

uv run --no-project python generate_question.py \
  --data_type spider --split test --tokenizer gpt-3.5-turbo \
  --max_seq_len 4096 --prompt_repr SQL --k_shot 9 --example_type QA \
  --selector_type EUCDISQUESTIONMASK

PRELIM=dataset/process/SPIDER-TEST_SQL_9-SHOT_EUCDISQUESTIONMASK_QA-EXAMPLE_CTX-200_ANS-4096
uv run --no-project python ask_llm.py --n 1 --end_index 20 --question "$PRELIM"

uv run --no-project python generate_question.py \
  --data_type spider --split test --tokenizer gpt-3.5-turbo \
  --max_seq_len 4096 --prompt_repr SQL --k_shot 9 --example_type QA \
  --selector_type EUCDISMASKPRESKLSIMTHR \
  --pre_test_result "$PRELIM/RESULTS_MODEL-cx_gpt-6-luna.txt"

FINAL=dataset/process/SPIDER-TEST_SQL_9-SHOT_EUCDISMASKPRESKLSIMTHR_QA-EXAMPLE_CTX-200_ANS-4096
uv run --no-project python ask_llm.py --n 1 --end_index 20 --question "$FINAL"
cp "$FINAL/RESULTS_MODEL-cx_gpt-6-luna.txt" "$COMPARISON/results/raw/dail_sql.txt"
cd "$COMPARISON"
```

Lượt cuối phải dùng SQL sơ bộ vừa sinh, không dùng gold hoặc kết quả GPT-4 đi kèm repo.
Tên file kết quả trên ứng với model hiện tại `cx/gpt-6-luna`; đổi tên nếu đổi model.
`--tokenize-only` và cache giúp preprocessing nhanh hơn; quy tắc linking giữ nguyên.
Tiếp tục bước chuẩn hóa/chấm điểm trong [commands.md](commands.md).
