# EX theo độ khó

Độ khó được lấy từ evaluator Spider gốc, dựa trên gold SQL.
Backend: SQLite, chấm trực tiếp trên một database cho mỗi câu; không phải test-suite accuracy. Điểm dùng độ chính xác đầy đủ.

| Method | all (n=1034) | easy (n=248) | medium (n=446) | hard (n=174) | extra (n=166) |
|---|---:|---:|---:|---:|---:|
| few_shot | 82.0% | 90.7% | 83.0% | 81.0% | 67.5% |
| mac_sql | 81.4% | 91.9% | 83.4% | 79.3% | 62.7% |
| dail_sql | 82.8% | 92.7% | 85.2% | 82.8% | 61.4% |

`—`: không có câu ở độ khó này, không phải EX bằng 0.

Giữ DISTINCT và số dòng trùng; cho phép hoán vị cột nhất quán; chỉ bắt buộc thứ tự dòng khi gold có ORDER BY ngoài cùng. Không thay giá trị dự đoán bằng giá trị gold.
