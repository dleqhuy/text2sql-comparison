# DAIL-SQL (`dail_sql`)

[Tổng quan các phương pháp](methods.md) · [Cấu hình và phiên bản](versions.md)

## Luồng xử lý

```text
Train Spider: các cặp câu hỏi/SQL        Các câu dev được chọn
              |                                  |
              +----------------+-----------------+
                               v
              Tiền xử lý, tokenize, schema linking
                               |
                               v
              Lượt 1: chọn 9 ví dụ QA theo câu hỏi đã mask
                               |
                               v
                         LLM sinh SQL sơ bộ
                               |
                               v
              Lượt 2: chọn lại 9 ví dụ QA theo câu hỏi
                      và cấu trúc SQL sơ bộ
                               |
                               v
                         LLM sinh SQL cuối
```

DAIL-SQL tập trung vào chọn ví dụ few-shot phù hợp. Runner dùng selector
`EUCDISQUESTIONMASK` ở lượt đầu và `EUCDISMASKPRESKLSIMTHR` ở lượt cuối;
lượt cuối đọc `raw/dail_preliminary.txt`. Cả hai lượt dùng 9 ví dụ QA, biểu diễn
schema dạng SQL, context 4096, `n=1`. SQL sơ bộ dùng cho chọn ví dụ là output
model của lượt đầu.

Runner stage dữ liệu trong `dail_work/`, chạy preprocessing với `--tokenize-only`
và vẫn xử lý train để chọn ví dụ, kể cả khi chỉ thử 20 câu dev. Cần chuẩn bị
Java/CoreNLP và checkpoint `all-mpnet-base-v2`; xem [setup.md](setup.md#tài-nguyên-dail-sql).

## Chuẩn bị

Chạy từ `text2sql-comparison/`, sau khi [cài môi trường và dữ liệu](setup.md).
Cần Python 3.9 và `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` trong `.env`.
Mỗi phương pháp dùng `.venv` riêng như hướng dẫn cài đặt.

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a
```

Lệnh mẫu dùng 20 câu đầu. Để chạy toàn bộ dev, bỏ `--count 20` và chọn
`--output` mới. Runner tự chuẩn hóa và chấm sau inference; raw đã có sẽ khiến
lượt inference mới bị từ chối.

## Chạy riêng và output

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods dail_sql --count 20 --output results/dail_guide20
```

- SQL: `raw/dail_preliminary.txt` và `raw/dail_sql.txt`.
- Log: `raw/dail_preprocess.log`, `raw/dail_preliminary_prompts.log`,
  `raw/dail_preliminary_inference.log`, `raw/dail_final_prompts.log`,
  `raw/dail_final_inference.log`.
- Dữ liệu trung gian/prompt: `dail_work/dataset/`; SQL chuẩn hóa:
  `predictions/dail_sql.jsonl`.
- Mã xử lý: [data_preprocess.py](../../DAIL-SQL/data_preprocess.py),
  [generate_question.py](../../DAIL-SQL/generate_question.py),
  [ask_llm.py](../../DAIL-SQL/ask_llm.py).

## Chấm lại và đọc kết quả

Chấm lại raw của đúng lượt chạy trên, không gọi model:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods dail_sql --count 20 --output results/dail_guide20 --evaluate-only
```

Mọi đường dẫn `raw/`, `predictions/`, `evaluation/` ở trên tính từ `--output`.
Mở `report.md` để xem điểm EX và `evaluation/dail_sql.details.json` để xem
đúng/sai, lỗi từng câu. Dùng `index` để đối chiếu SQL ở
`predictions/dail_sql.jsonl` với gold trong `examples.json` của input chung.
SQL chạy được vẫn có thể sai nghĩa; xem [quy tắc chấm](full-dev.md#đọc-kết-quả).

Thêm `--dry-run` vào lệnh inference để xem trước các bước, không gọi model hoặc
ghi output. Xem [tùy chọn chung và xử lý lỗi](methods.md#chạy-và-kiểm-tra-kết-quả).
