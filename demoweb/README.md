# Demoweb

Bản chạy độc lập của web local, đã tách khỏi dữ liệu chụp và tài liệu nghiên cứu.

## Yêu cầu

- Node.js 24 trở lên
- npm
- Python 3.11 và package root đã cài vào `<repo>/.venv` bằng
  `.venv/bin/python -m pip install -e ".[api]"` (Windows dùng `.venv\Scripts\python`).

## Chạy local

```powershell
npm ci
npm run dev -- --hostname 0.0.0.0 -p 3000
```

Mở `http://localhost:3000`.

## Kiểm tra

```powershell
npm run check
npx playwright install chromium
npm run test:e2e
```

Playwright tự chạy FastAPI mock tại `127.0.0.1:38100` và Next.js production build tại
`127.0.0.1:38101`. Suite kiểm
tra đúng ba route, hero tạm trú 5/5, manual edit, stale/retry, reset, session recreation và timeout
fallback. Ca OCR unreadable vẫn là `test.fixme` cho tới khi upload API/UI thật được tích hợp; không
được tính là pass.

Các thư mục `_DataURI`, `dichvucong.gov.vn`, `tong`, `docs` và cache của project gốc không cần để chạy bản demo này.
