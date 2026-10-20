# Chạy thử 20 câu Spider dev

Sau khi [cài môi trường](setup.md), chạy từ `text2sql-comparison/`:

```bash
export NLTK_DATA=/private/tmp/text2sql-nltk
set -a
source .env
set +a

uv run --no-project python scripts/run_comparison.py --count 20
```

Script chạy cả ba phương pháp trên 20 câu đầu dev (`dev_0000`–`dev_0019`),
rồi chuẩn hóa và chấm SQLite EX. Các câu đều thuộc `concert_singer`;
điểm này dùng kiểm tra pipeline, chưa đại diện cho toàn bộ Spider.

- Input: `data/smoke20/`.
- Kết quả: `results/smoke20/`.
- Workspace DAIL riêng: `results/smoke20/dail_work/`.
- Báo cáo: `results/smoke20/report.md`.

Chấm lại raw đã có, không gọi model:

```bash
uv run --no-project python scripts/run_comparison.py --count 20 --evaluate-only
```

Có thể thêm `--dry-run` để xem trước, `--methods` để chọn phương pháp hoặc
`--output` để chạy mới vào thư mục khác. Xem [tùy chọn chung và chính sách chấm](full-dev.md).
