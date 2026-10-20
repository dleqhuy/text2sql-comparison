# EX theo độ khó

Độ khó được lấy từ evaluator Spider gốc, dựa trên gold SQL.
EX được lấy từ đầu ra evaluator, làm tròn đến 3 chữ số thập phân.

| Method | all (n=1034) | easy (n=248) | medium (n=446) | hard (n=174) | extra (n=166) |
|---|---:|---:|---:|---:|---:|
| few_shot | 67.2% | 85.1% | 67.0% | 64.4% | 44.0% |
| mac_sql | 58.3% | 81.5% | 60.8% | 46.0% | 30.1% |
| dail_sql | 70.5% | 87.5% | 72.2% | 63.2% | 48.2% |

`—`: không có câu ở độ khó này, không phải EX bằng 0.
