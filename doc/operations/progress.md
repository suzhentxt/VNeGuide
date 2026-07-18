# Nhật ký tiến độ VNeGuide

## Trạng thái release

- Nhánh tích hợp: `integration/release-dev`, tạo từ `dev` tại `1d3e566`.
- Đã merge `tuan` bằng `4865ceb` và cherry-pick tài liệu scope `709b795` thành `ff06998`.
- LiteLLM, FastAPI Chat API và Next.js cùng tồn tại trên cây tích hợp.
- Backend/data chỉ có đúng `2.000635`, `1.013314`, `1.004194`.
- Frontend từ `tuan` vẫn chỉ có route Hôn nhân và gia đình ngoài scope; release sản phẩm chưa đạt.
- Không có branch UI/OCR mới trên origin tại lần fetch `2026-07-18 15:20 +07:00`.

## 2026-07-18 — QA, release và deploy

- Cài Python bằng `python -m pip install -e ".[api,dev]"` và web bằng `npm ci`.
- Thêm API orchestration/integration test in-process cho đúng ba mã, out-of-scope, hero tạm trú,
  stale revision, suggestion edit, reset, typed provider timeout và generic OCR safe fallback.
- Nâng Next `16.2.1 → 16.2.10`, shadcn `4.1.0 → 4.13.1`, đồng bộ eslint config và override
  PostCSS `8.5.16`; `npm audit` giảm từ 12 vulnerability xuống 0.
- Thêm GitHub Actions, Dependabot, Dockerfile API/web, Compose, Nginx gateway, smoke metrics và
  release audit staged text cho secret pattern phổ biến, số định danh 12 chữ số và conflict marker.
- Thêm release evidence, rollback runbook, pitch và shot list video dự phòng.
- Build container API/web đạt; Compose chạy API/web/gateway healthy.
- Public preview tạm thời qua ngrok đạt 5/5 HTTP 200 cho `/` và `/health`.

## Quality gate trên cây tích hợp

| Gate | Kết quả |
| --- | --- |
| `ruff check src tests deployment` | Pass |
| `ruff format --check src tests deployment` | Fail duy nhất `src/vneguide/api/session_store.py` từ branch `tuan` |
| `mypy` | Pass, 62 source files |
| `pytest -q` | 103 passed, 1 skipped |
| Coverage | 81.60%, đạt ngưỡng 80% |
| Release API integration | 12 passed, gồm hero 5/5 |
| `npm ci` | Pass trên host npm 11.6.2 và container npm 11.16.0 |
| `npm audit --audit-level=moderate` | 0 vulnerability |
| `npm run check` | Pass: ESLint, TypeScript, Next build 29 page |
| Docker build/health | Pass cho API, web, gateway |
| Staged repository audit | Pass: 333 tracked file, 188 text file |

Formatter failure không được che bằng exclude hoặc hạ version. File thuộc API owner nên Release Captain
đã bỏ thay đổi format tình cờ khỏi commit; cần owner sửa hoặc người dùng cho phép thay đổi ngoài scope.

## Metrics đã đo

- Local gateway, `2026-07-18T08:35:44.176021Z`, `mock/mock-scripted`, 5 mẫu: `/health` p95
  11.68 ms, web p95 12.93 ms.
- Public gateway, `2026-07-18T08:35:45.553122Z`, `mock/mock-scripted`, 5 mẫu: `/health` p95
  351.28 ms, web p95 469.29 ms.
- Image đã smoke: API `sha256:a3e4771015bf...a092`, web `sha256:e8b84b8ea57d...ed1a`.
- URL preview: `https://moschate-terri-dereistically.ngrok-free.dev`; chỉ hoạt động khi Docker/ngrok
  trên máy release còn chạy.

## Definition of Done

- [x] Backend/data đúng ba thủ tục.
- [x] Hero orchestration chạy độc lập 5 lượt bằng scripted extractor.
- [x] Python lint/type/test/coverage và npm check đạt.
- [ ] Python formatter còn fail một file API ngoài ownership.
- [x] npm audit và limited staged-text pattern scan đạt.
- [x] Infra metrics có lệnh, provider/model label và timestamp; chưa gọi model trong smoke.
- [x] Public preview và `/health` hoạt động ở tầng hạ tầng.
- [ ] Frontend route/form đúng ba thủ tục.
- [ ] Browser E2E và manual edit trực tiếp trên form.
- [ ] OCR implementation và OCR E2E thật.
- [ ] Public hosting bền vững thay cho tunnel tạm.
- [ ] Video dự phòng đã record và được hai người review offline.

Không merge release vào `dev` với nhãn hoàn thành cho tới khi các mục chưa đạt được xử lý.
