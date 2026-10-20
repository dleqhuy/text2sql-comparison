# Phiên bản và cấu hình

## Bộ thí nghiệm

- Spider 1.0 dev: 1.034 câu, 20 database, theo thứ tự trong `dev.json` gốc.
- Độ khó theo Spider: 248 easy, 446 medium, 174 hard, 166 extra.
- DIN-SQL, MAC-SQL, DAIL-SQL: model `cx/gpt-6-luna`, endpoint/API key từ `LLM_*`.
- Codex MCP SQL: model `gpt-6-luna`, effort `low`, xác thực Codex/OpenAI.
- Python 3.9.6 cho comparison và ba phương pháp gốc; Python 3.12 cho Codex.
  Mỗi repo có `.venv` riêng trên macOS Apple Silicon.
- Ruff 0.17.1 cho mã comparison.

## Cấu hình phương pháp

| Phương pháp | Cấu hình |
|---|---|
| DIN-SQL | Temperature 0; tối đa 600 token khi sinh, 350 token khi debug |
| MAC-SQL | Selector, Decomposer, Refiner; cấu hình mặc định của repo/provider |
| DAIL-SQL | Hai lượt; 9 ví dụ QA; context 4096; tối đa 200 token; temperature 0; n=1 |
| Codex MCP SQL | AsyncCodex; thread ephemeral mỗi câu; SQLite MCP; effort low; tối đa 4 worker; 20 tool calls và 180 giây/câu; 5 giây/SQL; 100 dòng/tool |

Codex dùng Python 3.12 và dependency trong `codex-mcp-sql/uv.lock` (SDK 0.163.0
tại thời điểm tích hợp). Model chọn bằng `--codex-model`/`CODEX_MODEL`, độc lập với
`LLM_MODEL`; metadata của mỗi run ghi model/effort và phiên bản runtime thực tế.
Kết quả cả bốn phương pháp nằm trong [báo cáo full dev](../results/full_dev/report.md).
Backend, công cụ và cấu hình inference khác nhau; đây là so sánh hệ thống.

DAIL dùng `sentence-transformers/all-mpnet-base-v2`, CoreNLP 2018-10-05 và Java 11.
Bộ đếm token của DAIL checkout gốc trả 0, nên phần ước tính token/chi phí của nó
không dùng để báo cáo chi phí thực tế.

## Mã nguồn gốc

| Repo | Commit gốc |
|---|---|
| DIN-SQL | `fe9d2ea39711dafaba7e0f0621513b9ab9646187` |
| MAC-SQL | `f8ca56f20192fe85b65a2542f917f820910e80d6` |
| DAIL-SQL | `7df99e15d8916a35711ff13735fd5ee01262c10e` |
| Spider (độ khó gold) | `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c` |

Các commit phương pháp đang dùng, gồm điều chỉnh tương thích bên dưới:

| Repo | Commit |
|---|---|
| DIN-SQL | `be08d838ce1cc1a4d465b3f34bb4d493d21cb10a` |
| MAC-SQL | `53e7ebf` |
| DAIL-SQL | `0f6d7ec` |
| Codex MCP SQL | `2aa92fa` |

Thư viện runtime nằm trong [dependencies/](dependencies/), checksum tài nguyên
và các file tương thích được liệt kê nằm trong [checksums.sha256](checksums.sha256).
Checksum bộ dữ liệu và database nằm trong `data/dev_full/source.json`.

## Điều chỉnh tương thích

- DIN-SQL, MAC-SQL và DAIL-SQL đọc endpoint/model/API key từ `LLM_*`.
- Codex dùng SDK/MCP riêng, checkpoint/resume và worker song song; validator
  chấp nhận dấu `;` cuối SQL khi đối chiếu với truy vấn đã thử thành công.
- DIN xử lý phản hồi chat/Markdown, giới hạn retry và lưu từng prediction.
- MAC trích xuất được cả khối Markdown SQL và SQL thuần bắt đầu bằng SELECT/WITH.
- DAIL giữ `AS (` khi chuẩn hóa CTE; bỏ tải vector GloVe không dùng và cache
  tra cứu giá trị, giữ nguyên quy tắc linking.
- Chuẩn hóa chung bỏ backtick an toàn và comment ngoài chuỗi trước khi dồn dòng.
- EX chấm bằng SQLite; mã Spider chỉ phân loại độ khó của gold SQL.

Kết quả và cách chạy được mô tả tại [README](../README.md) và [full-dev.md](full-dev.md).
