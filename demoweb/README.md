# Demoweb

Bản chạy độc lập của web local, đã tách khỏi dữ liệu chụp và tài liệu nghiên cứu.

## Yêu cầu

- Node.js 24 trở lên
- npm

## Chạy local

```powershell
npm ci
npm run dev -- --hostname 0.0.0.0 -p 3000
```

Mở `http://localhost:3000`.

## Kiểm tra

```powershell
npm run check
```

Các thư mục `_DataURI`, `dichvucong.gov.vn`, `tong`, `docs` và cache của project gốc không cần để chạy bản demo này.
