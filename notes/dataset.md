# Dataset: Spider 1.0

Spider là bộ dữ liệu Text-to-SQL: từ câu hỏi ngôn ngữ tự nhiên và schema của một
database, hệ thống sinh truy vấn SQL để lấy đúng thông tin. Spider 1.0 có
10.181 câu hỏi, 5.693 truy vấn SQL khác nhau và 200 database thuộc 138 lĩnh vực.
Thiết kế chia database giữa train và các tập đánh giá nhằm kiểm tra khả năng
làm việc với schema mới. Nguồn: [trang Spider chính thức](https://yale-lily.github.io/spider).

Workspace này so sánh bốn phương pháp trên **Spider 1.0 dev**, không chạy benchmark
Spider 2.0. Các số liệu về file bên dưới được kiểm tra từ bản dữ liệu đang dùng
trong `downloads/spider_data/`.

## Phạm vi thí nghiệm

| Thành phần | Quy mô trong workspace | Vai trò |
|---|---:|---|
| `dev.json` | 1.034 câu, 20 database | Input đánh giá chung cho cả bốn phương pháp |
| `train_spider.json` | 7.000 câu, 140 database | Nguồn ví dụ train cho DAIL-SQL |
| `train_others.json` | 1.659 câu, 6 database | Dữ liệu train bổ sung được đưa vào preprocessing DAIL-SQL |
| `tables.json` | Schema của các database | Tên bảng/cột, kiểu dữ liệu, khóa chính/ngoại |
| `database/` | Các file SQLite | Đọc schema/giá trị và thực thi SQL |

Số lượng trong hai file train là thống kê của gói local; không cộng chúng vào
1.034 câu được chấm. Pipeline này không fine-tune model: DAIL-SQL sử dụng ví dụ
train để chọn các cặp câu hỏi/SQL cho prompt few-shot. DIN-SQL có ví dụ viết sẵn
trong mã nguồn. Xem [hướng dẫn từng phương pháp](methods.md).

```text
Train: câu hỏi + SQL -----------------> chọn ví dụ cho DAIL-SQL
                                                |
Dev: câu hỏi + db_id + schema/database ----------+
                                                v
                                         Phương pháp sinh SQL
                                                |
                                                v
                                          Prediction SQL
                                                |
Dev: gold SQL ------------------------> Chấm trên SQLite -> EX
```

Gold SQL là đáp án tham chiếu để chấm; SQL sơ bộ của DAIL-SQL được model sinh
ở lượt đầu. Codex runner chỉ nhận các trường input cần thiết, bỏ gold khỏi
request gửi model.

## Một mẫu dữ liệu gồm gì?

Ví dụ rút gọn từ câu đầu tiên trong dev:

```json
{
  "db_id": "concert_singer",
  "question": "How many singers do we have?",
  "query": "SELECT count(*) FROM singer"
}
```

Hệ thống cần hiểu câu hỏi là đếm số ca sĩ, xác định bảng `singer`, rồi sinh SQL.
Database để thực thi nằm ở
`database/concert_singer/concert_singer.sqlite`.

| Trường gốc | Ý nghĩa |
|---|---|
| `db_id` | Database tương ứng với câu hỏi |
| `question` | Câu hỏi bằng tiếng Anh |
| `query` | SQL tham chiếu (gold) |
| `question_toks` | Câu hỏi đã tách token |
| `query_toks`, `query_toks_no_value` | SQL đã tách token, có hoặc bỏ giá trị |
| `sql` | Cấu trúc SQL đã parse, dùng khi phân loại độ khó gold |

`tables.json` mô tả tên bảng/cột gốc và tên chuẩn hóa, kiểu cột, primary key và
foreign key. Cần dùng đúng tên gốc khi thực thi trên SQLite. Định dạng dữ liệu
được mô tả thêm trong [README Spider trong workspace](../../spider/README.md#data-content-and-format).

## Vì sao có nhiều mức độ khó?

Một câu hỏi có thể chỉ cần lọc một bảng, hoặc cần JOIN, GROUP BY/HAVING,
truy vấn lồng và phép toán tập hợp như UNION/INTERSECT/EXCEPT. Việc sinh SQL
đòi hỏi xác định đúng cột, quan hệ giữa bảng và cách kết hợp các thao tác này.

Evaluator dùng mã Spider để phân loại cấu trúc **gold SQL** thành bốn mức:

| Mức độ khó | Số câu dev |
|---|---:|
| easy | 248 |
| medium | 446 |
| hard | 174 |
| extra | 166 |
| Tổng | 1.034 |

Đây là nhãn theo quy tắc của evaluator, không chỉ theo độ dài câu hỏi hoặc số
bảng. Nhãn EASY/NON-NESTED/NESTED do DIN-SQL dự đoán là một cơ chế riêng.
Số câu trên có thể đối chiếu ở [CSV theo độ khó](../results/full_dev/by_difficulty.csv).

## Dữ liệu được chuẩn bị như thế nào?

```text
downloads/spider_data/                # Dữ liệu gốc tải về
├── dev.json
├── tables.json
├── database/<db_id>/<db_id>.sqlite
├── train_spider.json
├── train_others.json
└── train_gold.sql
               |
               v
       scripts/prepare_data.py
               |
               v
data/dev_full/ hoặc data/smokeN/      # Input chung đã xuất
├── examples.json                    # Mẫu gốc + example_id
├── dev.json                         # Mẫu gốc + question_id cho MAC-SQL
├── tables.json                      # Bản sao schema
├── gold.txt                         # SQL + tab + db_id, một câu mỗi dòng
├── subset.json                      # Danh sách example_id theo thứ tự
└── source.json                      # Nguồn, số câu và SHA-256
```

`example_id` lấy từ vị trí trong dev: `dev_0000` đến `dev_1033` cho full dev.
`question_id` là vị trí cục bộ trong input đã xuất. Database được dùng từ thư
mục nguồn chung; bước chuẩn bị không sao chép database vào `data/dev_full/`.
Các file đã xuất vẫn chứa gold phục vụ adapter/evaluator; chúng không phải
bản prompt gửi nguyên trạng cho model.

Runner mặc định chọn toàn bộ dev. `--count N` lấy **N câu đầu**, giữ nguyên ID
và thứ tự, không lấy mẫu ngẫu nhiên. Các phương pháp được so sánh cần dùng cùng
lựa chọn này. `source.json` lưu checksum của `dev.json`, `tables.json` và các
database được chọn để bước chuẩn bị phát hiện tài nguyên đã thay đổi.

20 câu đầu (`dev_0000`–`dev_0019`) đều thuộc `concert_singer`. Vì vậy smoke20
phù hợp kiểm tra pipeline nhưng chưa đại diện cho 20 database của full dev.
Xem [chạy thử](smoke20.md) hoặc [chạy toàn bộ dev](full-dev.md).

## Điểm số được tính như thế nào?

Workspace báo cáo SQLite execution accuracy (EX): chạy prediction và gold
trên cùng database, rồi so kết quả theo [quy tắc evaluator](full-dev.md#đọc-kết-quả).

```text
EX = số câu có kết quả prediction khớp gold / tổng số câu được chấm
```

Prediction thiếu, rỗng hoặc lỗi thực thi tính sai. SQL có thể khác cách viết
mà vẫn khớp kết quả. Ngược lại, SQL thực thi thành công vẫn có thể trả sai dữ
liệu. Trên một database cụ thể, hai query cũng có thể tình cờ cho cùng kết quả.

Đây là EX trên **một database cho mỗi câu**, khác Test Suite Accuracy kiểm tra
trên nhiều database kiểm thử. Trang Spider ghi nhận Test Suite Accuracy là
metric chính thức từ năm 2020; vì vậy cần đối chiếu cả split và metric trước
khi so điểm workspace với leaderboard. Nguồn: [thông báo metric của Spider](https://yale-lily.github.io/spider).

Hướng dẫn tải và đặt dữ liệu: [setup.md](setup.md#dữ-liệu).
Nguồn học thuật: [Spider, EMNLP 2018](https://arxiv.org/abs/1809.08887).
