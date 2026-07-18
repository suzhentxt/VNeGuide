# Nhật ký tiến độ VNeGuide

## 2026-07-18 — Grounded conversational NLG (thay deterministic templates)

- Trước đây mọi câu trả lời assistant đều là template deterministic: lời chào/social talk bị
  extraction prompt ép thành `unsupported` (rule 11) rồi trả "nằm ngoài ba thủ tục"; câu hỏi làm
  rõ field không có `help_text` rơi vào `_missing_fact` → "liên hệ cơ quan" dù chỉ hỏi định dạng
  ngày sinh. Với người cao tuổi thì phản ứng này rất tệ.
- Thêm `GroundedResponder` (`src/vneguide/ai/grounded_responder.py`) sinh câu trả lời tự nhiên có
  grounding: LLM chỉ *diễn đạt* lại fact đã duyệt, không được bịa phí/thời hạn/giấy tờ/căn cứ ngoài
  khối context thu thập từ `ProcedureQAResponder`; phần chào/cảm ơn/giải thích khái niệm/làm rõ
  định dạng thì free-form; chủ đề lệch domain được `off_domain=true` → giữ `OUT_OF_SCOPE`.
- Prompt mới `src/vneguide/ai/prompts/conversation.py` chặn hallucination: fact chỉ từ "Thông tin
  đã duyệt", thiếu thì nói chưa có + gợi ý liên hệ cơ quan, không đoán. Trả JSON
  `{reply, off_domain}` qua `generate_structured` hiện có (không thêm method provider).
- `session.py`: nhánh `_unsupported` cold-start và `_informational` gọi responder trước; nếu
  provider lỗi/malformed thì fallback deterministic cũ (không bao giờ để citizen không có câu
  trả lời). `_unsupported` mid-flow (pending/active) vẫn giữ logic resume form. Field_help khi
  field không có `help_text` được bổ sung hint theo `field_type` (date → "nhập đầy đủ dd/mm/yyyy").
- Factory dựng `GroundedResponder` từ cùng provider/repository; `ConversationSession` nhận
  `responder` optional nên test/CLI cũ không vỡ. AGENTS.md vẫn tuân thủ: LLM không quyết định fact
  nghiệp vụ, chỉ phrase lại từ data đã review.
- Gate trên `.venv` Python 3.11.9: Ruff lint/format pass; Mypy strict pass (95 source file);
  Pytest `343 passed, 1 skipped` (thêm 12 test: 7 responder + 5 conversation), coverage `80.83%`;
  `demoweb/npm run check` pass (lint/typecheck/Node test/Next build 25 route). Release audit
  full-index chậm trên Windows nên dùng bounded scan: 4 file mới không có secret/PII/12 chữ số.
- Live smoke GLM-5.2 (HTTP, dữ liệu giả, không PII): "xin chao ban" → "Dạ em chào anh/chị ạ! Em
  là trợ lý VNeGuide, sẵn sàng hỗ trợ ba thủ tục..." (`off_domain=false`, `PRESENT_GUIDANCE`);
  "ngay sinh la ngay thang nam hay ngay thoi" → "Dạ, anh/chị nhập đầy đủ cả ngày, tháng và năm
  sinh (ví dụ 01/01/1990) nhé ạ." Không còn "nằm ngoài ba thủ tục" / "liên hệ cơ quan" cho hai
  trường hợp này.
- Chưa commit, chưa push. Phần `ambiguous` và mid-flow `unsupported` vẫn dùng template; làm rõ
  khái niệm chung ("giấy khai sinh là gì") chưa có nhánh riêng — có thể mở rộng sau nếu cần.

## 2026-07-18 — invalid_value fallback cho field sai định dạng

- Khi người dùng cung cấp giá trị field không khớp pattern (vd số định danh 9/11/14 chữ số thay
  vì 12), `_validate_value` raise `ExtractionSchemaError("invalid_value")` → extractor cũ gộp vào
  `malformed_output` → `_technical_fallback` trả "em chưa nghe rõ" / "nhập trực tiếp trên biểu mẫu"
  mà không nói rõ sai gì. Rule `BIRTH-ID-001` có câu sửa "nhập đủ 12 chữ số" nhưng không bao giờ
  chạy vì giá trị bị chặn ở tầng extraction.
- Sửa theo hướng nhẹ (giữ hard-reject ở extraction, chỉ đổi câu fallback): `ExtractionSchemaError`
  thêm `field_id` optional; `_validate_value` truyền `field_id` khi raise `invalid_value`; extractor
  bắt riêng `invalid_value` (không retry vì deterministic) và trả `error_code="invalid_value"` +
  `invalid_field_id` qua `ExtractionOutcome`; `_technical_fallback` sinh câu sửa theo field:
  "Dạ, mục {label} chưa đúng định dạng. {hint} Anh/chị kiểm tra rồi nói lại giúp em ạ." — hint lấy
  từ `help_text` hoặc `field_type` (date → "nhập đầy đủ dd/mm/yyyy").
- Giữ nguyên hard-reject cho fullwidth/garbage char (test `test_rejects_type_pattern_enum_bound`
  vẫn pass, chỉ đổi error_code sang `invalid_value`). `invalid_reply`/`invalid_root`/... vẫn
  `malformed_output`.
- Gate: Ruff lint/format pass; Mypy strict pass (95 file); Pytest `345 passed, 1 skipped`
  (+2 test invalid_value), coverage `80.77%`. Probe trực tiếp: citizen_id 11 chữ số →
  `error_code=invalid_value`, `invalid_field_id=requester_personal_id`.
- Chưa commit, chưa push.


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

## 2026-07-18 — Chatbot toàn cục

- Commit `agent/senior-conversation@22810e5` (cùng tip với `agent/web-global-chatbot`) đã
  được hợp nhất vào local `dev` mới nhất sau Rules/AI + OCR. Nhánh nguồn chưa có
  phần NLG/xác nhận thủ tục cho người cao tuổi.
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
- Gate trên merge result đạt: Compileall, Ruff lint/format, Mypy 88 source file, Pytest
  `216 passed, 1 skipped`, coverage `80.42%`; skip duy nhất là live-model opt-in.
- `npm run check` đạt: ESLint, TypeScript, 27 Node tests và Next production build 25 route.
- Full-index `release_audit.py` không hoàn tất trong thời gian giới hạn trên Windows và đã
  được dừng; staged-diff audit thay thế không thấy conflict marker, secret, `.env` hay
  chuỗi định danh 12 chữ số mới.
- HTTP production smoke đạt `200` và đúng một launcher trên `/`, trang danh mục và ba trang procedure.
- Chưa có visual/browser interaction smoke vì phiên này không có in-app browser khả dụng; cần kiểm tra
  responsive, focus và thao tác chat thật trong browser trước khi merge release.

## 2026-07-18 — Hội thoại xác nhận thủ tục và extraction bền vững

- Tạo nhánh `agent/senior-conversation-v2` từ local `dev@7fac2858`; không sửa data package hoặc mở rộng
  ngoài ba mã thủ tục đã khóa.
- Session tổng quát nay giữ `pending_procedure_code`: intent được nhận diện phải qua một lượt xác nhận
  `Đúng`/`Không phải` trước khi kích hoạt draft. Lượt xác nhận deterministic không gọi model, không tăng
  revision và không tạo suggestion sớm. Session được khởi tạo từ route thủ tục vẫn bỏ qua bước này.
- Nếu người dùng nêu rõ thủ tục khác khi đang chờ, core thay lựa chọn pending và hỏi lại. Lượt mơ hồ,
  ngoài phạm vi hoặc lỗi provider không làm mất lựa chọn pending. `close`/reset tạo state sạch.
- Câu hỏi, manual fallback, suggestion và kết quả validation dùng tiếng Việt lịch sự. Field label và
  tập enum value vẫn lấy từ catalog; ba tên thủ tục rút gọn được quản lý tập trung riêng cho hội thoại.
  Không hiển thị field ID hoặc enum value kỹ thuật cho người dùng.
- Câu hỏi enum liệt kê rõ phương án tiếng Việt; chín field boolean có câu riêng và luôn giữ quy ước
  `Có=True`, tránh phủ định kép cho các khai báo “không tranh chấp/không thuộc địa điểm cấm”.
- Lượt xác nhận có thêm dữ liệu, ví dụ `Đúng, tôi nộp trực tuyến`, vẫn tạo suggestion cho dữ liệu được
  trích ở chính lượt đó. Pending procedure được đánh dấu bằng `confirmation_required=true` trong
  extraction context và chỉ được activate sau outcome cùng mã. Lượt intent đầu tiên vẫn không
  auto-commit field trước khi xác nhận.
- Phủ nhận dài như `Vâng nhưng không phải thủ tục này` xóa pending bằng guard deterministic ngay cả
  khi model trả nhầm cùng mã. Nếu cùng câu nêu rõ thủ tục khác đã review, core chỉ thay pending sang
  mã mới, không activate sớm và không bắt reset.
- Phản hồi sau Accept/Reject/Edit và manual form edit được lưu vào `state.messages`; web thay transcript
  từ API nên không còn làm mất câu hỏi kế tiếp trong khi `asked_question_ids` đã đánh dấu là đã hỏi.
- LiteLLM parse JSON sạch trước, sau đó mới phục hồi riêng prefix thinking kết thúc bằng `</think>`;
  duplicate key, trailing prose, JSON không đóng và non-standard constant vẫn bị từ chối.
- LiteLLM extraction gửi `temperature=0`; prompt khóa thêm ví dụ route trực tiếp cho tạm trú và xác nhận
  điều kiện nhà ở. Probe model thật cho câu `Tôi muốn đăng ký tạm trú` đạt `5/5` lần liên tiếp.
- Candidate field/context có evidence không khớp bị loại riêng, không làm mất intent hoặc candidate tốt.
  Lỗi root, procedure, field ID, type, bounds, duplicate và origin không an toàn vẫn fail cứng.
- Provider schema vẫn khóa exact root và catalog ID nhưng được rút từ khoảng 18 KB/44 nhánh `anyOf`
  xuống dưới 5 KB. Type, procedure ownership và evidence tiếp tục được validator server-side kiểm tra.
  Thay đổi này sửa lỗi HTTP 500 thực tế của gateway khi compile schema lớn.
- `reply` NLG là nullable structured field. Core chỉ nhận ba acknowledgement chung trong allowlist và
  chỉ dùng làm lời mở đầu; model không được thay câu hỏi, next action, validation hoặc kết luận nghiệp vụ.

### Gate hội thoại senior

| Gate | Kết quả |
| --- | --- |
| Compileall | Pass |
| Ruff lint/format | Pass, 90 file |
| Mypy strict | Pass, 88 source file |
| Pytest/coverage | 252 passed, 1 skipped; coverage 80.62% |
| API recovery/confirmation | Pass; pending qua GET session, xác nhận không gọi extractor lần hai |
| `npm run check` | Pass; lint, typecheck, 27 test và Next build 25 route |
| Provider smoke | `MODEL_SMOKE_OK`, LiteLLM, `zai-org/GLM-5.2`; route tạm trú 5/5 |
| Live conversation smoke | Pass; intent → confirm → active và `Đúng, tôi nộp trực tuyến` → pending `submission_channel` |
| Release audit | Full-index scan tiếp tục quá chậm trên Windows và đã dừng; bounded diff scan pass cho conflict marker, secret, tracked `.env` và chuỗi định danh 12 chữ số mới |

Live smoke chỉ dùng dữ liệu giả. Gateway model vẫn là HTTP không mã hóa, vì vậy không được dùng PII hoặc
hồ sơ hành chính thật cho đến khi có HTTPS.

Môi trường máy này từng mất Python gốc mà `.venv` tham chiếu. Python `3.11.9` đã được cài lại theo phạm
vi user đúng tại `C:\Users\hautt\AppData\Local\Programs\Python\Python311`; `.venv` chạy lại bình thường.
Kết quả này đã được xác minh ngoài sandbox. Sandbox mặc định của coding agent không được đọc đường dẫn
Python trong user profile nên có thể báo nhầm executable không tồn tại; đây không phải lỗi của `.venv`
trong terminal người dùng.

## 2026-07-18 — Grounded Q&A cho ba thủ tục

- Extraction thêm classification `informational` và 11 `QATopic`. Output FAQ chỉ chứa route/topic,
  target field và enum tham chiếu có evidence; `fields`/`context_signals` phải rỗng nên câu hỏi không
  thể tự điền form. Prompt phân biệt `theo danh sách` với `theo danh sách tức là gì`, câu không dấu,
  multi-topic và follow-up.
- `ProcedureQAResponder` không giữ provider và dựng toàn bộ câu trả lời từ service info, checklist,
  field catalog, guidance, rule/scope và source register đã duyệt. Phí ba thủ tục, ranh giới giấy tờ
  với field biểu mẫu, legal-basis và official-review được khóa deterministic.
- Ba procedure pack lên `2.1.0`; mỗi service-info key có source riêng. `registration_mode` có help cho
  đủ ba lựa chọn, gồm CT01 từng người/văn bản danh sách và trường hợp đơn vị lực lượng vũ trang.
- FAQ đầu phiên đặt pending procedure nhưng không đổi draft/revision; lượt `Đúng` kích hoạt form mà
  không gọi model. FAQ trong form giữ values, revision, confirmed/dirty, suggestion, attempts và
  asked-question state; FAQ thủ tục khác chỉ tham khảo, muốn chuyển phải reset. Topic/procedure Q&A
  gần nhất nằm ngoài draft và được gửi dưới dạng bounded context cho câu nối tiếp.
- API public không đổi. FAQ trước khi active vẫn trả đúng source records. Web dùng mapper trạng thái
  tiếng Việt; chỉ hiện “Sẵn sàng kiểm tra trước khi nộp” khi `complete`, không còn field thiếu và
  validation thật sự là `ready_to_submit`; nguồn không có URL chỉ hiện tên, không tạo link rỗng.
- Thêm 15 case `synthetic_grounded_qa.jsonl` có checksum và case extraction informational trong
  `tests/evals/intent_cases.jsonl`. Đây là fixture tổng hợp, chưa phải accuracy của model thật.

### Bằng chứng kiểm tra grounded Q&A

| Gate | Kết quả |
| --- | --- |
| Renderer + conversation targeted | Pass: 91 test trước ba regression review cuối |
| Chat API targeted | Pass: 5 test |
| Form-sync API sau bump pack | Pass: 15 test |
| Mypy strict | Pass: 90 source file trước regression review cuối |
| Ruff lint/format | Pass: 93 file sau review cuối |
| Frontend `npm run check` | Pass: lint, typecheck, 36 test, Next build 25 route |
| Q&A fixture parse/checksum | Pass: 15 case, LF-normalized checksum khớp |

Full Pytest lần đầu thu thập 313 test và phát hiện hai kỳ vọng cũ (`pack_version=2.0.0`) trong
form-sync; chúng đã được sửa và suite form-sync đạt 15/15. Phiên công cụ sau đó hết hạn mức chạy ngoài
sandbox; mặc dù `.venv` đã chạy được trong terminal người dùng, sandbox mặc định không đọc được Python
user-level nên chưa chạy lại full Pytest/Mypy sau regression review cuối, chưa chạy live Q&A smoke và
chưa tạo commit follow-up. Không công bố metric accuracy model từ fixture hoặc test mock.

### Bổ sung xác minh sau khi phiên công cụ hết hạn mức

- `.venv` là Python 3.11.9 và `vneguide` import được.
- Full gate trên `.venv` đạt: Ruff lint/format pass, Mypy strict pass (91 source file), Pytest
  `331 passed, 1 skipped` (kể cả form-sync 15/15 sau bump pack), `demoweb/npm run check` pass
  (lint, typecheck, Node test, Next build 25 route).
- Release audit thoát 0; chỉ còn cảnh báo định danh 12 chữ số trong `data/procedures/viec-lam/*`
  (discovery seed, ngoài scope ba thủ tục, có trước thay đổi này).
- `repository.verify_checksums()` trả sạch; ba pack ở `v2.1.0`, `status=approved`.
- Provider smoke với `zai-org/GLM-5.2` qua HTTP gateway trả `MODEL_SMOKE_OK`.
- E2E live (dữ liệu giả, không PII): câu "đăng ký tạm trú cần giấy tờ gì" → bot phân loại
  `informational`, trả lời grounded từ checklist, cite `SRC-DVC-1004194`/`SRC-CIRC-53-2025`/
  `SRC-LAW-154-2024`, đặt pending procedure, bridge sang form (`confirm_procedure`); lượt "Đúng"
  kích hoạt form không gọi model; câu "lệ phí bao nhiêu" khi đang điền form trả lời phí đúng
  (7.000đ/15.000đ cá nhân, 5.000đ/10.000đ theo danh sách, lưu ý kiểm tra chính thức) mà draft
  revision và procedure không đổi.
- Chưa push; tạo một commit follow-up trên `agent/senior-conversation-v2`.
