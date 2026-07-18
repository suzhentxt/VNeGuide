# Nhật ký tiến độ VNeGuide

## 2026-07-18 — Hội thoại thân thiện và điền từng trường ngay trong chat

- Lời chào, cảm ơn và hội thoại xã giao không còn bị trình bày là dịch vụ ngoài MVP. Core chỉ dùng
  thông báo ngoài phạm vi khi câu hiện tại nêu rõ một dịch vụ/thủ tục không thuộc ba procedure pack;
  nếu đang làm hồ sơ, small talk giữ nguyên procedure và đưa người dùng trở lại trường đang điền.
- Nhận các cách yêu cầu trợ giúp tự nhiên và có lỗi gõ như `hướng dẫn tôi điền nôis đi`. Agent không
  gọi model cho intent trợ giúp mà tiếp tục đúng field còn thiếu, nêu nhãn field và hướng dẫn nhập từ
  type/pattern/minimum đã review. Cơ chế chống hỏi lặp không còn đẩy người dùng ra biểu mẫu quá sớm.
- API missing-field trả thêm `field_type` và `input_hint`. Chat chỉ hiển thị một field card mỗi lần:
  enum/boolean dùng nút lớn; text/date/integer/number dùng input phù hợp. Nút xác nhận ghi field thật
  qua revision guard và agent hỏi field tiếp theo. Chấp nhận/sửa/bỏ suggestion cũng được ghi thành
  lượt hội thoại và hiện ngay lời hướng dẫn kế tiếp.
- Agent chỉ đề xuất lưu thông tin dùng lại sau khi gate kê khai đã đạt và wizard chuyển khỏi bước 1.
  Trước thời điểm đó, card lưu bị ẩn; autofill từ ví cũ vẫn cần người dùng đồng ý và xác nhận lại.
- Gate đạt: full Python `277 passed, 2 skipped`, coverage `80.55%`; mypy strict trên 94 source;
  frontend lint/typecheck và `21` unit test; Next production build 25 route. BFF smoke bằng dữ liệu
  tổng hợp xác nhận greeting
  không out-of-scope, help trả field metadata, chọn requester type và nhập họ tên tăng revision
  `0 → 1 → 2`, rồi câu help có lỗi gõ tiếp tục đúng field số định danh. API `/health` trả `ok`.
- In-app Browser vẫn không khả dụng; chưa có click/keyboard/screenshot tự động. BFF smoke, build và
  test contract không thay thế browser E2E.

## 2026-07-18 — Chọn nơi tiếp nhận trước khi vào hồ sơ và trợ lý điền thực tế

- Luồng xác nhận dịch vụ trong chat giờ mở trang chi tiết thủ tục thay vì nhảy thẳng vào wizard.
  Người dùng chọn tỉnh/thành phố và phường/xã/cơ quan tiếp nhận tại đây; nút `Nộp hồ sơ` chỉ bật khi
  lựa chọn hợp lệ và mang nơi tiếp nhận sang hồ sơ. Wizard không hỏi lại các mục địa điểm này.
- Nút `Nhờ trợ lý điền cùng tôi` tự gửi câu lệnh hướng dẫn ẩn. Core trả lời deterministic từ field
  catalog, hỏi từng mục một và không gọi model/out-of-scope guard cho chính yêu cầu trợ giúp này.
- Enum và boolean được trả thành lựa chọn lớn ngay trong cửa sổ chat. Chọn một giá trị cập nhật field
  thật qua revision guard, ghi lượt người dùng bằng nhãn tiếng Việt, xác nhận field và hỏi mục kế tiếp;
  transcript không lộ tên field kỹ thuật.
- Đề xuất lưu/điền lại thông tin dùng chung được chuyển vào agent. Ví chỉ lưu trong session browser;
  agent chỉ lưu hoặc autofill sau khi người dùng đồng ý, và dữ liệu autofill vẫn phải được xác nhận
  trên biểu mẫu trước khi qua bước tiếp theo.
- Gate đạt: full Python `275 passed, 2 skipped`, coverage `80.40%`, Ruff lint/format và mypy strict
  trên 94 source file; frontend lint/typecheck và `21` unit test; Next production build thành công
  với 25 route. BFF smoke xác nhận
  trợ giúp → lựa chọn `Cá nhân hoặc hộ gia đình` → draft revision `1` → hỏi `Họ tên người đăng ký`;
  detail và submission URL hợp lệ đều trả `200`, `/health` trả `ok`.
- In-app Browser không khả dụng nên chưa có bằng chứng click/keyboard/screenshot trong phiên này;
  HTTP/BFF smoke và unit/integration test không thay thế browser E2E.

## 2026-07-18 — Luồng trợ lý đồng hành hồ sơ bốn bước

- Thay wizard nộp hồ sơ chung bằng luồng dùng trực tiếp field catalog đã review cho cả ba thủ tục:
  nơi tiếp nhận, kê khai, giấy tờ, kiểm tra/nhận kết quả. Enum/boolean/date/number dùng control dễ
  hiểu; field bắt buộc do catalog quyết định, không do LLM.
- Chat phải hiện thẻ tên dịch vụ và nhận xác nhận rõ ràng trước khi điều hướng. URL nộp hồ sơ thiếu
  `confirmed=1` bị trả `307` về trang chi tiết; xác nhận từ modal hoặc chat mới tạo URL hợp lệ.
- Shared workspace ghi nguồn dữ liệu `manual`/`assistant`/`wallet`. Người dùng tự nhập được xác nhận
  ngay; ví thông tin chỉ lưu trong session trình duyệt, autofill ở trạng thái chưa xác nhận và chặn
  bước tiếp theo cho tới khi người dùng kiểm tra, xác nhận rồi đồng bộ lần lượt về draft API.
- Mỗi bước có panel trợ lý, nút mở chat kèm câu hỏi theo bước và danh sách mục còn thiếu. Kê khai,
  giấy tờ bắt buộc và địa chỉ bưu chính đều có gate, thông báo lý do bằng tiếng Việt và control tối
  thiểu 48 px cho người lớn tuổi/người ít quen công nghệ.
- `npm` lint/typecheck đạt; 19 unit test đạt, gồm route xác nhận, missing-field gate, wallet confirm
  và reducer source. Next production build ngoài sandbox đạt 25 route. HTTP production smoke xác
  nhận ba URL hợp lệ đều `200`, URL bản sao khai sinh chưa xác nhận trả `307` và cả ba trang có đúng
  nội dung wizard mới.
- In-app Browser không khả dụng nên chưa có manual click/keyboard/screenshot. Dockerfile đã mang đúng
  `field_catalog.json` duy nhất vào builder/runner nhưng chưa chạy lại Docker image trong phiên này.

## 2026-07-18 — Memory nhiều lượt và UX dễ dùng cho người dân

- Tái hiện chuỗi lỗi thật: sau câu mơ hồ “làm giấy khai sinh”, câu trả lời rút gọn “xin bản sao” bị
  mất ngữ cảnh; typo “bảo sao” bị coi ngoài phạm vi; “cho con tôi” chuyển quá sớm sang tên field kỹ
  thuật.
- Session giờ giữ trạng thái câu hỏi làm rõ, hiểu lựa chọn rút gọn ở lượt kế tiếp và nhận typo
  `bảo sao` trong cụm xin bản sao Giấy khai sinh. Câu “cho con tôi” được ghi nhớ và xác nhận bằng
  tiếng Việt; core không tự suy ra tư cách pháp lý khi data package chưa có ánh xạ đã review.
- Câu hỏi `requester_type` được diễn đạt thành ba tư cách dễ hiểu. UI thêm các nút trả lời nhanh cao
  tối thiểu 48 px, tăng cỡ chữ hội thoại/input và vẫn giữ ô nhập tự do; không hiển thị enum hoặc tên
  field nội bộ cho người dùng.
- BFF smoke ba lượt trên session thật đạt: `ask_clarification` → chọn procedure `2.000635` → xác nhận
  đã ghi nhớ “cho con”; transcript có đủ sáu message và draft không bị tự điền. Trình duyệt tích hợp
  không khả dụng nên chưa có click/screenshot; hành vi nút được bảo vệ bằng unit test frontend.
- Full Python gate đạt `272 passed, 2 skipped`; compile, Ruff lint/format và mypy đều đạt. Next
  `npm run check` đạt lint, typecheck, 13 test và production build 25 route.

## 2026-07-18 — Hiển thị chatbot trên toàn bộ demoweb

- Tái hiện trang chủ trả HTTP `200` nhưng không có nút chatbot: `ChatWidget` và workspace provider
  chỉ được mount trong layout `/hon-nhan-va-gia-dinh`.
- Chuyển `ProcedureWorkspaceProvider` và `ChatWidget` lên root layout, bỏ mount lặp ở layout con.
  Chatbot giờ xuất hiện trên trang chủ và mọi route; các route thủ tục vẫn dùng chung workspace với
  biểu mẫu như trước.
- HTML smoke xác nhận cả `/` và hero tạm trú đều có đúng một nút `Mở trợ lý VNeGuide`, không bị render
  trùng. `npm run check` đạt lint, typecheck, 11 test và production build 25 route.

## 2026-07-18 — Sửa phân loại “làm giấy khai sinh” và trạng thái hồ sơ

- Tái hiện trên phiên route `1.004194`: câu “tôi muốn làm giấy khai sinh” từng bị model gán
  `unsupported`, dù cụm từ này có thể chỉ cấp bản sao Giấy khai sinh trong phạm vi hoặc đăng ký khai
  sinh mới ngoài phạm vi.
- Thêm guard deterministic, fail-closed cho đúng nhóm câu mơ hồ này trước extractor. Chatbot hỏi rõ
  người dùng muốn bản sao hay đăng ký mới, nêu đúng giới hạn hỗ trợ và giữ nguyên draft/procedure
  hiện tại; các câu rõ nghĩa như “bản sao/trích lục” hoặc “đăng ký khai sinh” vẫn đi qua extractor.
- UI không còn hiển thị `ready_to_submit` như trạng thái hoàn tất khi `missing_fields` còn phần tử.
  Trường hợp rule không có issue nhưng draft còn thiếu được trình bày là “Hồ sơ chưa đủ thông tin” và
  không hiện readiness score; contract rule/completeness hiện hành không bị thay đổi.
- Full Python gate đạt `268 passed, 2 skipped`; compile, Ruff lint/format và mypy đều đạt. Next lint,
  typecheck, 11 unit test và production build 25 route đạt.
- BFF smoke qua `http://127.0.0.1:13000` trả `ask_clarification`, giữ procedure `1.004194`, draft
  revision `0`, đủ 11 missing field và câu trả lời phân biệt hai ý định. Trình duyệt tích hợp không
  khả dụng trong phiên, nên visual regression được bảo vệ bằng presentation unit test thay vì bằng
  chứng click/screenshot.

## 2026-07-18 — Chuyển chatbot local sang OpenAI

- Tái hiện lỗi cấu hình trước thay đổi: provider vẫn là LiteLLM/Qwen nhưng key mới có định dạng
  OpenAI nằm dưới biến LiteLLM; provider smoke trả `MODEL_SMOKE_FAILED: provider_error`.
- `.env` local đã được chuyển sang `provider=openai`, `model=gpt-5.6-luna` và đúng biến
  `VNEGUIDE_API_KEY`. File vẫn bị Git ignore; secret không xuất hiện trong log, diff hoặc commit.
- Chọn model bằng cùng một câu synthetic: `gpt-4.1-mini` phản hồi nhanh nhưng gán sai “trực tuyến”
  thành `direct`; `gpt-5.6-luna` trả đúng `online`. Không giữ cấu hình nhanh nhưng sai nghiệp vụ.
- Provider smoke cuối đạt `MODEL_SMOKE_OK provider=openai model=gpt-5.6-luna
  structured_output=true`, timestamp `2026-07-18T12:45:28Z`.
- Live three-procedure smoke nhận đúng `2.000635`, `1.013314`, `1.004194`; case tạm trú tạo đúng
  `submission_channel=online`, tổng thời gian ba request khoảng `5.271 s`.
- BFF smoke cuối trả HTTP `200`, `confirm_suggestion`, `submission_channel=online`, draft revision
  vẫn `0`; thời gian lượt web khoảng `1.415 s`. Trang hero tạm trú trả HTTP `200`.
- Targeted config/provider/core/API gate đạt `104 passed`. Browser tab tích hợp không khả dụng trong
  phiên nên chưa có bằng chứng click/visual; HTTP/BFF smoke không thay thế browser E2E.
- OCR Qwen hiện dùng chung provider/model config và không thể chạy bằng chat `.env` OpenAI. Giữ OCR
  tắt hoặc chạy process với env riêng cho tới khi tách cấu hình OCR khỏi chatbot.

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
- [x] Manual edit sync được browser E2E xác minh qua BFF và backend.
- [x] Rebuild/smoke API container từ merge result mới.
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

### 2026-07-18 — Chuẩn bị Vercel production

- Project Vercel `trinhs-projects-e6e09c31/vneguide` đã được tạo với Root Directory `demoweb`,
  framework Next.js, Node.js 24, build `npm run build`, install `npm ci` và output `.next`.
- Frontend import trực tiếp `data/catalog/field_catalog.json`; Next output tracing/Turbopack dùng repo
  root để không tạo bản sao runtime của data package. `.vercelignore` chỉ cho phép field catalog cần
  thiết và loại `.env`, cache, dependency local, Python source, test và tài liệu khỏi payload.
- `VNEGUIDE_API_BASE_URL` production đã trỏ tới API preview ngrok; biến này không chứa secret. API
  `/health` trả `200 {"status":"ok"}` ngay trước lần deploy.
- Frontend gate đạt: ESLint, TypeScript, 21/21 test và Next production build 25 route.
- Lần upload đầu dừng ở bước detect Next.js vì Root Directory còn ở repo root; cấu hình project sau
  đó đã được sửa và giữ lại như evidence của lần phát hành lỗi.
- Redeploy source cũ sau khi sửa Root Directory đã nhận đúng Next.js 16.2.10 nhưng thất bại vì archive
  không có `demoweb/src`: mẫu `.vercelignore` `src` không neo ở root đã loại cả frontend source.
  Pattern đã đổi thành `/src`; các data directory được loại tường minh để giữ duy nhất
  `data/catalog/field_catalog.json`. Vercel dry-run xác nhận có frontend app và field catalog, không có
  `src/vneguide` hoặc catalog khác. Redeploy archive cũ sẽ tiếp tục thất bại.
- Fresh production deployment `HGBB73U7JGdaQay1V8DcU8tvNKGc` đã `READY`; alias công khai là
  `https://vneguide.vercel.app/`. SSO Protection đã tắt sau xác nhận rõ của chủ project.
- Smoke 2026-07-18 23:29 ICT: trang chủ và ba procedure route trả `200`; backend ngrok `/health`
  trả `200`; tạo phiên qua production BFF trả `201`. `/api/portal-options` thiếu query bắt buộc trả
  `400` đúng validation contract.
- Kiểm tra lại 23:34 ICT xác nhận tunnel đã dừng: ngrok trả HTML `404 ERR_NGROK_3200`, production
  BFF trả JSON `invalid_backend_response`. Vì vậy public frontend đã bền vững nhưng chatbot chưa có
  backend hosting bền vững; smoke trước đó chỉ hợp lệ trong lúc FastAPI và ngrok cùng chạy.

### 2026-07-18 — Deploy Render FastAPI

- Thêm Blueprint `render.yaml` cho Python web service `vneguide-api`: Free plan, region Singapore,
  branch `experiment/chat-core-v2`, health check `/health`, auto-deploy sau khi CI pass.
- Blueprint chỉ khai báo tên secret `VNEGUIDE_API_KEY` với `sync: false`; provider/model công khai là
  `openai`/`gpt-4o-mini`. Không commit `.env`, key hoặc dữ liệu cá nhân.
- Render CLI Blueprint validation trả `valid: true` với một create action; API targeted gate
  `29 passed`. Image `vneguide-api:render-test` build từ
  `deployment/api.Dockerfile` và container health trả `200 {"status":"ok"}` trên cổng 18001.
- Render service `srv-d9dqule1a83c73b989s0`, deploy `dep-d9dr0nf41pts73docp7g` đã `live` tại
  `https://vneguide-api.onrender.com` với secret nhập qua Dashboard; không ghi hoặc in key.
- Direct live smoke: health `200`, create session `201`, message model thật `200`. Vercel production
  đã đổi backend URL sang Render và deployment `8tf1DLcUwfYtJFw18UyALrUn4zEW` đã `READY`.
- E2E Vercel → Render → OpenAI bằng dữ liệu tổng hợp: create session `201`/1.178 giây, message
  `200`/5.039 giây; reply hỏi đúng `requester_type` và không còn phụ thuộc ngrok.

### 2026-07-19 — Sửa false positive release audit trên PR #5

- GitHub Actions merge result có thêm corpus từ `dev`; regex cũ nhầm 12 chữ số nằm trong UUID,
  SHA-256, mã thủ tục dạng `TP-G12.000...` và placeholder lặp là số định danh cá nhân.
- Scanner vẫn kiểm tra toàn bộ data package nhưng chỉ báo token 12 chữ số độc lập, không nằm trong
  mã máy; regression test xác nhận vẫn bắt số CCCD tổng hợp 12 chữ số đứng độc lập.
- Gate local đạt: Ruff/format/mypy sạch, `279 passed`, `2 skipped`, coverage `80.55%`. Audit branch
  đạt `385/239`; audit trên merge result `origin/dev` + candidate đạt `17379/11569` file.
- Job container sau đó phát hiện Next standalone nằm dưới `/app/app` trong image, trong khi
  `web.Dockerfile` chạy/copy asset ở `/app`. Dockerfile đã dùng `app/server.js`,
  `app/.next/static` và `app/public`; Compose local xác nhận API/web/gateway healthy. Smoke mock trên
  gateway cổng test đạt API `3/3` và web `3/3`, toàn bộ HTTP `200`.

### 2026-07-19 — README theo rubric chấm 100 điểm

- README có bản đồ evidence và nội dung riêng cho sáu tiêu chí: kỹ thuật 20, AI-Native 20, khả thi
  kinh doanh/pilot 20, UX 15, safety/grounding 15 và pitch 10.
- Claim kỹ thuật chỉ dùng số liệu đã kiểm chứng: 44 field, 27 rule, 13 source register entry, 58 ca
  evaluation JSONL, 279 Python test đạt/2 skip, coverage 80,55% và 21 web test.
- Lộ trình pilot 12 tuần, KPI và mô hình B2G/B2B2G được ghi rõ là đề xuất/mục tiêu; không trình bày
  như kết quả thị trường đã đạt. README giữ nguyên cảnh báo demo, giới hạn Render Free, session
  in-memory, OCR candidate-only và browser E2E/video chưa hoàn tất.

### 2026-07-19 — Chặn false out-of-scope cho alias đã review

- Tái hiện production: “tôi muốn làm bản sao giấy khai sinh” bị phân loại mơ hồ; lượt xác nhận
  “tôi muốn cấp bản sao Giấy khai sinh” bị model phân loại `unsupported` dù mã `2.000635` nằm trong
  phạm vi.
- Core vẫn gọi structured extractor trước để giữ khả năng lấy field trong mixed turn. Chỉ khi model
  trả `ambiguous`/`unsupported` hoặc thiếu procedure code, tên/alias duy nhất từ procedure pack mới
  được dùng làm routing evidence xác định; không mở rộng ngoài ba pack đã review.
- Alias bắt đầu bằng “xin” chấp nhận hai cách diễn đạt hành động tương đương “cấp” và “làm”; nếu câu
  khớp nhiều thủ tục thì không tự chọn. Regression bao phủ đúng transcript lỗi và alias của cả ba
  thủ tục.
- Gate đạt: compileall, Ruff lint/format, mypy strict; `284 passed`, `2 skipped`, coverage `80.65%`.
- Sau khi rebase `origin/dev`, bản sửa là `7ea8ff5d`; cấu hình Render theo `dev` là `e341b55a`.
  Deploy `dep-d9dt5lvaqgkc73cvj7ug` đã `live` lúc `2026-07-18T19:26:50Z`.
- Public smoke Vercel → Render → OpenAI: health `200`, session `201`; hai lượt đúng transcript lỗi đều
  `200`, trả procedure `2.000635`, `next_action=ask_clarification`, không có error hoặc thông báo ngoài
  phạm vi. Thời gian lần lượt: health `0.239s`, session `1.298s`, turn 1 `3.464s`, turn 2 `2.590s`.

### 2026-07-19 — Khóa Git deployment Vercel theo nhánh dev

- Kiểm tra project `vneguide` cho thấy Git integration đang đặt Production Branch là `main`; vì vậy
  commit `dev` trước đây tạo Preview Deployment, còn mọi nhánh khác cũng được Vercel build theo mặc
  định.
- `demoweb/vercel.json` chỉ cho phép Git deployment khi branch là `dev`; wildcard chặn các nhánh còn
  lại để tránh tốn build và tạo preview ngoài quy trình release.
- Frontend gate đạt: ESLint, TypeScript, 21/21 unit test và Next production build 25 route. Build cần
  chạy ngoài sandbox vì Turbopack bind cổng nội bộ trong bước xử lý CSS.
- Production Branch là setting cấp project, không nằm trong `vercel.json`. Vercel REST API v9 từ chối
  trường `productionBranch` với `400`; browser tích hợp không khả dụng trong phiên này. Chủ project
  cần đổi một lần tại `Settings → Environments → Production → Branch Tracking` từ `main` sang `dev`.

### 2026-07-19 — Routing “đăng ký thường trú” vào xác nhận diện tích nhà ở

- Theo quyết định sản phẩm, cách nói đời thường “đăng ký thường trú” được route tới thủ tục được hỗ
  trợ `1.013314` về xác nhận Mẫu số 02/điều kiện diện tích nhà ở. Hệ thống vẫn không tuyên bố thực
  hiện thủ tục đăng ký thường trú `1.004222` và vẫn yêu cầu xác nhận dịch vụ trước khi điều hướng.
- Procedure pack nhà ở tăng version `2.0.1`, bổ sung hai alias đúng transcript và thông báo xác nhận
  nêu rõ ranh giới hỗ trợ. Evaluation cũ đánh dấu cụm này unsupported đã được đổi thành supported.
- Regression bao phủ hai lượt “đăng ký thường trú” → “xác nhận diện tích nhà ở để đăng ký thường
  trú”; cả hai giữ procedure `1.013314`, không quay lại menu ba thủ tục và không báo ngoài phạm vi.
- Gate đạt: compileall, Ruff lint/format, mypy 95 source; `287 passed`, `2 skipped`, coverage `80.60%`;
  checksum procedure pack khớp data package.

### 2026-07-19 — Chuẩn hóa phương ngữ, lỗi ASR và evidence

- Tạo `vneguide.language` với protected span cho họ tên, CCCD, ngày sinh, địa chỉ, mã thủ tục, số
  điện thoại và mã hồ sơ; deterministic glossary không được sửa bên trong các span này.
- Tầng model-assisted là tùy chọn qua `VNEGUIDE_LANGUAGE_MODEL_ASSISTED`; chỉ nhận text đã thay dữ
  liệu định danh bằng placeholder, dùng strict schema và không chứa bảng phương ngữ trong prompt.
- Structured extractor kiểm tra trên câu normalized rồi remap evidence về câu gốc trước khi tạo
  suggestion. Cụm mơ hồ “giấy nhà” dừng trước provider và trả ba lựa chọn, không suy luận procedure
  hay field. Cùng contract nhận `InputSource.TEXT` và `InputSource.SPEECH`.
- Workbook `data/DIALECT LEXICON_v2 (đã nhóm).xlsx` chỉ là input nghiên cứu cục bộ và đã được
  `.gitignore` bằng pattern `data/DIALECT LEXICON_v2*.xlsx`; không có workbook hoặc repo tham khảo
  ngoài scope nào trong Git index.
- Dataset mới có 15 mẫu tổng hợp Bắc/Trung/Nam, ASR và ambiguity. Reference classifier đạt raw
  `33.33%` và normalized `100%`; exact normalization `100%`, protected preservation `100%`, unsafe
  inference `0`. Đây là offline fixture metric, không phải claim người dùng thật.
- Gate đạt: compileall, Ruff lint/format, mypy 103 source; `304 passed`, `2 skipped`, coverage
  `80.59%`; release audit `17379/11569` file đạt. Frontend gate đạt ESLint, TypeScript, `21/21` test
  và Next production build 25 route; lần build sandbox đầu thất bại vì Turbopack không được bind
  cổng, chạy lại ngoài sandbox đạt.

### 2026-07-19 — Audit readiness theo sáu tiêu chí chấm và browser E2E

- Thêm ma trận [`judging-readiness.md`](judging-readiness.md) phân biệt độ phủ evidence nội bộ với
  điểm chấm/production readiness. Mức ước lượng nội bộ là 82/100 evidence coverage; repo chưa claim
  100/100 vì thiếu user validation, đơn vị pilot/LOI, DPIA/pen-test độc lập và video dự phòng.
- Đưa Playwright vào CI với đúng ba procedure route, hero đăng ký tạm trú 5/5, out-of-scope, manual
  edit, stale/retry, reset, session bị xóa, đổi procedure và typed timeout. Kết quả local:
  `15 passed, 1 skipped`; skip được khai báo là OCR upload UI chưa tồn tại, không được tính pass.
- E2E phát hiện và sửa ba lỗi sản phẩm: session cookie trỏ tới backend session đã mất; đổi thủ tục vẫn
  dùng session cũ; rule mức `info` về lệ phí bị UI coi như lỗi chặn. BFF nay tạo lại session theo
  procedure context, form giữ local edit/rebase đúng trạng thái và thông tin không chặn nằm trong
  vùng “Thông tin tham khảo”.
- Core không còn trả `ready_to_submit` khi vẫn còn missing field; regression khóa hành vi này.
- Gate 04:12 ICT đạt: Ruff lint/format, mypy 103 source; Pytest `305 passed, 2 skipped`, coverage
  `80.58%`; frontend `22/22` unit test, lint/type/build đạt; npm audit 0 vulnerability; Playwright
  `15 passed, 1 skipped`.
- Public smoke trên artifact đang deploy trước thay đổi này: `https://vneguide.vercel.app/` và
  `https://vneguide-api.onrender.com/health` đều HTTP 200; synthetic message phương ngữ đi qua
  Vercel → Render → OpenAI trả 200 và route đúng `1.004194`. Cần push/redeploy commit mới trước khi
  dùng public URL làm evidence cho các sửa session/readiness ở trên.

### 2026-07-19 — Mở rộng README và đưa phương ngữ vào tóm tắt

- Thêm phần tóm tắt giải pháp cho ban giám khảo: vấn đề, người dùng mục tiêu, ranh giới AI, đúng ba
  thủ tục, bằng chứng chạy được và giới hạn pilot/production.
- Đưa phương ngữ/ASR vào elevator pitch và kịch bản chấm nhanh với ví dụ tổng hợp “tui muốn làm tạm
  chú”; không biến fixture offline thành claim người dùng thật.
- Bổ sung pipeline protected spans → deterministic/model-assisted normalization → evidence remap →
  ambiguity clarification → suggestion. README nêu rõ họ tên/CCCD/ngày sinh/địa chỉ không được sửa,
  raw/normalized text không được log production và fact nghiệp vụ vẫn do source/rule quyết định.
- Chỉ thay tài liệu; `git diff --check` và release audit staged là gate bắt buộc trước merge/push.

### 2026-07-19 — Đồng bộ npm lock với GitHub runner

- Quality gate sau merge phát hiện `npm ci` trên npm 11.16.0 yêu cầu hai optional peer
  `@emnapi/core@1.11.2` và `@emnapi/runtime@1.11.2` chưa được khóa bởi npm 11.6.2 local.
- Regenerate `demoweb/package-lock.json` bằng đúng npm 11.16.0; clean install cùng phiên bản đạt,
  595 package và 0 vulnerability. Không đổi dependency trực tiếp hoặc application code.

### 2026-07-19 — OpenAI local wiring, phương ngữ và xác nhận dịch vụ

- Sửa composition root tự đọc `.env` bị Git ignore khi chạy local; process environment vẫn ghi đè,
  nên Render tiếp tục dùng secret/config managed. Trước thay đổi, chạy API mà không đặt
  `VNEGUIDE_LLM_ENV_FILE=.env` âm thầm rơi về provider `mock` dù key có trong file.
- Provider-only live smoke bằng dữ liệu tổng hợp đạt
  `MODEL_SMOKE_OK provider=openai model=gpt-4o-mini structured_output=true`. FastAPI local được khởi
  động không truyền env-file và ba lượt transcript tổng hợp đều trả HTTP 200 qua model thật.
- Glossary deterministic hiểu “Tui ưng mần tạm trú” thành “Tôi muốn đăng ký tạm trú”; dataset tăng
  lên 16 fixture. Reference classifier raw `31.25%`, normalized `100%`, exact normalization `100%`,
  protected preservation `100%`, unsafe inference `0`; đây vẫn là offline synthetic baseline.
- Core không hỏi field ngay ở lượt vừa xác định procedure. Nó trả `confirmation_message` đã review,
  giữ `suggestions=0`, rồi UI yêu cầu xác nhận trước khi mở trang chọn nơi nộp. Transcript “xin giấy
  tờ thường trú” → “đăng ký thường trú” chọn `1.013314`, trả xác nhận Mẫu số 02 và không hỏi họ tên.
- Gate đạt: Ruff lint/format, mypy strict; `309 passed`, `2 skipped`, coverage `80.61%`; frontend
  ESLint/TypeScript, `22/22` unit test và Next production build 25 route đạt. In-app Browser không có
  instance trong phiên; manual public click-through và GitHub browser E2E phải kiểm tra sau deploy.

### 2026-07-19 — LLM clarification fallback và chuyển dịch vụ giữa hội thoại

- Routing deterministic nay dùng cùng `LanguageNormalizer` trước các guard của core. Câu tổng hợp
  “tui ưng mần giấy khai sinh” được chuẩn hóa thành “tôi muốn làm giấy khai sinh” và hỏi đúng giữa
  bản sao được hỗ trợ với đăng ký khai sinh mới; không gọi model và không tự suy luận field.
- Trong lúc đang làm rõ giấy khai sinh, “thường trú” thoát trạng thái cũ để xác nhận thủ tục Mẫu 02;
  “đổi thành đăng kí tạm trú” tiếp tục chuyển sang `1.004194`. Chuyển explicit xóa suggestion/draft
  không còn phù hợp, tăng revision khi đã có procedure và trả confirmation trước điều hướng.
- Structured output cho phép một `clarification_question` tự nhiên khi procedure đã rõ nhưng không
  trích được field. Validator cấm kết hợp câu hỏi này với field/context signal; pending suggestion
  vẫn được ưu tiên xác nhận và rule/catalog tiếp tục là nguồn quyết định nghiệp vụ.
- Dataset phương ngữ tăng lên 17 fixture; reference classifier raw `29.41%`, normalized `100%`,
  exact normalization `100%`, protected preservation `100%`, unsafe inference `0` trên dữ liệu tổng
  hợp. Python gate đạt Ruff/format/mypy, `316 passed`, `2 skipped`, coverage `80.56%`. Frontend
  lint/typecheck và `22/22` unit test đạt; Next build 25 route đạt khi chạy ngoài sandbox (lần đầu
  bị sandbox chặn Turbopack bind cổng nội bộ, không phải lỗi application). Release audit đạt
  `17401/11591` index/text file, không phát hiện secret/PII/conflict marker.
- Chưa push/redeploy trong phiên này. Public URL vẫn chạy artifact trước thay đổi; cần deploy rồi
  smoke bằng session mới trước khi ghi nhận production evidence.
