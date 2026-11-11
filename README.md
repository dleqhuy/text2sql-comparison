# Text-to-SQL Comparison

So sánh DIN-SQL, MAC-SQL, DAIL-SQL và Codex MCP SQL trên **toàn bộ Spider 1.0 dev**:
1.034 câu, 20 database, cùng ID và thứ tự. Cả bốn dùng chung luồng chuẩn hóa và
chấm SQLite EX; EM được chấm thêm trước và sau chuẩn hóa cú pháp cho parser Spider.
Cấu hình model/backend nằm trong [báo cáo so sánh](results/full_dev/report.md).
Mặc định CLI chạy DIN-SQL, MAC-SQL và DAIL-SQL; chọn cả bốn bằng
`--methods few_shot mac_sql dail_sql codex_mcp`.

## Các repo đã fork

| Phương pháp | Repo fork | Repo gốc |
|---|---|---|
| DIN-SQL | [dleqhuy/Few-shot-NL2SQL-with-prompting](https://github.com/dleqhuy/Few-shot-NL2SQL-with-prompting) | [MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting) |
| MAC-SQL | [dleqhuy/MAC-SQL](https://github.com/dleqhuy/MAC-SQL) | [wbbeyourself/MAC-SQL](https://github.com/wbbeyourself/MAC-SQL) |
| DAIL-SQL | [dleqhuy/DAIL-SQL](https://github.com/dleqhuy/DAIL-SQL) | [BeachWang/DAIL-SQL](https://github.com/BeachWang/DAIL-SQL) |

Bộ đánh giá hiệu suất SQL được clone thêm từ
[bird-bench/mini_dev](https://github.com/bird-bench/mini_dev) vào thư mục ngang cấp
`../BIRD-mini-dev/`. Repo này cung cấp R-VES, được áp dụng bổ sung trên các
prediction **Spider 1.0 dev** hiện có; không phải lượt chạy trên dataset BIRD.

## Chạy

**Ứng dụng SQL / Lab — frontend/backend từ Full Stack FastAPI Template:**
chạy `npm ci`, `uv sync --project backend --locked`, `npm run setup:env`, rồi
`npm run dev`. Mở <http://127.0.0.1:5173> để vào thẳng dashboard, không cần tài khoản.
React/TypeScript có timeline và prompt/response inspector; FastAPI phục vụ API/SSE,
PostgreSQL lưu lịch sử chung của workspace. Xem [hướng dẫn SQL / Lab](notes/live.md).

Giới thiệu dữ liệu: [Spider 1.0, cấu trúc mẫu, train/dev và cách chấm](notes/dataset.md).

1. [Cài môi trường và tài nguyên](notes/setup.md).
2. [Chạy full dev và chấm điểm](notes/full-dev.md).
3. [Tổng quan luồng xử lý](notes/methods.md) và hướng dẫn riêng:
   [DIN-SQL](notes/din-sql.md), [MAC-SQL](notes/mac-sql.md),
   [DAIL-SQL](notes/dail-sql.md), [Codex MCP SQL](notes/codex-mcp-sql.md).
4. [Cấu hình phương pháp và phiên bản](notes/versions.md).

Cần kiểm tra pipeline trước: [chạy thử 20 câu](notes/smoke20.md).

Mỗi phương pháp dùng repo và `.venv` riêng. Ba phương pháp gốc đọc `LLM_*`
từ `.env`; Codex dùng xác thực Codex/OpenAI và `CODEX_MODEL` hoặc `--codex-model`.
Xem `.env.example` và [hướng dẫn cài đặt](notes/setup.md).
Script chung: `scripts/run_comparison.py`; mặc định full dev, dùng `--count 20`
để chạy thử. Các tùy chọn nằm trong [hướng dẫn chạy](notes/full-dev.md).

Chạy riêng Codex trên 3 câu, sau khi [cài môi trường Codex](notes/setup.md#codex-mcp-sql):

```bash
uv run --no-project python scripts/run_comparison.py \
  --methods codex_mcp --codex-model gpt-6-luna \
  --count 3 --output results/codex_smoke3
```

Thêm `--resume` vào cùng lệnh để chạy tiếp khi hết usage; xem
[cách chạy Codex và chấm cùng các phương pháp khác](notes/full-dev.md#codex-mcp-sql).
Thêm `--workers 4` để Codex xử lý đồng thời 4 câu, kể cả khi resume.

```text
text2sql/
├── text2sql-comparison/
│   ├── data/dev_full/           # Input chung cho 1.034 câu
│   ├── scripts/                 # Chạy, chuẩn hóa và chấm điểm
│   ├── tests/
│   ├── notes/
│   └── results/full_dev/
│       ├── raw/                 # Output phương pháp
│       ├── predictions/         # SQL chuẩn hóa, cùng ID và thứ tự
│       ├── evaluation/          # Input, log và kết quả SQLite từng câu
│       ├── summary.csv
│       ├── by_difficulty.csv
│       └── report.md
├── Few-shot-NL2SQL-with-prompting/
├── MAC-SQL/
├── DAIL-SQL/
├── codex-mcp-sql/
├── BIRD-mini-dev/              # Evaluator R-VES upstream
└── spider/
```

## Kết quả full dev

| Phương pháp | SQLite EX | EM trước chuẩn hóa Spider | EM sau chuẩn hóa Spider | R-VES (điểm) |
|---|---:|---:|---:|---:|
| DIN-SQL | 82,01% | 58,80% | 61,22% | 71,87 |
| MAC-SQL | 81,43% | 48,07% | 54,16% | 71,30 |
| DAIL-SQL | 82,79% | 63,93% | 66,05% | 73,53 |
| Codex MCP SQL | 76,69% | 18,67% | 39,07% | 66,46 |

Cả bốn có đủ 1.034 prediction không rỗng. Độ khó: 248 easy, 446 medium,
174 hard, 166 extra. Xem [báo cáo so sánh](results/full_dev/report.md) để đọc
cấu hình, EX theo độ khó, số câu đúng EM và lỗi parser trước/sau chuẩn hóa.

SQLite EX thực thi trực tiếp, giữ DISTINCT, literal và số dòng trùng;
cho phép hoán vị cột nhất quán, xét thứ tự dòng khi gold có ORDER BY ngoài cùng.
Đây là EX trên một database cho mỗi câu, không phải test-suite accuracy.
Trong lượt chấm EX, mã Spider phân loại độ khó của gold SQL; prediction được
thực thi trực tiếp bằng SQLite.

EM là **Exact Set Match** bằng evaluator Spider gốc với `--etype match`, giữ
`DISABLE_VALUE=True` và `DISABLE_DISTINCT=True`; không phải so khớp chuỗi SQL.
“Trước chuẩn hóa Spider” là prediction đã lưu sau pipeline inference/chuẩn hóa
chung, trước bước thích nghi cú pháp bổ sung dành riêng cho EM. Bước này dùng
SQLGlot để xử lý identifier, alias và cú pháp tương đương, không gọi lại model.

3.728 SQL được thay đổi đều đã đối chiếu kết quả SQLite với bản trước đó:
giữ vị trí cột, số dòng trùng và thứ tự khi có ORDER BY ngoài cùng. Nhãn cột đầu
ra có thể được bỏ trong bản dành cho EM; prediction gốc được giữ riêng. Không có
câu vốn đúng EM bị chuyển thành sai hoặc câu vốn parse được phát sinh lỗi parser.
Đối chiếu này kiểm tra trên database hiện có, không chứng minh tương đương trên
mọi dữ liệu. Các lỗi parser còn lại vẫn tính trong mẫu số 1.034 câu mỗi phương pháp.

Chấm lại từ prediction đã lưu bằng [evaluate_em.py](scripts/evaluate_em.py) và
[normalize_em.py](scripts/normalize_em.py); xem lệnh và giới hạn trong
[báo cáo so sánh](results/full_dev/report.md#exact-set-match-trước-và-sau-chuẩn-hóa-spider).

Tám file prediction được lưu trong Git để chấm lại, mỗi file có 1.034 dòng JSONL
gồm `example_id`, `db_id`, `question`, `predicted_sql`:

- Bản dùng cho EX, EM trước chuẩn hóa và R-VES:
  [DIN-SQL, MAC-SQL, DAIL-SQL](results/full_dev/predictions/) và
  [Codex MCP SQL](results/codex_full_dev/predictions/codex_mcp.jsonl).
- Bản dùng cho EM sau chuẩn hóa: [cả bốn phương pháp](results/em_normalized_full_dev/predictions/).

Dataset/database cần được chuẩn bị riêng theo [hướng dẫn cài đặt](notes/setup.md).
Raw response, trace và log timing không được đưa vào Git.

## Đánh giá hiệu suất SQL bằng BIRD R-VES

[evaluate_bird_rves.py](scripts/evaluate_bird_rves.py) gọi trực tiếp các hàm trong
[evaluation_ves.py của BIRD Mini-Dev](https://github.com/bird-bench/mini_dev/blob/1c49a375e76c471e218564da3f4617513d33e371/evaluation/evaluation_ves.py).
Đây là **Reward-based Valid Efficiency Score (R-VES)**. Metric kiểm tra hai tập
tuple kết quả trước khi đo tốc độ: bỏ qua thứ tự và số lần lặp của dòng, giữ thứ
tự cột. Điều kiện này khác SQLite EX ở bảng trên.

Chạy từ thư mục `text2sql-comparison/`, dùng prediction đã lưu trước bước chuẩn
hóa riêng cho EM:

```bash
git clone --depth 1 https://github.com/bird-bench/mini_dev.git ../BIRD-mini-dev
git -C ../BIRD-mini-dev checkout 1c49a375e76c471e218564da3f4617513d33e371
uv sync --extra bird
.venv/bin/python -m nltk.downloader -d /tmp/text2sql-nltk punkt_tab
export NLTK_DATA=/tmp/text2sql-nltk
.venv/bin/python scripts/evaluate_bird_rves.py
```

Nếu đã clone repo thì bỏ qua lệnh clone. Để tái lập revision trên một clone
shallow ở thời điểm khác, có thể cần fetch commit trước khi checkout.
Mặc định chạy đủ bốn phương pháp, một worker, một lượt toàn bộ dữ liệu;
100 cặp đo prediction/gold cho mỗi câu khớp kết quả. `--meta-timeout 3` cho phép
tối đa 300 giây/câu, theo cách nhân timeout với số lần đo của upstream.
Không gọi lại model; không đo thời gian sinh SQL hoặc thời gian gọi MCP.

Kết quả nằm ở `results/bird_rves_full_dev/`; [summary.csv](results/bird_rves_full_dev/summary.csv)
và [by_difficulty.csv](results/bird_rves_full_dev/by_difficulty.csv) được lưu trong Git.
Log từng câu và metadata được giữ cục bộ: `*.details.jsonl`, `*.details.json`,
`*.bird_input.json`, `gold.txt` và `manifest.json`. Manifest lưu revision/hash
evaluator, hash prediction, phiên bản runtime, số lần đo và thứ tự phương pháp.
Độ khó vẫn là easy/medium/hard/extra của Spider, không gán nhãn BIRD.

R-VES phụ thuộc máy, cache và tải hệ thống; điểm tính bằng
`100 × trung bình(sqrt(reward))`, có thể vượt 100 nên không phải phần trăm câu
đúng. Xem [báo cáo so sánh](results/full_dev/report.md) để đọc kết quả và cấu hình đo.

## Kiểm thử

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
uv run --no-project python -m unittest discover -s tests -v
uv run --no-project ruff format --check .
```
