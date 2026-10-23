# Các phương pháp hoạt động và chạy như thế nào?

Tài liệu mô tả **implementation đang được runner của workspace sử dụng**.
Tên `few_shot` trong CLI tương ứng với DIN-SQL, không phải một baseline few-shot
khác. Xem [cài môi trường](setup.md) trước khi chạy; cấu hình chi tiết nằm ở
[versions.md](versions.md).

## Hướng dẫn từng phương pháp

Mỗi file có sơ đồ text, phần chuẩn bị, lệnh chạy riêng, vị trí log/output và
lệnh chấm lại:

- [DIN-SQL (`few_shot`)](din-sql.md)
- [MAC-SQL (`mac_sql`)](mac-sql.md)
- [DAIL-SQL (`dail_sql`)](dail-sql.md)
- [Codex MCP SQL (`codex_mcp`)](codex-mcp-sql.md)

## Luồng chung

```text
Spider: dev.json + tables.json + database/
                |
                v
prepare_data.py: chọn toàn bộ dev hoặc N câu đầu, giữ ID/thứ tự
                |
                v
data/dev_full/ hoặc data/smokeN/
                |
                v
run_comparison.py: chạy lần lượt các phương pháp đã chọn
                |
       +--------+---------+----------+-----------+
       |                  |          |           |
    DIN-SQL            MAC-SQL    DAIL-SQL   Codex MCP SQL
       |                  |          |           |
       +------------------+----------+-----------+
                          |
                          v
                   raw/ + log/trace
                          |
                          v
             normalize_<method>.py
                          |
                          v
             predictions/<method>.jsonl
                          |
                          v
     evaluate.py: thực thi prediction và gold trên SQLite
                          |
                          v
       summary.csv + by_difficulty.csv + report.md
```

Các phương pháp dùng cùng câu hỏi, schema và database được chọn. Gold SQL dùng
để chấm sau inference. SQLite EX so kết quả thực thi; SQL chạy được chưa chắc
trả lời đúng câu hỏi. Đây là EX trên một database mỗi câu, không phải test-suite
accuracy. [Quy tắc chấm và đọc kết quả](full-dev.md#đọc-kết-quả) mô tả chi tiết hơn.

| Phương pháp / CLI | Cách sinh SQL | Dùng SQLite trong inference? | Tài nguyên riêng |
|---|---|---|---|
| DIN-SQL / `few_shot` | Schema linking → phân loại → sinh SQL → sửa bằng prompt | Không | Python 3.9, `LLM_*` |
| MAC-SQL / `mac_sql` | Selector → Decomposer → Refiner | Có, để kiểm tra và sửa lỗi | Python 3.9, `LLM_*` |
| DAIL-SQL / `dail_sql` | Chọn ví dụ → SQL sơ bộ → chọn lại ví dụ → SQL cuối | Không có vòng thực thi SQL để sửa lỗi trong pipeline này | Python 3.9, `LLM_*`, train Spider, Java/CoreNLP, embedding |
| Codex MCP SQL / `codex_mcp` | Khám phá schema và thử SQL qua MCP | Có; SQL cuối phải khớp truy vấn đã thử thành công | Python 3.12, Codex/OpenAI auth, model Codex |

MAC-SQL còn đọc giá trị mẫu từ database để tạo mô tả schema. DAIL-SQL có bước
schema linking với giá trị trong database; điều này khác với việc thực thi SQL
ứng viên rồi lấy lỗi để sửa.

## Chuẩn bị lệnh chạy

Tất cả lệnh dưới đây chạy từ `text2sql-comparison/`, sau khi cài dependency và
đặt dữ liệu theo [setup.md](setup.md):

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a
```

Ba phương pháp gốc cần `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` trong `.env`.
Codex dùng xác thực riêng, model lấy từ `--codex-model` hoặc `CODEX_MODEL`.
Các tên model trong ví dụ là cấu hình của thí nghiệm đã lưu; thay bằng model
mà endpoint hoặc tài khoản của bạn hỗ trợ khi cần.

Mỗi ví dụ dùng 20 câu đầu để kiểm tra pipeline. Muốn chạy toàn bộ dev, bỏ
`--count 20` và chọn một `--output` mới. Runner tự chuẩn hóa và chấm sau inference.
Raw đã có sẽ khiến lượt inference mới bị từ chối; đổi output khi chạy lại.

## Chạy và kiểm tra kết quả

Xem trước lệnh cho cả bốn phương pháp, không gọi model hoặc ghi file:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods few_shot mac_sql dail_sql codex_mcp \
  --codex-model gpt-6-luna --count 20 \
  --output results/all_guide20 --dry-run
```

Bỏ `--dry-run` để inference thật. Các phương pháp chạy lần lượt theo danh sách;
`--workers 4` nếu thêm vào chỉ làm các câu của Codex chạy đồng thời.
Model/backend của Codex và ba phương pháp gốc có thể khác nhau, nên cần đọc
cấu hình cùng điểm EX khi so sánh hệ thống.

Ví dụ chấm lại riêng DIN-SQL từ raw của lượt chạy cả bốn phía trên, không gọi LLM:

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods few_shot --count 20 --output results/all_guide20 --evaluate-only
```

Mọi đường dẫn `raw/`, `predictions/`, `evaluation/` ở tài liệu này đều tính từ
`--output`. Mở `report.md` để xem tổng quan và
`evaluation/<method>.details.json` để xem đúng/sai và lỗi từng câu. Dùng `index`
trong details để đối chiếu SQL ở `predictions/<method>.jsonl` và gold ở
`examples.json` trong thư mục input chung.
Chấm lại sẽ cập nhật báo cáo trong output bằng các phương pháp được chọn.

| Hiện tượng | Cách xử lý |
|---|---|
| Thiếu `LLM_*` | Điền `.env` và chạy lại đoạn `set -a; source .env; set +a` |
| Thiếu `.venv/bin/python` | Cài môi trường riêng của phương pháp theo `setup.md` |
| `Existing output` hoặc `Existing DAIL workspace` | Dùng output mới để inference; dùng `--evaluate-only` nếu chỉ chấm lại |
| DAIL lỗi Java/CoreNLP/model cache | Kiểm tra tài nguyên, `JAVA_HOME`, `CORENLP_HOME` và các log DAIL |
| Codex dừng vì usage/còn pending | Xem `summary.json`, rồi dùng cùng lệnh với `--resume` khi có thể chạy tiếp |
| SQL chạy được nhưng EX sai | Dùng index trong details để đối chiếu prediction/gold; kiểm tra JOIN, điều kiện, GROUP BY và ORDER BY |

Các lệnh nâng cao, thêm Codex vào run cũ và lưu ý về báo cáo đã có nằm ở
[full-dev.md](full-dev.md).
