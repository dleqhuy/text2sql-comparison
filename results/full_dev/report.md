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
Hai CSV tổng hợp các lượt tại những thư mục nguồn ở bảng cấu hình. Bốn file
prediction JSONL dùng chấm EX/EM trước chuẩn hóa/R-VES được lưu trong Git tại
`results/full_dev/predictions/` và `results/codex_full_dev/predictions/`.
Raw response và trace được giữ cục bộ, không đưa vào Git.

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
Các artifact chi tiết được giữ cục bộ; riêng bốn file JSONL trong
`results/em_normalized_full_dev/predictions/` được lưu trong Git cùng các
prediction trước chuẩn hóa. Bảng trên lưu kết quả tổng hợp trong báo cáo.
Prediction gốc và kết quả
EM trước chuẩn hóa không bị ghi đè khi chạy bước chuẩn hóa.

## Hiệu suất SQL theo BIRD Mini-Dev R-VES

Bổ sung metric từ
[evaluation_ves.py](https://github.com/bird-bench/mini_dev/blob/1c49a375e76c471e218564da3f4617513d33e371/evaluation/evaluation_ves.py)
của `bird-bench/mini_dev`, revision `1c49a375e76c471e218564da3f4617513d33e371`,
clone vào `../BIRD-mini-dev/`. Đây là R-VES áp dụng trên **Spider 1.0 dev**,
không phải đánh giá trên dataset BIRD Mini-Dev. Input là cùng prediction đã lưu
trước bước chuẩn hóa riêng cho EM; không gọi lại model.

| Phương pháp | R-VES (điểm) | Khớp tập kết quả / 1.034 | Lỗi thực thi/đọc dữ liệu | Timeout |
|---|---:|---:|---:|---:|
| DIN-SQL | 71,87 | 811 | 3 | 0 |
| MAC-SQL | 71,30 | 804 | 3 | 0 |
| DAIL-SQL | 73,53 | 826 | 4 | 0 |
| Codex MCP SQL | 66,46 | 760 | 2 | 0 |

DAIL-SQL có R-VES cao nhất trong lượt đo này. Mỗi câu nhận reward dương đều
có đủ 100 cặp đo, không có timeout hay trường hợp bộ lọc outlier trả rỗng.
Các lỗi chủ yếu là dữ liệu trong `wta_1` không giải mã được bằng UTF-8 mặc
định của upstream; DAIL-SQL còn có một câu tham chiếu cột `Airline` không rõ bảng.
Giữ nguyên cách upstream chấm các lỗi này bằng 0. Lượt SQLite EX trước đó dùng
chính sách giải mã bỏ qua byte UTF-8 lỗi, nên không suy diễn các lỗi này thành
lỗi inference hoặc chuẩn hóa SQL đối với các trường hợp giải mã UTF-8.

Số liệu đầy đủ được lưu trong Git: [summary.csv](../bird_rves_full_dev/summary.csv)
và [by_difficulty.csv](../bird_rves_full_dev/by_difficulty.csv).

### Công thức và điều kiện đúng

Upstream chỉ đo thời gian khi `set(predicted_rows) == set(gold_rows)`: bỏ qua
thứ tự và số lần lặp của dòng, giữ thứ tự cột. Cả hai kết quả rỗng cũng thỏa
điều kiện này. Chính sách khác SQLite EX trong báo cáo, vốn giữ dòng trùng,
cho phép hoán vị cột nhất quán và xét ORDER BY ngoài cùng.

Với câu khớp kết quả, mỗi cặp đo lấy tỷ lệ `r = thời gian gold / thời gian prediction`.
Bỏ các tỷ lệ nằm ngoài khoảng mở `mean ± 3 × std`, rồi lấy trung bình các tỷ lệ
còn lại để chọn reward:

| Tỷ lệ thời gian trung bình | Reward |
|---|---:|
| `0 < r < 0,25` | 0,25 |
| `0,25 ≤ r < 0,5` | 0,5 |
| `0,5 ≤ r < 1` | 0,75 |
| `1 ≤ r < 2` | 1 |
| `r ≥ 2` | 1,25 |
| Không khớp kết quả, lỗi hoặc timeout | 0 |

Điểm tổng là `100 × tổng(sqrt(reward)) / số câu`, tính trên toàn bộ 1.034 câu
mỗi phương pháp. Đây là điểm R-VES, không phải phần trăm câu đúng, và có thể
vượt 100. Giữ nguyên hành vi upstream: nếu mọi tỷ lệ bằng nhau, bộ lọc nghiêm
ngặt có thể trả danh sách rỗng; lỗi phát sinh được upstream chấm reward 0.

### Cấu hình và khả năng tái lập

[evaluate_bird_rves.py](../../scripts/evaluate_bird_rves.py) gọi trực tiếp
`execute_model` và `compute_ves` của upstream. Phần ghi log quan sát kết quả,
thời gian và lỗi; không sửa chính sách so khớp, loại outlier hoặc reward.
Mỗi câu khớp kết quả được đo 100 cặp prediction/gold, một worker, một lượt toàn
bộ dữ liệu; chạy các phương pháp theo thứ tự DIN-SQL, MAC-SQL, DAIL-SQL, Codex MCP SQL.
`meta_time_out=3` được upstream nhân với 100, thành ngân sách 300 giây/câu.

Runtime của lượt đo: Linux x86_64, Python 3.9.25, SQLite 3.50.4, NumPy 2.0.2,
func-timeout 4.3.5. Thời gian upstream bao gồm execute/fetch/đóng kết nối, không
bao gồm mở kết nối; không tính thời gian sinh SQL hoặc gọi MCP. Có hiệu ứng cache
và tải máy, nên kết quả là một lượt đo cục bộ, không phải cấu hình lặp 5 lượt rồi
lấy điểm cao nhất được mô tả trong README upstream.

Lệnh chạy và cài dependency ở [README](../../README.md#đánh-giá-hiệu-suất-sql-bằng-bird-r-ves).
Artifact cục bộ nằm trong `results/bird_rves_full_dev/`: CSV tổng hợp và theo độ
khó Spider, input BIRD, gold, log từng câu có timing/reward/lỗi và manifest ghi
revision/hash evaluator, hash prediction cùng cấu hình runtime. Không thay nhãn
độ khó Spider thành simple/moderate/challenging của BIRD.

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
