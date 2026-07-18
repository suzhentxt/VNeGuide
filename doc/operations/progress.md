# Nhật ký tiến độ VNeGuide

## Trạng thái release

- Remote baseline trước merge: `origin/dev@9960bf2`; local `dev` đã nhận merge result bằng
  `55d13cd`, chưa push.
- `integration/release-dev` đã fast-forward từ `0cb4d6b` lên `9960bf2` ngày 2026-07-18.
- Đã tích hợp `origin/agent/memory-form-sync@83adb18` trên `integration/release-dev`; full gate và
  release audit trên cây hợp nhất đạt trước khi chốt merge commit local.
- Đã merge `integration/release-dev@7695039` vào local `dev` bằng `55d13cd`.
- LiteLLM, FastAPI Chat API và Next.js cùng tồn tại; backend/data và frontend chỉ hỗ trợ đúng ba mã
  `2.000635`, `1.013314`, `1.004194`.
- `.DS_Store`, `procedures.csv` và `view_parquet.py` là file local ngoài scope, không được stage.

## 2026-07-18 — Conversation memory và form sync

- Extractor nhận compact context gồm procedure đang hoạt động và field đang chờ; không gửi transcript
  hoặc draft chứa PII sang model.
- Procedure hợp lệ trong session context khởi tạo core ngay khi tạo phiên. Create/GET session trả draft
  snapshot gồm `values`, `revision`, `confirmed_fields`, `dirty_fields` và `pack_version`.
- Backend thêm `PATCH /v1/chat/sessions/{session_id}/draft/fields/{field_id}` với optimistic revision,
  catalog/rule validation và typed `409 stale_revision`/`422 invalid_field_value`.
- Manual edit được đánh dấu confirmed và dirty, tăng revision một lần, loại pending suggestion cùng
  field và không cho extractor ghi đè field người dùng đã xác nhận.
- Core lưu `asked_question_ids`, giữ procedure qua small talk/câu trả lời ngắn và giới hạn hỏi lặp.
- Store giữ per-session lock xuyên suốt request để tránh DELETE/TTL cleanup đua với model/form mutation.
- Khi tích hợp, BFF `/api/chat/field` được đổi sang gọi đúng backend bằng `PATCH` và TypeScript contract
  được mở rộng với `draft.values`, `pack_version` và top-level session draft.

## Web và release baseline đã có

- Catalog, static route và form chỉ còn ba thủ tục được review; route đăng ký kết hôn cũ trả 404.
- Hero `1.004194` có form CT01 và shared workspace với chat; reducer bảo vệ dirty field, stale response,
  reset và session recreation.
- GitHub Actions, Dependabot, Dockerfile API/web, Compose, Nginx gateway, smoke metrics, staged-text
  audit, rollback runbook và pitch checklist đã có.
- Next `16.2.10`, shadcn `4.13.1`, ESLint config `16.2.10` và PostCSS `8.5.16` được giữ từ release
  baseline; không nhận dependency cũ có advisory từ branch nguồn.

## Quality gate sau merge Người 2

| Gate | Kết quả |
| --- | --- |
| Compileall | Pass |
| Ruff lint/format | Pass, 67 Python file formatted |
| Mypy strict | Pass, 65 source files |
| Pytest/coverage | 166 passed, 1 skipped; coverage 82.87% |
| `npm ci` / audit | Pass; 0 vulnerability |
| Reducer tests | 9 passed |
| Next production build | Pass, 25 route; chỉ generate ba procedure slug |
| BFF → backend field smoke | 200; revision 0 → 1; values/confirmed/dirty/pack_version đúng |
| Limited staged-text audit | Pass: 335 index file, 190 text file |

Next build lần đầu bị Turbopack từ chối bind cổng nội bộ trong sandbox; chạy lại ngoài sandbox đạt.
Smoke chỉ dùng dữ liệu giả và provider mock, không gửi PII hoặc gọi model ngoài.

## Definition of Done

- [x] Backend/data đúng ba thủ tục.
- [x] Frontend catalog/route đúng ba thủ tục.
- [x] Hero orchestration API chạy độc lập 5/5 bằng scripted extractor.
- [x] Backend có revisioned form-edit contract và draft snapshot.
- [x] Full Python/npm gate đạt trên merge result `agent/memory-form-sync`.
- [x] BFF gọi đúng revisioned backend field-edit contract bằng production server smoke.
- [ ] Manual edit sync được browser E2E xác minh qua BFF và backend.
- [ ] Rebuild/smoke container từ merge result mới.
- [ ] OCR implementation và OCR E2E thật.
- [ ] Public hosting bền vững thay tunnel tạm.
- [ ] Video dự phòng đã record và được hai người review offline.

Không gắn nhãn release hoàn thành cho tới khi các mục chưa đạt được xử lý.

## Giới hạn kỹ thuật cần giữ

- LLM chỉ phân loại/trích xuất; required field, rule, phí, thời hạn và nguồn do code/data package đã
  review quyết định.
- `draft.revision` chỉ bảo vệ mutation form/suggestion; retry message dùng `client_turn_id`, không dùng
  revision của form làm transcript token.
- Session store in-memory chỉ phù hợp một worker và mất memory khi restart/TTL; cần shared store trước
  khi scale.
- Frontend có banner mô phỏng Hackathon và `noindex`; không tiếp nhận dữ liệu cá nhân thật.

## 2026-07-18 — Chatbot toàn cục

- Nhánh `agent/web-global-chatbot` được tạo từ `dev@f90b5e2`.
- `ChatWidget` và `ProcedureWorkspaceProvider` được chuyển lên root layout; mọi route dùng đúng một
  launcher, không còn mount lặp trong layout danh mục.
- Khi đổi procedure, request cũ bị hủy và response/session sai context không được ghi vào form.
  Message, suggestion và field BFF đều kiểm tra procedure context trước khi mutation.
- Form mutation được serialize theo revision; tạo session dùng single-flight để form và chat không tạo
  hai session cạnh tranh. Manual/dirty value tiếp tục thắng AI value.
- Field `dirty/saving/error` được snapshot và tự replay khi quay lại procedure; replay phải đồng
  bộ hết form mới cho phép retry message. Suggestion đang chờ không thể ghi đè manual edit mới hơn.
- Khi chuyển giữa phạm vi tổng quát và một procedure, UI yêu cầu tạo session đúng scope; transcript cũ
  không được trộn vào form. Rebind giữ form local và tuần tự đồng bộ các field sang session mới.
- `npm run check` đạt: ESLint, TypeScript, 27 Node tests và Next production build 25 route.
- HTTP production smoke đạt `200` và đúng một launcher trên `/`, trang danh mục và ba trang procedure.
- Chưa có visual/browser interaction smoke vì phiên này không có in-app browser khả dụng; cần kiểm tra
  responsive, focus và thao tác chat thật trong browser trước khi merge release.
