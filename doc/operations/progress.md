# Nhật ký tiến độ VNeGuide

## Trạng thái release

- Nhánh tích hợp: `integration/release-dev`, tạo từ `dev` tại `1d3e566`.
- Đã merge `tuan` bằng `4865ceb`, tài liệu scope bằng `ff06998`, release baseline bằng `a8e182f`
  và `origin/dev@e65b31b` bằng `44d399f`.
- Đã tích hợp `origin/agent/web-three-procedures@7646399` bằng `0cb4d6b`, sau đó merge cây đã kiểm
  chứng vào local `dev` bằng `829c6fa`; chưa push remote.
- LiteLLM, FastAPI Chat API và Next.js cùng tồn tại trên cây tích hợp.
- Backend/data và frontend catalog/route đều chỉ còn đúng `2.000635`, `1.013314`, `1.004194`.

## 2026-07-18 — Web đúng ba thủ tục

- Loại route và dữ liệu đăng ký kết hôn cũ; static params chỉ generate ba procedure slug được hỗ trợ.
- Thêm form CT01 mô phỏng cho hero `1.004194` và shared workspace giữa form/chat.
- Workspace giữ dirty/confirmed field, revision, stale-response guard và state theo browser session.
- Accept/Edit cập nhật field sạch; Reject giữ nguyên; AI không được ghi đè field người dùng đã sửa.
- Giữ retry session 404/410 từ `dev`; khi backend session bị tạo lại, workspace rebase revision nhưng
  vẫn giữ giá trị form và đánh dấu cần đồng bộ lại.
- Thêm BFF `/api/chat/field`. Backend chưa có endpoint field-update và `DraftResponse.values`, nên
  manual-edit sync end-to-end vẫn là blocker được ghi rõ.
- Giữ Next `16.2.10`, shadcn `4.13.1`, ESLint config `16.2.10` và PostCSS `8.5.16` từ release branch;
  không nhận dependency cũ có 12 advisory từ branch UI.

## QA, release và deploy baseline

- Python cài bằng `python -m pip install -e ".[api,dev]"`; web cài bằng `npm ci`.
- Có API integration test cho đúng ba mã, out-of-scope, hero 5/5, stale revision, suggestion edit,
  reset, typed provider timeout và generic OCR fallback.
- Có GitHub Actions, Dependabot, Dockerfile API/web, Compose, Nginx gateway, smoke metrics, limited
  staged-text audit, rollback runbook, pitch và shot list video.
- Docker context chặn root/nested `.env*`; Python API runtime dependency khóa version; gateway có
  timeout 75 giây trên BFF timeout 60 giây.

## Quality gate sau merge UI

| Gate | Kết quả |
| --- | --- |
| Ruff lint/format | Pass, 65 Python file formatted |
| Mypy strict | Pass, 63 source files |
| Pytest/coverage | 106 passed, 1 skipped; coverage 81.93% |
| `npm ci` / audit | Pass; 0 vulnerability |
| Reducer tests | 9 passed, gồm session recreation giữ form data |
| Next production build | Pass, 25 route; chỉ generate ba procedure slug |
| HTTP route smoke | Ba route 200; hero tạm trú 5/5; route kết hôn cũ 404 |
| Limited staged-text audit | Pass: 333 index file, 188 text file |

## Metrics gần nhất trước merge UI

- Clean revision `44d399f`, local gateway `2026-07-18T08:50:23.102344Z`: `/health` p95 8.44 ms,
  web p95 20.12 ms.
- Public gateway `2026-07-18T08:50:28.004246Z`: `/health` p95 326.07 ms, web p95 729.74 ms.
- Runtime `provider=mock`, `model=mock-scripted`; smoke không gọi model.
- Image: API `sha256:c72a78e6a5b5...9e4f`, web `sha256:b87a68c910cf...c0b7`.
- Preview ngrok chỉ hoạt động khi Docker/ngrok trên máy release còn chạy.

## Definition of Done

- [x] Backend/data đúng ba thủ tục.
- [x] Frontend catalog/route đúng ba thủ tục.
- [x] Hero orchestration API chạy độc lập 5/5 bằng scripted extractor.
- [x] Python/npm gate và route smoke đạt sau merge UI.
- [ ] Rebuild/smoke container sau merge UI.
- [ ] Manual edit sync end-to-end qua backend field-update contract.
- [ ] Browser E2E/visual/keyboard QA cho hero tạm trú.
- [ ] OCR implementation và OCR E2E thật.
- [ ] Public hosting bền vững thay tunnel tạm.
- [ ] Video dự phòng đã record và được hai người review offline.

Không push `dev` với nhãn release hoàn thành cho tới khi các mục chưa đạt được xử lý.

## Lịch sử kỹ thuật cần giữ

- LLM chỉ phân loại/trích xuất; required field, rule, phí, thời hạn và nguồn do code/data package
  đã review quyết định.
- Core/rules có Accept/Reject/Edit, revision guard, retry cap và deterministic validation.
- FastAPI dùng session ID ngẫu nhiên, TTL/capacity/per-session lock; store in-memory chỉ phù hợp một
  worker. Next BFF giữ session ID trong cookie `HttpOnly` và không đưa model key ra browser.
- Frontend có banner mô phỏng Hackathon và `noindex`; không tiếp nhận dữ liệu cá nhân thật.
