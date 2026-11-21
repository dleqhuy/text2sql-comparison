# Workspace Linux

Đã chuyển workspace từ bản copy macOS sang Linux x86_64 ngày 24/10/2026.

- Các repo nằm cạnh nhau, không còn lồng thêm một cấp folder.
- Comparison, DIN-SQL, MAC-SQL và DAIL-SQL có `.venv` mới với Python 3.9.25.
- Codex MCP SQL có `.venv` mới với Python 3.12.15. Mã nguồn thiếu được khôi phục
  từ `https://github.com/dleqhuy/codex-mcp-sql`, commit
  `2aa92fa62fa3502ea2583761cb4e273085d67c60`.
- DIN/DAIL dùng PyTorch 1.13.1 CPU và torchvision 0.14.1 CPU.
  Các requirements Linux nằm trong `notes/dependencies/linux/`.
- Java 11 Linux nằm tại `../DAIL-SQL/third_party/java11/linux/`;
  runner tự chọn bản này hoặc tôn trọng `JAVA_HOME` đã đặt.
- NLTK và tiktoken dùng cache trong `.cache/nltk_data` và `.cache/tiktoken`
  của comparison. Model embedding DAIL tiếp tục dùng cache trong repo DAIL.
- Symlink dữ liệu đã đổi từ đường dẫn `/Users/...` thành đường dẫn tương đối.

Các môi trường cũ, Java Mac ARM và metadata Finder được giữ tại
`../.migration-backup-macos/`. Thư mục này chỉ để lưu bản cũ.
Python Linux được cài tại `../.runtime/python/`; không di chuyển thư mục này
riêng lẻ vì các `.venv` đang tham chiếu tới interpreter bên trong.

## Chạy từ thư mục text2sql

```bash
# Kiểm tra các bước, không gọi model
./run-comparison.sh --count 3 --output results/linux-smoke3 --dry-run

# DIN-SQL, MAC-SQL, DAIL-SQL, sau khi endpoint LLM hoạt động
./run-comparison.sh --count 3 --output results/linux-smoke3

# Codex MCP SQL có xác thực riêng
./run-comparison.sh --methods codex_mcp --codex-model gpt-6-luna \
  --count 3 --output results/linux-codex-smoke3
```

Script nạp `text2sql-comparison/.env`. Tại thời điểm kiểm tra, endpoint trong
file này là `http://localhost:20128/v1`. Đã cài 9router 0.5.104 bằng mise
(`npm:9router`) với Node.js 24.22.1 và khởi động dashboard tại
`http://localhost:20128/` (chỉ bind `127.0.0.1`).
Provider đã được người dùng cấu hình; key trong `.env` đã cập nhật.
Live smoke test ngày 24/10/2026 với `cx/gpt-6-luna`: DIN-SQL, MAC-SQL và
DAIL-SQL đều chạy thành công và đúng 1/1 câu theo SQLite EX.
Kết quả: `results/linux-live-smoke1-20261024/`. Đây là kiểm tra một câu,
không phải đo lại accuracy full dev. DAIL dùng lại cache schema-linking
đã đối chiếu đủ 8.659 mẫu train và 1.034 mẫu dev; embedding, tạo prompt
và cả hai lượt inference đều được chạy mới trên Linux.

Để khởi động lại khi dịch vụ đã dừng:

```bash
mise exec -- 9router --host 127.0.0.1 --port 20128 --no-browser --skip-update
```

Log lần khởi động này: `~/.9router/mise-start.log`.
Dịch vụ chưa được cấu hình tự khởi động sau khi reboot.

## Kiểm tra

Đã pass 88 tests: comparison 43, DIN-SQL 7, MAC-SQL 8, DAIL-SQL 5,
Codex MCP SQL 25. Các test provider dùng HTTP giả hoặc mock; không gọi model.
Test HTTP localhost, CoreNLP và MCP stdio cần môi trường cho phép socket/IPC.

Đã chạy annotation CoreNLP bằng Java 11 Linux và encode câu hỏi với
`sentence-transformers/all-mpnet-base-v2` từ cache, trả vector 768 chiều.
Cả năm môi trường đều qua `uv pip check`.

Log kiểm tra và kết quả chấm lại nằm trong `../.runtime/`.
Các kết quả inference cũ được giữ nguyên.
