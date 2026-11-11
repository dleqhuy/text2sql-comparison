# SQL / Lab — Full Stack FastAPI

Ứng dụng dùng source của [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)
ở commit ghi trong `template-source.json`. Giấy phép MIT được giữ tại
`licenses/full-stack-fastapi-template.txt`. Bản tích hợp dùng Python 3.12 thay vì
3.14 của upstream, npm thay Bun, và thêm pipeline explorer vào ứng dụng.

## Chạy trên workspace hiện tại

```bash
npm run dev
```

Từ `text2sql-comparison/`, lệnh này khởi động PostgreSQL local (port 55432), chạy
Alembic migrations, rồi chạy FastAPI ở
<http://127.0.0.1:8100> và Vite ở <http://127.0.0.1:5173>.
Ctrl+C dừng các service do lệnh này khởi động; dữ liệu PostgreSQL được giữ lại.
Một PostgreSQL service có sẵn sẽ không bị lệnh này dừng.

Mở URL là vào thẳng dashboard. Không có đăng nhập, đăng ký, tài khoản, Admin
hay JWT. Lịch sử được dùng chung trong workspace local.

## Cài từ checkout mới

Cần Node.js 22.12+ (Vite 8), Python 3.12 và uv. Cài riêng môi trường của các
phương pháp/dữ liệu theo [setup.md](setup.md), rồi:

```bash
npm ci
uv sync --project backend --locked
npm run setup:env
npm run generate-client
npm run dev
```

`setup:env` chỉ điền cấu hình ứng dụng còn thiếu, giữ nguyên các `LLM_*` đã có.
Điền `LLM_API_KEY` trước khi chạy DIN/MAC. Có thể dùng `python3 -m venv backend/.venv`
và `backend/.venv/bin/python -m pip install -e './backend'` nếu không dùng uv.

Launcher dùng PostgreSQL thật từ package npm `embedded-postgres`, giữ database
trong `.cache/postgres/` và chỉ listen trên loopback. Không cần cài dịch vụ
PostgreSQL toàn hệ thống hoặc Docker. Nếu dùng PostgreSQL có sẵn, đặt
`DATABASE_URL` tương ứng và `LOCAL_POSTGRES=0`.

`compose.yml` là lựa chọn khác để chạy riêng PostgreSQL bằng Docker. Khi dùng,
đặt `POSTGRES_PASSWORD` và `DATABASE_URL` khớp nhau, rồi chạy
`docker compose up -d db`. Docker Compose chưa được kiểm tra trên máy này vì
máy không có Docker. Các runner hiện chạy bằng môi trường của host; ứng dụng
không kèm cấu hình triển khai toàn bộ runner trong container.

## Cấu trúc

```text
frontend/                         # React / TypeScript / Vite / Tailwind / shadcn
  src/routes/                     # TanStack Router, một route dashboard
  src/features/pipeline/          # Timeline, inspector, schema, results, replay
  src/client/                     # Client/types sinh từ OpenAPI
backend/
  app/api/routes/live.py          # FastAPI /api/v1/live/*
  app/services/pipeline.py        # Điều phối subprocess và chấm SQLite
  app/services/run_store.py       # SQLModel persistence trong PostgreSQL
  app/live_models.py             # Request/response schemas và PipelineRun table
  app/alembic/versions/           # Migrations upstream + pipeline_run
scripts/live_worker.py            # Quan sát code phương pháp gốc
results/live/<run_id>/            # Trace/artifact JSONL, được Git ignore
```

Giao diện cũ được giữ trong `.local_archive/live-before-fastapi/`; thư mục
`live/` hiện chỉ là shim cho các lệnh cũ `npm --prefix live run dev/build`.
`scripts/live_server.py` là entry point tương thích; HTTP server cũ đã được
thay bằng FastAPI. Không có hai backend chạy song song.

## Cách dùng

1. Chọn database và câu hỏi Spider hoặc sửa câu hỏi để chạy input riêng.
2. Chọn DIN-SQL, MAC-SQL, DAIL-SQL, Codex MCP SQL rồi bấm **Chạy pipeline**. Các phương
   pháp chạy lần lượt trên cùng input.
3. Chọn tab phương pháp để xem sơ đồ React Flow chia lane. Bấm từng nút để xem
   **Input / prompt** và **Output / SQL / kết quả**; trên màn hình rộng inspector ở
   bên phải, màn hình hẹp tự cuộn đến phần chi tiết và có nút **Sơ đồ** để quay lại.
   DAIL hiển thị ví dụ train được chọn ở từng lượt; sinh SQL liên kết với prompt
   của lời gọi LLM tương ứng. Kết quả truy vấn được hiển thị dạng bảng.
   Nút chưa có trace hiện mờ và không có dữ liệu giả. Các lần retry/Refiner/tool
   calls có nút riêng; bấm **Tập trung bước**, dùng +/−, minimap hoặc kéo để xem.
   DIN chỉ tô nhãn nhánh khi response có `Label:` rõ ràng. Hình thoi là nút chọn
   nhánh có liên kết về bản ghi phân loại, không phải lời gọi LLM bổ sung.
4. **Schema** hiển thị DDL thật; **Result** hiển thị SQL cuối và tối đa 100 dòng.
5. **Lịch sử chạy** và **Phát lại** đọc trace đã lưu, không gọi model lại.
6. **JSON** xuất các sự kiện; nút vuông hủy runner. Đóng tab không
   hủy job; mở lại dashboard rồi chọn phiên đó từ lịch sử.

Lịch sử PostgreSQL là lịch sử chung của dashboard. Migration gỡ liên kết với
tài khoản và giữ nguyên các run/trace cũ. Code giao diện/API tài khoản trước đây
đã được đưa vào `.local_archive/accounts-removed/`, không được build hay chạy.
Các migration upstream và bảng tài khoản cũ được giữ như lịch sử schema; ứng dụng
hiện tại không đọc/ghi hoặc cung cấp API cho những bảng đó.

### Xóa lịch sử

- Biểu tượng thùng rác bên từng phiên hoặc nút **Xóa phiên đang xem** xóa một phiên.
- **Xóa lịch sử** xóa các phiên đã kết thúc; phiên đang chạy được giữ lại.
- Hộp thoại cho phép kiểm tra lại trước khi xóa. Sau khi xóa, nút **Hoàn tác**
  trong thông báo khôi phục lần xóa gần nhất mà không gọi model lại.
- Nếu xóa phiên đang xem, timeline/inspector/replay của phiên đó được đóng.

Đây là xóa khỏi lịch sử, có thể hoàn tác: PostgreSQL giữ `deleted_at` và trace
vẫn ở ổ đĩa để phục hồi. Không giải phóng dung lượng hay xóa vĩnh viễn dữ liệu.
API không cho đọc/stream phiên đã xóa; startup không nhập lại artifact đã xóa.

DIN-SQL ghi schema linking → classification → SQL generation → self-correction.
MAC-SQL ghi trạng thái trước/sau Selector, Decomposer, Refiner và lời gọi model
của từng agent, kể cả các vòng sửa. Agent có thể bỏ qua LLM khi schema đơn giản
hoặc SQL đã hợp lệ; không tạo bước giả để lấp chỗ trống.
DAIL-SQL dùng lại luồng hai lượt của comparison: preprocessing → chọn ví dụ lượt 1
→ sinh SQL sơ bộ → chọn lại ví dụ lượt 2 → sinh SQL cuối. Inspector hiển thị
prompt, các cặp câu hỏi/SQL train thực sự được chọn và phản hồi model ở mỗi lượt.
Mỗi lượt chọn tối đa 9 ví dụ theo cấu hình runner. Input live chỉ chứa câu hỏi,
`db_id`, token câu hỏi và SQL placeholder `SELECT 1` phục vụ API dữ liệu gốc;
gold của câu Spider không được đưa vào DAIL. Câu hỏi tùy chỉnh cũng dùng luồng này.

Lần đầu DAIL cần xử lý 8.659 mẫu train. Train schema linking được cache trong
`.cache/dail-live/`; dữ liệu train/schema, mã preprocessing/linking hoặc dấu thời
gian/kích thước database thay đổi sẽ đổi khóa cache. Câu hỏi mới vẫn được linking
lại. DAIL có giới hạn 30 phút/phiên để bao gồm bước chuẩn bị; các phương pháp khác
vẫn có giới hạn runner 10 phút. Lời gọi provider của DAIL retry tối đa 3 lần,
không dùng vòng retry vô hạn của CLI gốc. Huỷ phiên dừng cả process group.
Bootstrap báo thiếu Java/CoreNLP hoặc dữ liệu train trước khi cho chọn DAIL.
Embedding `all-mpnet-base-v2` cần có cache hoặc kết nối mạng để tải ở lần đầu.
Embedding train được lưu trong `DAIL-SQL/.cache/train-embeddings/` và dùng chung
giữa hai lượt chọn ví dụ và các phiên chạy. Lần đầu vẫn tính toàn bộ train;
những lần sau chỉ encode câu hỏi mới. Trong một live worker, hai lượt cũng dùng
chung model CPU đã nạp. Cache giữ nguyên dtype và giá trị vector,
không thay đổi masking, khoảng cách, điều kiện lọc hay thứ tự chọn ví dụ.
Khóa cache gồm toàn bộ câu train sau masking theo đúng thứ tự, trọng số model,
cấu hình tokenizer/model và phiên bản thư viện. Thay đổi các đầu vào này sẽ tính
lại; cache hỏng tự được xây lại. Có thể đặt `DAIL_EMBEDDING_CACHE_DIR` để đổi nơi
lưu hoặc `DAIL_EMBEDDING_CACHE=0` để đối chiếu với encode train trực tiếp.
SQL skeleton, schema linking và question pattern của train sau bước chuẩn bị
được cache riêng trong `DAIL-SQL/.cache/prepared-train/`. Hai lượt trong live
worker dùng chung cache bộ nhớ; phiên sau đọc cache trên đĩa. Mỗi lần sử dụng
nhận bản dữ liệu riêng và gắn lại đường dẫn SQLite cùng mô tả bảng của phiên
hiện tại. Câu hỏi đầu vào và SQL sơ bộ ở lượt 2 vẫn xử lý mới như trước.
Cache train tự đổi khi nội dung/thứ tự train, schema, train linking, mã xử lý
hoặc phiên bản parser thay đổi; cache hỏng tự xây lại. Đặt
`DAIL_TRAIN_CACHE_DIR` để đổi thư mục lưu, `DAIL_TRAIN_CACHE=0` để chạy đường xử
lý train gốc và đối chiếu kết quả.

Codex ghi request, public final response/usage và các SQLite MCP tool audit.
Tool audit xuất hiện sau khi tool hoàn thành, khi Codex turn vẫn đang chạy.
Không stream token hoặc đưa reasoning items nội bộ lên UI.

DIN/MAC dùng `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` ở `.env`. Codex dùng
`CODEX_MODEL` và Codex login hoặc `CODEX_API_KEY`/`OPENAI_API_KEY` như runner gốc;
không dùng chat endpoint `LLM_BASE_URL`.

## Lưu trữ và chấm điểm

PostgreSQL lưu run ID, thời gian, trạng thái, câu hỏi, model và
metadata. JSON/JSONL vẫn là artifact chi tiết phục vụ replay và chẩn đoán.
API lấy danh sách lịch sử từ PostgreSQL. SSE gửi snapshot idempotent, tự kết nối
lại, không phụ thuộc token hay phiên đăng nhập.
API restart đánh dấu run bị gián đoạn là `interrupted`.

Chỉ nguyên câu hỏi Spider + db_id + index mới được chấm SQLite EX. Input tùy
chỉnh chỉ kiểm tra SQL thực thi được, không gắn nhãn đúng/sai. Gold không được
gửi cho phương pháp; chỉ đọc sau khi nhận final SQL.

Chấm bằng đúng `execute`, `result_eq`, `order_matters` của comparison, trên toàn
bộ kết quả; không chấm trên bảng preview 100 dòng. Đây là EX trên một database,
không phải test-suite accuracy. SQLite đọc database Spider read-only, giới hạn
5 giây/query. PostgreSQL lưu ứng dụng, không thay thế SQLite Spider.

Chỉ chạy một API worker (`--workers 1`): khóa runner hiện nằm trong process và
chỉ nhận một phiên active tại một thời điểm. Dashboard dùng cấu hình model
trong `.env` của host; chưa có hàng đợi/distributed worker.

## Kiểm tra và client

```bash
npm run build
npm --workspace frontend run test:flow
npm run generate-client
npm run test:comparison
# Khi PostgreSQL local đang chạy trong terminal khác:
npm run test:backend
```

Backend tests tự tạo database riêng có hậu tố `_test`, không xóa lịch
sử dev. Fixture từ chối chạy nếu trỏ nhầm database thường. Có thể đặt
`TEST_DATABASE_URL` cho CI. Email trong tests được mock, không gửi ra ngoài.

Ứng dụng chỉ phục vụ local: launcher bind loopback; FastAPI kiểm tra Host/Origin
trước khi nhận request. API không cần token để chạy, stream hay hủy phiên.
Các test tài khoản/email của template đã được loại khỏi bộ test hiện tại.

`npm run build` xuất frontend vào `backend/app/frontend/`; khi khởi động lại,
FastAPI phục vụ cả bundle đó trên port 8100. Dev vẫn dùng Vite ở port 5173.
API docs: <http://127.0.0.1:8100/docs>; schema: `/api/v1/openapi.json`.
