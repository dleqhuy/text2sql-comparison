# SQL / Lab backend

FastAPI, SQLModel, PostgreSQL, Alembic từ Full Stack FastAPI Template.
Pipeline routes ở `app/api/routes/live.py`; runner service ở `app/services/`.

Từ repo root:

```bash
uv sync --project backend --locked
npm run setup:env
npm run dev
```

`npm run dev` chuẩn bị PostgreSQL local và migrations. Dashboard/API không cần đăng nhập.
API ở `http://127.0.0.1:8100`, docs ở `/docs`. Chỉ dùng một Uvicorn worker.
Chạy test bằng `npm run test:backend` khi PostgreSQL đang chạy; wrapper tạo
DB `_test` riêng và không đụng dữ liệu dev.

Xem [hướng dẫn ứng dụng](../notes/live.md) cho cấu hình, lưu trữ và giới hạn.
