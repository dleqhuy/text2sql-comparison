# EX theo độ khó

Độ khó được lấy từ evaluator Spider gốc, dựa trên gold SQL.
SQLite EX: thực thi trực tiếp trên một database cho mỗi câu; không phải test-suite accuracy.

| Method | all (n=1034) | easy (n=248) | medium (n=446) | hard (n=174) | extra (n=166) |
|---|---:|---:|---:|---:|---:|
| few_shot | 82.0% | 90.7% | 83.0% | 81.0% | 67.5% |
| mac_sql | 81.4% | 91.9% | 83.4% | 79.3% | 62.7% |
| dail_sql | 82.8% | 92.7% | 85.2% | 82.8% | 61.4% |
| codex_mcp | 76.7% | 89.9% | 80.0% | 70.7% | 54.2% |

`—`: không có câu ở độ khó này, không phải EX bằng 0.

Giữ DISTINCT và số dòng trùng; cho phép hoán vị cột nhất quán; chỉ bắt buộc thứ tự dòng khi gold có ORDER BY ngoài cùng. Không thay giá trị dự đoán bằng giá trị gold.

## Kết quả Codex MCP SQL

Codex đạt **793/1.034 câu đúng (76,69% EX)**, đủ 1.034 prediction không rỗng;
runner hoàn tất 1.034 câu, không còn câu lỗi hoặc chờ chạy.
Dùng `gpt-6-luna`, reasoning effort `low`, tối đa 4 worker; mỗi câu có ngân sách
20 tool calls, 180 giây toàn phiên, 5 giây mỗi SQL và tối đa 100 dòng tool trả về.

Ba phương pháp gốc dùng `cx/gpt-6-luna` qua proxy; Codex dùng Python SDK
`openai-codex==0.163.0` và xác thực Codex/OpenAI. Vì endpoint, công cụ và cấu hình
inference khác nhau, bảng này so sánh các hệ thống, không cô lập tác động prompting.
Điểm Codex là kết quả sau khi resume/retry các câu lỗi; bốn trace cuối được khôi phục
sau sửa validator nhận dấu `;` cuối SQL, không gọi model thêm cho bước khôi phục này.

Bảng và CSV tại đây tổng hợp ba lượt gốc trong `results/full_dev/` và lượt Codex
trong `results/codex_full_dev/`. Raw, prediction và trace Codex vẫn nằm ở thư mục
riêng; đây là các artifact cục bộ, không được đưa vào Git.

## Kiểm tra các câu Codex bị chấm sai

Kiểm tra cả 1.034 câu cho thấy JSON model, SQL lưu trong result/raw, chuẩn hóa,
input evaluator, gold, định tuyến câu hỏi/database và xác nhận MCP đều khớp.
Với riêng **241 câu EX sai**, đã thực thi lại SQL gốc, SQL chuẩn hóa và gold:
không có lỗi thực thi SQLite, không có thay đổi kết quả do chuẩn hóa, không có câu
SQL gốc đúng nhưng bị chuẩn hóa thành sai, và kết quả chấm lại khớp kết quả đã lưu.
Chưa phát hiện lỗi parse hoặc chuẩn hóa gây mất điểm trong lượt này.

| Khác biệt với kết quả gold | Số câu |
|---|---:|
| Khác số cột | 66 |
| Cùng số cột, khác số dòng | 104 |
| Cùng số cột và số dòng, khác giá trị | 71 |
| Tổng | 241 |

Ví dụ: `dev_0026` trả thêm cột COUNT; `dev_0022` dùng LEFT JOIN nên có 9 dòng
thay vì 5; `dev_0101` chọn Accelerate trong khi gold chọn Year. Một số gold có
điểm không khớp rõ với cách diễn đạt câu hỏi, như `dev_0066` hỏi tên nhưng gold
trả cả tuổi. Vì vậy, EX sai là khác kết quả gold trên database hiện có, không tự
động chứng minh mọi SQL đó đều sai theo ý định câu hỏi.

Chi tiết kiểm tra cục bộ: `results/codex_full_dev/audit/parse_audit.json` và
`results/codex_full_dev/audit/wrong_examples.csv`.
