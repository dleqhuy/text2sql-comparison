# Phiên bản và kết quả

Thử nghiệm dùng Python 3.9.6 trên macOS Apple Silicon. Mỗi repo có `.venv` riêng,
được tạo và cài thư viện bằng `uv`.

Formatter: Ruff 0.17.1, khai báo trong nhóm `dev` của `pyproject.toml`.

## Dữ liệu và model

- Spider 1.0: [nguồn chính thức](https://yale-lily.github.io/spider).
- Subset: 20 câu đầu dev, `dev_0000`–`dev_0019`, đều thuộc `concert_singer`.
- Model: `cx/gpt-6-luna`, endpoint `http://localhost:20128/v1`.
- DIN: temperature 0, tối đa 600 token khi sinh SQL và 350 token khi debug.
- MAC: giữ cấu hình mặc định của repo/provider.
- DAIL: hai lượt chọn ví dụ, temperature 0, tối đa 200 token, `n=1`.

Đây là thử nghiệm kiểm tra pipeline, chưa đại diện cho toàn bộ Spider.

## Commit gốc

| Repo | Commit |
|---|---|
| DIN-SQL | `fe9d2ea39711dafaba7e0f0621513b9ab9646187` |
| MAC-SQL | `f8ca56f20192fe85b65a2542f917f820910e80d6` |
| DAIL-SQL | `7df99e15d8916a35711ff13735fd5ee01262c10e` |
| Spider evaluator | `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c` |

Các sửa đổi đã được commit riêng:

| Repo | Commit có các sửa đổi dùng trong thí nghiệm |
|---|---|
| DIN-SQL | `be08d838ce1cc1a4d465b3f34bb4d493d21cb10a` |
| DAIL-SQL | `fa1c2a1e38946934858fef5db5e3e22661fee02b` |

Danh sách thư viện đã cài nằm trong [dependencies/](dependencies/).
Checksum của các tài nguyên và mã phương pháp ở thời điểm chạy nằm trong
[checksums.sha256](checksums.sha256). Hash dữ liệu nằm trong `data/source.json`.

## Các sửa đổi cần biết

- DIN/DAIL: đọc được SQL trong Markdown và phản hồi chat khác định dạng cũ.
- DIN: giới hạn retry, ghi kết quả từng câu và giữ vị trí khi lỗi.
- DAIL: bỏ tải vector GloVe không dùng và cache tra cứu giá trị; đã đối chiếu với hàm gốc.
- DAIL: bộ đếm token của checkout gốc trả 0; số token/chi phí ước tính không đáng tin.
- Chuẩn hóa chung: bỏ backtick an toàn và comment ngoài chuỗi trước khi dồn dòng.
- Output raw và evaluator Spider gốc được giữ nguyên.

## Kết quả hiện tại

| Phương pháp | Đúng / tổng | EX |
|---|---:|---:|
| DIN-SQL | 16/20 | 80% |
| MAC-SQL | 17/20 | 85% |
| DAIL-SQL | 19/20 | 95% |

MAC còn hai lỗi parser do alias cột; câu `dev_0016` chạy được nhưng khác gold.
13 kiểm thử comparison đã qua. Test phương pháp: DIN 7, DAIL 3 đều qua.

Điểm cuối nằm trong [summary.csv](../results/summary.csv). Các bản trước chuẩn hóa
và audit được giữ cục bộ trong `results/archive/`, không đưa vào Git.
