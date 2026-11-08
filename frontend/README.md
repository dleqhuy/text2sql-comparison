# SQL / Lab frontend

React, TypeScript, Vite 8, Tailwind CSS, shadcn/ui, TanStack Router/Query từ
Full Stack FastAPI Template. Cần Node.js 22.12+.

Từ repo root:

```bash
npm ci
npm run generate-client
npm run dev
```

Frontend ở `http://127.0.0.1:5173`, proxy `/api` sang FastAPI port 8100.
Mở URL là vào dashboard, không có màn hình tài khoản/đăng nhập hay Admin.

`src/features/pipeline/` chứa dashboard. `src/client/` được sinh từ OpenAPI;
đổi backend schema thì chạy lại `npm run generate-client` từ repo root.
`npm run build` xuất bundle vào `backend/app/frontend/`.

Xem [hướng dẫn đầy đủ](../notes/live.md).
