# Nhật ký tiến độ VNeGuide

## Trạng thái release

- Nhánh tích hợp: `integration/release-dev`, tạo từ `dev` tại `1d3e566`.
- Đã merge `tuan` bằng `4865ceb`, cherry-pick tài liệu scope `709b795` thành `ff06998` và tạo
  release baseline `a8e182f`.
- Đã hợp nhất `origin/dev` tại `e65b31b` bằng merge commit `44d399f`, gồm merge web/API và sửa kết
  nối model với web.
- LiteLLM, FastAPI Chat API và Next.js cùng tồn tại trên cây tích hợp.
- Backend/data chỉ có đúng `2.000635`, `1.013314`, `1.004194` theo `data/README.md`.
- Frontend vẫn chỉ có route Hôn nhân và gia đình với bốn mã ngoài data package; release sản phẩm
  chưa đạt tiêu chí đúng ba thủ tục.

## 2026-07-18 — QA, release và deploy

- Cài Python bằng `python -m pip install -e ".[api,dev]"` và web bằng `npm ci`.
- Thêm API orchestration/integration test in-process cho đúng ba mã, out-of-scope, hero tạm trú
  chạy độc lập 5/5, stale revision, suggestion edit, reset, typed provider timeout và generic OCR
  safe fallback.
- Nâng Next `16.2.1 → 16.2.10`, shadcn `4.1.0 → 4.13.1`, đồng bộ ESLint config và override
  PostCSS `8.5.16`; `npm audit` giảm từ 12 vulnerability xuống 0.
- Thêm GitHub Actions, Dependabot, Dockerfile API/web, Compose, Nginx gateway, smoke metrics và
  limited staged-text audit cho secret pattern phổ biến, số định danh 12 chữ số và conflict marker.
- Thêm release evidence, rollback runbook, pitch và shot list video dự phòng.
- Chặn root/nested `.env*` khỏi Docker context, khóa version Python API runtime và thêm Nginx timeout
  75 giây để có margin trên BFF timeout 60 giây.
- Build container API/web đạt; Compose chạy API/web/gateway healthy sau merge.
- Public preview tạm thời qua ngrok đạt 5/5 HTTP 200 cho `/` và `/health` trên image sau merge.

### Tích hợp cập nhật `origin/dev` tại `e65b31b`

- Giữ tùy chọn khởi động `python -m vneguide.api --env-file .env`; file LLM chỉ được đọc khi opt-in
  tường minh, không tự nạp secret lúc import.
- Giữ timeout BFF 60 giây cho retry provider có giới hạn; widget tạo lại session rồi gửi lại một lần
  khi cookie trỏ tới session backend đã mất hoặc hết hạn.
- Nhận bản format chuẩn của `src/vneguide/api/session_store.py` từ API owner.
- Bằng chứng live BFF/model ghi trong commit nguồn dùng dữ liệu tổng hợp; Release Captain chưa xem
  đó là accuracy gate và không ghi prompt, raw response hay secret vào evidence.
- Conflict chỉ ở `.env.example`, `progress.md` và `session-handoff.md`; cấu hình LiteLLM HTTPS mẫu,
  API local và port Compose đều được giữ.

## Quality gate sau merge `e65b31b`

| Gate | Kết quả |
| --- | --- |
| `ruff check src tests deployment` | Pass |
| `ruff format --check src tests deployment` | Pass, 65 file formatted |
| `mypy` | Pass, 63 source files |
| `pytest --cov` | 106 passed, 1 skipped; coverage 81.93% |
| Release API integration | 12 passed, gồm hero 5/5 |
| `npm ci` | Pass trên host npm 11.6.2 và container npm 11.16.0 |
| `npm audit --audit-level=moderate` | 0 vulnerability |
| `npm run check` | Pass: ESLint, TypeScript, Next build 29 page |
| Docker build/health | Pass cho API, web, gateway |
| Limited staged-text audit | Pass: 335 index file, 190 text file |

## Metrics sau merge `e65b31b`

- Post-commit smoke trên `44d399f` có `tracked_dirty=false`, không có staged diff.
- Local gateway, `2026-07-18T08:50:23.102344Z`, `mock/mock-scripted`, 5 mẫu: `/health` p95
  8.44 ms, web p95 20.12 ms.
- Public gateway, `2026-07-18T08:50:28.004246Z`, `mock/mock-scripted`, 5 mẫu: `/health` p95
  326.07 ms, web p95 729.74 ms.
- Runtime container được kiểm tra riêng: `provider=mock`, `model=mock-scripted`; smoke không gọi model.
- Image đã smoke: API `sha256:c72a78e6a5b5...9e4f`, web `sha256:b87a68c910cf...c0b7`.
- URL preview: `https://moschate-terri-dereistically.ngrok-free.dev`; chỉ hoạt động khi Docker/ngrok
  trên máy release còn chạy. Smoke chỉ kiểm hạ tầng `/health` và web marker, không gọi model.

## Definition of Done

- [x] Backend/data đúng ba thủ tục.
- [x] Hero orchestration chạy độc lập 5 lượt bằng scripted extractor.
- [x] Python/npm/container gate đạt sau merge `e65b31b`.
- [x] npm audit và limited staged-text pattern scan đạt.
- [x] Infra metrics có lệnh, provider/model label và timestamp; chưa gọi model trong smoke.
- [x] Public preview và `/health` hoạt động ở tầng hạ tầng trên image sau merge.
- [ ] Frontend route/form đúng ba thủ tục.
- [ ] Browser E2E và manual edit trực tiếp trên form.
- [ ] OCR implementation và OCR E2E thật.
- [ ] Public hosting bền vững thay cho tunnel tạm.
- [ ] Video dự phòng đã record và được hai người review offline.

Không merge release vào `dev` với nhãn hoàn thành cho tới khi các mục chưa đạt được xử lý.

## Lịch sử kỹ thuật cần giữ khi bàn giao

- Domain/data foundation cung cấp contract dùng chung, repository đã audit và ba procedure pack v2.
- Structured extraction hỗ trợ mock, OpenAI Responses và LiteLLM Chat Completions; LLM chỉ phân
  loại/trích xuất, không quyết định required field, rule, phí, thời hạn hoặc căn cứ pháp lý.
- Core/rules có suggestion Accept/Reject/Edit, revision guard, retry cap và deterministic validation.
- FastAPI dùng session ID ngẫu nhiên, TTL/capacity/per-session lock; store in-memory chỉ phù hợp một
  worker. Next BFF giữ session ID trong cookie `HttpOnly` và không đưa model key ra browser.
- Frontend hiện có banner mô phỏng Hackathon và `noindex`; không tiếp nhận dữ liệu cá nhân thật.
