# Nhật ký tiến độ VNeGuide

## 2026-07-18 — Khắc phục chatbot web không phản hồi

- Xác định hai nguyên nhân độc lập: mọi câu guidance trên route đã seed vẫn gọi extractor trước, và
  process demo ban đầu không có network egress tới LiteLLM nên trả `provider_error`.
- Thêm whole-message allowlist để bảy topic guidance thuần được trả trực tiếp từ procedure pack đã
  review. Câu có field/nội dung hỗn hợp/thủ tục khác vẫn qua extractor; draft, revision và suggestion
  contract không đổi.
- Thêm guard ngữ cảnh fail-closed: sau `unsupported`, `ambiguous`, procedure switch hoặc provider
  failure, câu mơ hồ không được gán fact của route cũ; nhắc rõ active procedure có thể phục hồi.
- Full Python gate đạt `265 passed, 2 skipped`, coverage `80.27%`; compile, Ruff lint/format và mypy
  strict đều đạt. Next gate đạt lint, typecheck, 9 reducer tests, production build 25 route; npm audit
  báo `0 vulnerabilities`.
- Provider smoke đạt `MODEL_SMOKE_OK`, provider `litellm`, model `Qwen/Qwen3.5-9B`, structured output,
  timestamp `2026-07-18T11:40:42Z`. A/B deterministic vẫn đạt `12/12` fact/topic/source, không thêm
  model call, timestamp `2026-07-18T11:41:32Z`.
- BFF smoke trên `http://127.0.0.1:13000`: session route `1.004194` trả phí đúng với
  `present_guidance`; câu tổng hợp “Tôi đăng ký trực tuyến.” đi qua model và tạo pending suggestion
  `submission_channel=online`. Không dùng PII thật và không ghi raw provider response.

## 2026-07-18 — Thử nghiệm grounded conversational core

- Tạo nhánh `experiment/chat-core-v2` từ `dev@48f9c1f`; mọi thay đổi nằm trong worktree riêng, không
  chạm nhánh `agent/browser-e2e` hoặc ba file local ngoài scope.
- Thêm `CatalogReplyComposer` deterministic cho phí, thời gian, hồ sơ, các bước, cơ quan, kênh nộp
  và kết quả. Composer chỉ render procedure pack đã review sau khi extractor khóa procedure code.
- Guidance-only dùng `present_guidance`, không tăng clarification attempt hoặc đổi draft/revision;
  mixed turn vẫn tạo suggestion. Source ngoài pack, lỗi composer, unsupported/ambiguous và procedure
  switch đều fail closed về flow hiện hành.
- Factory mặc định `VNEGUIDE_CHAT_CORE_VARIANT=guided`; đặt `baseline` để A/B/rollback, không đổi
  FastAPI/Next.js wire contract và không thêm model call.
- A/B deterministic 12 case tổng hợp: baseline fact coverage `0/12`, guided `12/12`, topic accuracy
  `12/12`, source grounding `12/12`; reply layer chạy khoảng `0.928 ms/12 case` tại timestamp
  `2026-07-18T11:10:35Z`, engine `catalog-deterministic`, model `none`.
- Targeted core/API/release/eval đạt `92 passed`. Full pytest đạt `243 passed, 2 skipped`, coverage
  `80.04%`; repository-state test chạy với LFS filter tắt cục bộ chỉ cho subprocess status, không
  stage các binary LFS giả-dirty. Compile, Ruff lint/format và mypy strict đều đạt.
- `npm ci`, `npm audit --audit-level=moderate` đạt `0 vulnerabilities`; `npm run check` đạt lint,
  typecheck, 9 reducer tests và production build 25 route. Turbopack build cần chạy ngoài sandbox vì
  worker nội bộ phải bind cổng; không có thay đổi frontend/dependency.
- Staged release audit đạt `RELEASE_AUDIT_OK index_files=370 text_files=224`; không có secret, PII
  ngoài fixture tổng hợp, conflict marker hoặc file ngoài scope trong commit.

## Trạng thái release

- Remote baseline của lượt tích hợp: `origin/dev@f90b5e2`.
- Đã merge `origin/agent/rules-ai-eval@4a7aac3` vào local `dev` bằng `43ed537` sau khi hợp nhất
  contract context hiện hành và chạy targeted gate.
- Đã merge `origin/agent/ocr-hero@2a155a0` bằng `299cc69`; thay đổi dependency/CI/config thuộc
  Release Captain nằm trong cùng merge result. Đích push là `origin/dev`.
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

### 2026-07-18 — Context-aware extraction, rule signals và evaluation (Người 3)

- Giữ contract runtime hiện hành `ExtractionTurnContext(active_procedure_code,
  expected_field_id)` và JSON prompt envelope; model chỉ dùng context để hiểu câu trả lời ngắn,
  không dùng metadata làm evidence.
- Schema catalog-derived có `context_signals` tách khỏi form field. Text model chỉ được sinh signal
  có origin `intent_extraction`/`user_declaration`; `document_check` dành cho adapter tài liệu.
- `RuleEngine` kiểm type, origin và promotion trước khi dùng signal. Boolean signal được kiểm
  grounding/polarity theo evidence trong chính message hiện tại.
- Thêm 21 case tổng hợp cho đúng ba thủ tục, multi-turn, out-of-scope và ambiguous; fixture có
  checksum LF-normalized. Live evaluator là opt-in, khóa fixture và không ghi message/evidence/raw
  output/secret vào report.
- Giới hạn: extractor mới chỉ tạo signal candidate; conversation core chưa lưu, xác nhận và promote
  signal vào trusted state, nên chưa được coi là chức năng end-to-end.

### 2026-07-18 — Qwen OCR CT01 (Người 4)

- Thêm module biệt lập `vneguide.ocr` cho hero CT01 của thủ tục `1.004194`; model
  `Qwen/Qwen3.5-9B` đọc từ `.env` qua LiteLLM multimodal, không dùng MinerU/vLLM.
- Upload được kiểm tra magic MIME, giới hạn 8 MiB/2 trang/20 MP, chuẩn hóa trong memory và không log
  raw image. Worker chỉ bind localhost, có bearer token, queue một inference, TTL và fallback nhập tay.
- Mapper chỉ tạo candidate `USER_UPLOAD` gồm field/value/confidence/evidence, kiểm tra field bằng rule
  engine đã review và không có đường ghi draft. `OcrCandidateSink` là port để Core/API nối candidate
  vào suggestion pipeline trong PR tích hợp riêng.
- Fixture hoàn toàn tổng hợp bao phủ clear, blurred, rotated, wrong-document, MIME spoof, PDF quá số
  trang, timeout và output model lỗi; không commit ảnh giấy tờ hoặc PII thật.
- Extra `ocr` đã khai báo Pillow/pypdfium2; CI cài `.[api,dev,ocr]`. Targeted OCR gate chạy đủ
  raster ảnh/PDF đạt `33 passed`, không còn skip do thiếu dependency.
- Live smoke ngày 2026-07-18, 3 lượt ảnh CT01 tổng hợp: field recall `0.75` (9/12), latency trung bình
  `6,688` giây, lớn nhất `8,407` giây. Lệnh cố ý trả exit code `1` vì chưa đạt 4/4 mọi lượt; đây là
  baseline thật và fallback nhập tay vẫn bắt buộc.
- OCR vẫn chưa có API/UI sink và không tự ghi draft. Upload không có `Content-Length` hiện vẫn có thể
  bị buffer trước khi kiểm cap; worker phải tiếp tục chỉ bind localhost.

## Quality gate trên merge result Rules/AI + OCR

| Gate | Kết quả |
| --- | --- |
| Compileall | Pass |
| Ruff lint/format | Pass, 90 Python file formatted |
| Mypy strict | Pass, 88 source files |
| Pytest/coverage | 216 passed, 1 skipped; coverage 80.44% |
| OCR targeted | 33 passed; ảnh và PDF preprocess đều chạy |
| `npm ci` / audit | Pass; 0 vulnerability |
| Reducer tests | 9 passed |
| Next production build | Pass, 25 route; chỉ generate ba procedure slug |
| Release audit | Pass: 363 index file, 217 text file; không secret/PII/conflict marker |

### 2026-07-18 — Kết nối lại model thật với chatbot web

Next build lần đầu bị Turbopack từ chối bind cổng nội bộ trong sandbox; chạy lại ngoài sandbox đạt.
Smoke chỉ dùng dữ liệu giả và provider mock, không gửi PII hoặc gọi model ngoài.

## Definition of Done

- [x] Backend/data đúng ba thủ tục.
- [x] Frontend catalog/route đúng ba thủ tục.
- [x] Hero orchestration API chạy độc lập 5/5 bằng scripted extractor.
- [x] Backend có revisioned form-edit contract và draft snapshot.
- [x] Full Python/npm gate đạt trên merge result Rules/AI + OCR.
- [x] BFF gọi đúng revisioned backend field-edit contract bằng production server smoke.
- [ ] Manual edit sync được browser E2E xác minh qua BFF và backend.
- [ ] Rebuild/smoke container từ merge result mới.
- [x] OCR adapter/worker candidate-only và synthetic gate.
- [ ] OCR API/UI sink và browser E2E thật.
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
