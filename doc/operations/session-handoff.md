# Bàn giao phiên

## Trạng thái hiện tại

- Repo có data package v2, domain/data runtime foundation, AI extraction và CLI shell.
- Repo có thêm `demoweb/`, một giao diện Next.js độc lập; thư mục này không phụ thuộc tool clone hoặc dữ liệu capture ban đầu.
- Luồng demoweb tại `/hon-nhan-va-gia-dinh` chỉ còn ba thủ tục đúng data package; route đăng ký kết hôn cũ trả 404.
- Form `1.004194` là hero flow và dùng shared workspace với chat, giữ dirty/confirmed/revision qua refresh trong phiên.
- Scope runtime nằm trong `data/README.md`.
- `vneguide.domain` cung cấp contract dùng chung; `ProcedureRepository` cung cấp dữ liệu đã audit.
- `python -m vneguide.cli` nạp được `vneguide.core:create_session`.
- Core và rules đã hỗ trợ suggestion, Accept/Reject/Edit, validation và question selection.
- Repo có HTTP Chat API và Next.js BFF; chatbox chỉ xuất hiện trong `/hon-nhan-va-gia-dinh/**`.
- Session web dùng cookie `HttpOnly`; Python store hiện là in-memory single-process với TTL/capacity/per-session lock.

## Việc đã xác minh

- `demoweb`: `npm run check` pass (ESLint, TypeScript và production build; 26 route).
- `demoweb`: 12 HTTP assertion production pass; catalog có 4 thủ tục tích hợp/11 chưa tích hợp, thư mục có 7 dịch vụ và query không dấu/mã thủ tục hoạt động.
- Nhánh Người 1 có 25 unit test pass cho domain/data foundation.
- Baseline main trước tích hợp đạt `37 passed, 1 skipped`.
- AI tests không cần API key; live provider smoke mặc định skip.
- Data repository kiểm nguồn approved, local path, rule context và checksum.
- Python 3.11.9: Ruff và Mypy pass; Pytest `75 passed, 1 skipped`; coverage `82.64%`.
- Sau tích hợp chat: Ruff và Mypy pass; Pytest `79 passed, 1 skipped`; coverage `82.32%`.
- `demoweb`: `npm run check` pass, production build có 29 route gồm ba BFF route `/api/chat/*`.
- Smoke end-to-end local web → BFF → Python API pass; provider mock rỗng trả fallback `retry`.
- Nhánh `agent/web-three-procedures`: `npm run check` pass, 8 reducer tests pass, hero route HTTP `5/5` status 200, route kết hôn cũ 404.

## Rủi ro

- Tài liệu Product/Architecture/Terminal cũ vẫn mô tả bộ thủ tục khác data package v2.
- Fixture intent scripted mock không chứng minh accuracy model thật.
- Rule condition không phải DSL thực thi; phải dùng handler xác định theo `rule_id`.
- Một số rule dùng context/document signal, không được suy đoán từ field biểu mẫu.
- Git LFS có thể cần quyền ghi `.git/lfs/tmp` trong môi trường sandbox.
- Danh sách Phường/Xã và Sở phụ thuộc upstream `vpcp.dichvucong.gov.vn`; khi upstream lỗi hoặc quá hạn, UI hiển thị lỗi và cho phép thử lại thay vì dùng dữ liệu giả.
- Backend hiện chưa có endpoint cập nhật field trực tiếp `/v1/chat/sessions/{session_id}/fields/{field_id}` và `DraftResponse` chưa trả `values`; BFF/frontend đã chuẩn bị contract nhưng chưa thể xác minh manual-edit sync end-to-end trước khi backend merge.
- Browser in-app không khởi tạo được trong Windows sandbox, nên visual, keyboard và screen-reader QA vẫn cần chạy ở môi trường browser khả dụng.
- In-memory session store chỉ phù hợp một API worker; cần Redis hoặc store dùng chung trước khi scale nhiều worker.

## Bước tốt nhất tiếp theo

Merge backend field-update contract, chạy visual/browser QA 5 lượt cho hero tạm trú, sau đó cấu hình provider/model và chạy live smoke/E2E trên dữ liệu giả.

## Lệnh dự kiến

- Cài Python API: `python -m pip install -e ".[dev,api]"`
- Chạy API: `python -m vneguide.api`
- Chạy web: `cd demoweb`, `npm ci`, `npm run dev -- --hostname 0.0.0.0 -p 3000`
- Kiểm tra web: `cd demoweb`, `npm run check`
- Cài dev dependencies: `python -m pip install -e ".[dev]"`
- Quality gate: `python -m ruff check .`, `python -m mypy`, `python -m pytest`
- CLI: `python -m vneguide.cli`
