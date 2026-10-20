# Kiểm tra prediction bị chấm sai

Phạm vi: lượt `codex_mcp` trên 1.034 câu Spider dev. Kiểm tra này chưa được
thực hiện cho ba phương pháp còn lại; không suy rộng kết luận sang các lượt đó.

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

Bốn trace từng bị validator từ chối vì dấu `;` cuối SQL đã được khôi phục bằng
validator đã sửa, không gọi model thêm. Báo cáo dùng kết quả sau resume/retry
các câu lỗi và sau bước khôi phục này.

Xem [báo cáo so sánh](../results/full_dev/report.md).
