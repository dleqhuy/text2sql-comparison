# MAC-SQL (`mac_sql`)

[Tổng quan các phương pháp](methods.md) · [Cấu hình và phiên bản](versions.md)

## Luồng xử lý

```text
Câu hỏi + schema + khóa ngoại + giá trị mẫu trong database
    |
    v
Selector: thu gọn bảng/cột khi schema đủ lớn để cần pruning
    |
    v
Decomposer: phân rã câu hỏi và sinh SQL
    |
    v
Refiner: chạy SQL trên SQLite
    |
    +-- Chạy thành công -------------------> SQL cuối
    |
    +-- Có lỗi -> LLM sửa từ SQL + lỗi -> Refiner kiểm tra lại
                  (giới hạn bởi MAX_ROUND=3 của ChatManager)
```

Selector có thể giữ nguyên schema nhỏ mà không gọi LLM để pruning. Với Spider,
Refiner yêu cầu sửa khi thực thi lỗi; kết quả rỗng hoặc có NULL không tự động
kích hoạt sửa. Vòng lặp có giới hạn, nên SQL cuối vẫn có thể lỗi hoặc sai nghĩa.
Ba agent này được điều phối trong `ChatManager`, không phải ba model riêng.

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
  --methods mac_sql --count 20 --output results/mac_guide20
```

- Output thô: `raw/mac_sql.jsonl`; log tiến trình: `raw/mac_sql.log`.
- Trace: `raw/mac_trace/log.txt`; SQL chuẩn hóa: `predictions/mac_sql.jsonl`.
- Mã xử lý: [agents.py](../../MAC-SQL/core/agents.py),
  [chat_manager.py](../../MAC-SQL/core/chat_manager.py).

## Chấm lại và đọc kết quả

Chấm lại raw của đúng lượt chạy trên, không gọi model:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods mac_sql --count 20 --output results/mac_guide20 --evaluate-only
```

Mọi đường dẫn `raw/`, `predictions/`, `evaluation/` ở trên tính từ `--output`.
Mở `report.md` để xem điểm EX và `evaluation/mac_sql.details.json` để xem
đúng/sai, lỗi từng câu. Dùng `index` để đối chiếu SQL ở
`predictions/mac_sql.jsonl` với gold trong `examples.json` của input chung.
SQL chạy được vẫn có thể sai nghĩa; xem [quy tắc chấm](full-dev.md#đọc-kết-quả).

Thêm `--dry-run` vào lệnh inference để xem trước các bước, không gọi model hoặc
ghi output. Xem [tùy chọn chung và xử lý lỗi](methods.md#chạy-và-kiểm-tra-kết-quả).
