# So sánh Text-to-SQL trên Spider dev

## Dữ liệu và cấu hình

Cả bốn phương pháp dùng 1.034 câu Spider 1.0 dev, 20 database, cùng ID và thứ tự.
Độ khó lấy từ gold SQL bằng evaluator Spider: 248 easy, 446 medium, 174 hard,
166 extra.

| Phương pháp | Model / backend | Cấu hình chính | Nguồn artifact cục bộ |
|---|---|---|---|
| DIN-SQL (`few_shot`) | `cx/gpt-6-luna` / proxy LLM | Temperature 0; tối đa 600 token sinh, 350 token debug | `results/full_dev/` |
| MAC-SQL (`mac_sql`) | `cx/gpt-6-luna` / proxy LLM | Selector, Decomposer, Refiner; mặc định repo/provider | `results/full_dev/` |
| DAIL-SQL (`dail_sql`) | `cx/gpt-6-luna` / proxy LLM | Hai lượt; 9 ví dụ QA; context 4096; tối đa 200 token; temperature 0 | `results/full_dev/` |
| Codex MCP SQL (`codex_mcp`) | `gpt-6-luna` / Codex SDK 0.163.0 | Effort low; tối đa 4 worker; 20 tool calls, 180 giây/câu; 5 giây/SQL; 100 dòng/tool | `results/codex_full_dev/` |

Đây là so sánh hệ thống: backend, công cụ và cấu hình inference khác nhau nên
kết quả không cô lập tác động của prompting. Phiên bản và cấu hình chi tiết ở
[notes/versions.md](../../notes/versions.md).

## Kết quả

| Phương pháp | Đúng / tổng | SQLite EX | Prediction rỗng |
|---|---:|---:|---:|
| DIN-SQL | 848 / 1.034 | 82,01% | 0 |
| MAC-SQL | 842 / 1.034 | 81,43% | 0 |
| DAIL-SQL | 856 / 1.034 | 82,79% | 0 |
| Codex MCP SQL | 793 / 1.034 | 76,69% | 0 |

DAIL-SQL có EX cao nhất trong lượt so sánh này. Cả bốn có đủ 1.034 prediction.

| Phương pháp | Easy (248) | Medium (446) | Hard (174) | Extra (166) |
|---|---:|---:|---:|---:|
| DIN-SQL | 90,7% | 83,0% | 81,0% | 67,5% |
| MAC-SQL | 91,9% | 83,4% | 79,3% | 62,7% |
| DAIL-SQL | 92,7% | 85,2% | 82,8% | 61,4% |
| Codex MCP SQL | 89,9% | 80,0% | 70,7% | 54,2% |

Số liệu đầy đủ: [summary.csv](summary.csv), [by_difficulty.csv](by_difficulty.csv).
Hai CSV tổng hợp các lượt tại những thư mục nguồn ở bảng cấu hình; raw,
prediction và trace được giữ cục bộ trong từng thư mục, không đưa vào Git.

## Cách chấm và kiểm tra

SQLite EX thực thi trực tiếp trên một database cho mỗi câu; không phải test-suite
accuracy. Evaluator giữ DISTINCT, literal và số dòng trùng; cho phép hoán vị cột
nhất quán và chỉ bắt buộc thứ tự dòng khi gold có ORDER BY ngoài cùng. Không thay
giá trị dự đoán bằng giá trị gold. Mã Spider chỉ phân loại độ khó của gold SQL.

Báo cáo sử dụng prediction cuối đã lưu sau các bước retry và kiểm tra hợp lệ.
Audit bổ sung cho `codex_mcp` kiểm tra pipeline trên 1.034 câu và thực thi lại SQL
gốc, SQL chuẩn hóa, gold của 241 câu EX sai: chưa phát hiện lỗi parse/chuẩn hóa
gây mất điểm, không có lỗi thực thi SQLite. Phạm vi và chi tiết khôi phục trace
được ghi tại [ghi chú kiểm tra prediction](../../notes/prediction-audit.md).
EX sai thể hiện khác kết quả gold trên database hiện có; một số câu hỏi/gold có
thể có cách hiểu khác nhau.
