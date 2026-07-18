# Bàn giao phiên release

## Trạng thái Git

- Nhánh hiện tại: `integration/release-dev`.
- Đã merge `origin/agent/web-three-procedures@7646399`; conflict ở README, chat hook và hai file
  operations đã được hợp nhất theo baseline Release Captain; merge commit đang chờ chốt.
- Merge result giữ LiteLLM, FastAPI, Next.js, retry session từ `dev`, shared workspace từ UI branch
  và dependency đã vá của release branch.
- Repo đối thủ, DOCX, CSV, `.DS_Store` và `view_parquet.py` không được stage.
- Chưa cập nhật/push `dev`; integration gate đã đạt và còn bước commit/rebuild container.

## Gate sau merge UI

- Ruff lint/format và Mypy pass; Pytest `106 passed, 1 skipped`, coverage `81.93%`.
- `npm ci` và audit pass với 0 vulnerability.
- `npm run check` pass: lint, typecheck, 9 reducer test và Next 16.2.10 build 25 route.
- Ba procedure route trả 200; hero tạm trú đạt 5/5; route đăng ký kết hôn cũ trả 404.
- Limited staged-text audit pass: 333 index file, 188 text file.

## Thay đổi từ nhánh UI

- Demoweb chỉ còn đúng ba procedure code `2.000635`, `1.013314`, `1.004194`.
- Route đăng ký kết hôn cũ bị xóa; build phải chỉ generate ba procedure slug mới.
- Hero `1.004194` có form CT01 và shared workspace với chat.
- Reducer bảo vệ dirty field, stale response, reset và session recreation; form giữ dữ liệu khi
  session backend hết hạn.
- BFF `/api/chat/field` validate field ID/revision và proxy bằng cookie `HttpOnly`.

## Blocker còn lại

1. Backend chưa có `POST /v1/chat/sessions/{session_id}/fields/{field_id}`.
2. API `DraftResponse` chưa trả `values`, nên form không thể xác minh giá trị server cuối cùng.
3. Chưa có browser E2E/visual/keyboard QA; reducer test không thay thế thao tác browser.
4. OCR owner chưa cung cấp adapter/upload/UI và typed OCR failure thật.
5. Chưa có cloud target/credential hoặc video dự phòng được review.
6. In-memory session store chỉ phù hợp một worker; cần shared store trước khi scale.

## Runtime preview

Preview đang chạy là image trước merge UI và phải rebuild trước demo tiếp theo:

- Gateway local `8080`, API `8000`, web `3000`.
- Ngrok: `https://moschate-terri-dereistically.ngrok-free.dev`.
- Image cũ: API `sha256:c72a78e6a5b5...9e4f`, web `sha256:b87a68c910cf...c0b7`.

## Việc Release Captain làm tiếp

1. Chạy Python/npm gate, limited staged-text audit và kiểm tra route manifest.
2. Commit merge UI vào integration nếu gate đạt.
3. Merge integration vào local `dev`, chạy lại gate và chỉ push khi được yêu cầu rõ.
4. Sau backend field contract, chạy manual-edit/browser E2E và rebuild/smoke public image.
5. Record/review video, chốt rollback digest và hosting bền vững.

## Lệnh gate chuẩn

```bash
python -m pip install -e ".[api,dev]"
python -m ruff check src tests deployment
python -m ruff format --check src tests deployment
python -m mypy
python -m pytest --cov=vneguide --cov-report=term-missing
python deployment/scripts/release_audit.py
cd demoweb
npm ci
npm audit --audit-level=moderate
npm run check
```

Rollback bằng `git revert`; không dùng reset hoặc force-push trên branch dùng chung.
