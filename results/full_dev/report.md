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

## Exact Set Match trước và sau chuẩn hóa Spider

Chấm lại cùng 1.034 prediction mỗi phương pháp bằng `spider/evaluation.py`,
`--etype match`, giữ nguyên gold và evaluator; không gọi lại model. “Trước chuẩn
hóa Spider” là prediction đã lưu sau pipeline inference/chuẩn hóa chung, trước
bước thích nghi cú pháp bổ sung cho parser Spider. Cả hai lượt giữ cùng ID,
database, câu hỏi và thứ tự; schema/database được kiểm tra SHA-256 theo dữ liệu
chuẩn bị ban đầu.

| Phương pháp | Đúng EM trước → sau / 1.034 | EM trước | EM sau | Tăng (điểm %) | Lỗi parser trước → sau |
|---|---:|---:|---:|---:|---:|
| DIN-SQL | 608 → 633 | 58,80% | 61,22% | +2,42 | 160 → 128 |
| MAC-SQL | 497 → 560 | 48,07% | 54,16% | +6,09 | 305 → 225 |
| DAIL-SQL | 661 → 683 | 63,93% | 66,05% | +2,13 | 169 → 130 |
| Codex MCP SQL | 193 → 404 | 18,67% | 39,07% | +20,41 | 666 → 341 |

EM ở đây là **Exact Set Match** theo cấu trúc SQL của Spider, không phải so
khớp chuỗi hay execution accuracy. Giữ mặc định `DISABLE_VALUE=True` và
`DISABLE_DISTINCT=True`: EM không kiểm tra giá trị literal và DISTINCT như lượt
SQLite EX ở trên. SQL không parse được được thay bằng cấu trúc SQL rỗng để chấm
theo evaluator gốc; không loại khỏi mẫu số. Lỗi parser Spider không đồng nghĩa
SQL không hợp lệ trong SQLite.

### Chuẩn hóa và kiểm tra ý nghĩa

[Bộ chuẩn hóa](../../scripts/spider_normalize.py) dùng SQLGlot 27.29.0 và schema,
không dùng gold SQL để viết lại prediction. Các quy tắc gồm bỏ dấu nháy ở
identifier đơn giản đã xác định theo scope, đặt alias bảng tường minh và duy
nhất, xử lý alias cột cùng tham chiếu trong các clause, đổi `<>` thành `!=`,
viết `INNER JOIN` thành `JOIN` và bỏ ngoặc quanh identifier/literal đơn lẻ.
Alias đầu ra được scope khác sử dụng qua CTE hoặc derived table được giữ lại;
nhãn cột đầu ra ở ranh giới query có thể được bỏ trong bản dành riêng cho EM.
Không bỏ CAST, DISTINCT, literal, điều kiện NULL hoặc đổi outer join thành inner join.

| Phương pháp | SQL thay đổi, đã đối chiếu SQLite | Giữ nguyên | Giữ bản gốc do lỗi khi chuẩn hóa/kiểm tra |
|---|---:|---:|---:|
| DIN-SQL | 747 | 283 | 4 |
| MAC-SQL | 1.001 | 26 | 7 |
| DAIL-SQL | 1.010 | 19 | 5 |
| Codex MCP SQL | 970 | 58 | 6 |

Cả 3.728 thay đổi được nhận đều cho cùng số cột, cùng giá trị theo vị trí cột
và số lần lặp của dòng khi thực thi trước/sau trên SQLite; giữ thứ tự dòng khi
SQL gốc có ORDER BY ngoài cùng, không hoán vị cột. Không có thay đổi bị loại vì
khác kết quả trong lượt này; 22 câu gặp lỗi khi chuẩn hóa/kiểm tra giữ nguyên
prediction gốc. Kiểm tra trên database hiện có không chứng minh tương đương
trên mọi dữ liệu; 11 kiểm thử bổ sung bao phủ alias trùng tên cột, scope tương
quan, CTE/derived table, chuỗi có dấu nháy, NULL, dòng trùng và sắp xếp.

Kết quả khớp lệnh CLI Spider gốc, không có câu vốn đúng EM bị chuyển thành sai
và không phát sinh lỗi parser ở câu vốn parse được. Những cú pháp chưa chuyển
đổi an toàn như LEFT JOIN, CAST, IS NOT NULL và EXISTS vẫn giữ nguyên. Do đó,
EM sau chuẩn hóa vẫn chịu giới hạn parser, đặc biệt với Codex MCP SQL; cần đọc
cùng SQLite EX để đánh giá kết quả thực thi.

### Chạy lại và artifact

Từ thư mục `text2sql-comparison/`, sau khi cài dependency trong `pyproject.toml`
và có đủ prediction, dataset/database cục bộ:

```bash
.venv/bin/python -m nltk.downloader -d /tmp/text2sql-nltk punkt_tab
export NLTK_DATA=/tmp/text2sql-nltk
.venv/bin/python scripts/evaluate_em.py
.venv/bin/python scripts/normalize_em.py
```

[evaluate_em.py](../../scripts/evaluate_em.py) ghi kết quả trước chuẩn hóa vào
`results/em_full_dev/`; [normalize_em.py](../../scripts/normalize_em.py) ghi
prediction riêng, audit chuẩn hóa và kết quả chấm mới vào
`results/em_normalized_full_dev/`. Mỗi lượt có `summary.csv`, `by_difficulty.csv`,
`report.md`, log evaluator và kết quả từng câu. Lượt chuẩn hóa có thêm
`normalization_summary.csv`, `*.normalization.json` và manifest lưu checksum nguồn.
Các thư mục artifact này được giữ cục bộ, không đưa vào Git; bảng trên lưu lại
kết quả tổng hợp trong báo cáo được version control. Prediction gốc và kết quả
EM trước chuẩn hóa không bị ghi đè khi chạy bước chuẩn hóa.

## Cách chấm và kiểm tra

SQLite EX thực thi trực tiếp trên một database cho mỗi câu; không phải test-suite
accuracy. Evaluator giữ DISTINCT, literal và số dòng trùng; cho phép hoán vị cột
nhất quán và chỉ bắt buộc thứ tự dòng khi gold có ORDER BY ngoài cùng. Không thay
giá trị dự đoán bằng giá trị gold. Trong lượt chấm EX, mã Spider chỉ phân loại
độ khó của gold SQL; các lượt EM dùng thêm bộ so khớp cấu trúc của Spider như
mô tả ở trên.

Báo cáo sử dụng prediction cuối đã lưu sau các bước retry và kiểm tra hợp lệ.
Audit bổ sung cho `codex_mcp` kiểm tra pipeline trên 1.034 câu và thực thi lại SQL
gốc, SQL chuẩn hóa, gold của 241 câu EX sai: chưa phát hiện lỗi parse/chuẩn hóa
gây mất điểm, không có lỗi thực thi SQLite. Phạm vi và chi tiết khôi phục trace
được ghi tại [ghi chú kiểm tra prediction](../../notes/prediction-audit.md).
EX sai thể hiện khác kết quả gold trên database hiện có; một số câu hỏi/gold có
thể có cách hiểu khác nhau.
