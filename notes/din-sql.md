# DIN-SQL (`few_shot`)

[Tổng quan các phương pháp](methods.md) · [Cấu hình và phiên bản](versions.md)

## Luồng xử lý

```text
Câu hỏi + bảng/cột + khóa chính/khóa ngoại
    |
    v
[LLM 1] Schema linking: xác định cột, liên kết, giá trị liên quan
    |
    v
[LLM 2] Phân loại độ phức tạp
    |
    +-- EASY -------> prompt SQL đơn giản
    +-- NON-NESTED -> prompt suy luận JOIN, không truy vấn lồng
    +-- NESTED -----> prompt có câu hỏi con cho truy vấn lồng
                         |
                         v
                   [LLM 3] SQL ứng viên
                         |
                         v
                   [LLM 4] Debug bằng prompt
                         |
                         v
                     SQL cuối
```

Ví dụ trong prompt được viết sẵn trong `DIN-SQL.py`. Bước debug nhận câu hỏi,
schema và SQL ứng viên để yêu cầu LLM sửa; không nhận lỗi thực thi SQLite.
Một câu đi qua bốn bước gọi LLM khi không có retry. Nhãn EASY/NON-NESTED/NESTED
là nhãn nội bộ DIN-SQL, khác bốn mức độ khó Spider trong báo cáo.

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
  --methods few_shot --count 20 --output results/din_guide20
```

- SQL thô: `raw/few_shot.txt`; lỗi từng câu: `raw/few_shot.txt.errors.jsonl`.
- Log: `raw/few_shot.log`; SQL chuẩn hóa: `predictions/few_shot.jsonl`.
- Mã xử lý: [DIN-SQL.py](../../Few-shot-NL2SQL-with-prompting/DIN-SQL.py).

## Chấm lại và đọc kết quả

Chấm lại raw của đúng lượt chạy trên, không gọi model:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods few_shot --count 20 --output results/din_guide20 --evaluate-only
```

Mọi đường dẫn `raw/`, `predictions/`, `evaluation/` ở trên tính từ `--output`.
Mở `report.md` để xem điểm EX và `evaluation/few_shot.details.json` để xem
đúng/sai, lỗi từng câu. Dùng `index` để đối chiếu SQL ở
`predictions/few_shot.jsonl` với gold trong `examples.json` của input chung.
SQL chạy được vẫn có thể sai nghĩa; xem [quy tắc chấm](full-dev.md#đọc-kết-quả).

Thêm `--dry-run` vào lệnh inference để xem trước các bước, không gọi model hoặc
ghi output. Xem [tùy chọn chung và xử lý lỗi](methods.md#chạy-và-kiểm-tra-kết-quả).
