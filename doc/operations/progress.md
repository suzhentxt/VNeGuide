# Nhật ký tiến độ VNeGuide

## 2026-07-19 — Mem0 long-term memory opt-in trên nhánh refactor

- Clone shallow source chính thức `mem0ai/mem0` vào `D:\tmp\mem0-reference-20260719`, đối chiếu bản
  `mem0ai 2.0.12`, rồi tích hợp qua port nhỏ `add/search`; không vendor source Mem0 vào repository.
- State phiên hiện tại vẫn là nguồn sự thật. Mem0 chỉ được gọi trước GroundedResponder để lấy tối đa ba
  sở thích hỗ trợ và sau lượt để lưu preference. Memory không đi vào extractor, RuleEngine, draft,
  revision hoặc fact nghiệp vụ đã review.
- Chỉ ba preference được chuẩn hóa và allow-list: trả lời ngắn, diễn đạt đơn giản, hướng dẫn từng bước.
  `add` dùng `infer=False`; raw transcript, tên, địa chỉ, số định danh và field form không được gửi.
  Kết quả search ngoài allow-list cũng bị loại để chặn prompt injection/memory poisoning.
- API nhận optional `memory_scope_token` 32–128 ký tự base64url, băm SHA-256 thành anonymous `user_id`;
  cùng token nhớ qua session, còn `run_id` luôn là session ID riêng. Không token thì không gọi Mem0.
- Provider mặc định `disabled`; khi bật phải đặt cờ xác nhận external embedding và API key. Mem0
  telemetry bị ép `False`; Qdrant/history lưu local trong `.vneguide-memory/` đã git-ignore. Lỗi import,
  khởi tạo, add hoặc search đều fail closed/best-effort và không làm mất draft.
- Cài optional extra `memory` với `mem0ai>=2,<3`; khóa NumPy `<2.3` để giữ mypy Python 3.11 tương thích.
  SDK đã khởi tạo thật và smoke `add → search` qua Qdrant embedded bằng local deterministic embedder,
  không gọi mạng.
- Gate cuối: targeted `82 passed`; full Pytest `439 passed, 1 skipped`, coverage `81.49%`; compile,
  Ruff lint/format và Mypy strict (115 source file) pass. Full-index `release_audit.py` tiếp tục không
  hoàn tất trong timeout 60 giây trên Windows; không sửa hoặc hạ audit để che giới hạn.
- Giới hạn: `demoweb/**` vẫn ngoài scope nên BFF chưa phát/giữ stable memory token; web hiện vẫn dùng
  memory theo session. Chưa có UI consent/revoke hoặc scoped delete endpoint, vì vậy production phải
  giữ Mem0 disabled cho tới khi web owner bổ sung các control này và HTTPS.

## 2026-07-19 — Conversation Core & Guided Q&A trên nhánh refactor

- Nhánh `refactor-code` giữ `ConversationSession` làm nguồn state transition; `DeepAgentSession`
  tiếp tục chỉ re-compose FAQ đã grounded. FAQ trước form dùng `confirm_procedure` làm hành động chính
  và Deep Agent luôn giữ lại cầu nối xác nhận; provider/extractor failure không bị agent viết lại.
- Chuẩn hóa wire `next_action` thành đúng chín string: `confirm_procedure`, `choose_portal`,
  `fill_missing_field`, `review_suggestion`, `upload_document`, `fix_validation`,
  `ready_to_continue`, `needs_official_review`, `unsupported`. Wire shape không đổi; tên enum Python
  cũ chỉ là alias và không tạo thêm value.
- Core không hỏi field đã confirmed hoặc đang có suggestion pending. Field được hỏi lại đúng một lần
  sau lần không hiểu đầu tiên; sau lần thất bại thứ hai trả đúng hướng dẫn “Bạn có thể nhập trực tiếp
  vào biểu mẫu.” FAQ và route ngoài phạm vi không phát lại nguyên câu hỏi field.
- Một lượt có nhiều field giữ toàn bộ giá trị hợp lệ thành suggestion pending theo contract hiện hành;
  model không ghi thẳng draft. Correction rõ như “Không, địa chỉ đúng là…” mở lại field confirmed
  thành suggestion cần review, còn field `dirty` không bao giờ bị extractor ghi đè.
- Khi không còn missing field, core ngừng hỏi và chuyển `ready_to_continue`, hoặc chuyển
  `fix_validation`/`needs_official_review` theo RuleEngine. Lời đáp lúc thu thập được rút gọn theo mẫu
  ghi nhận + một “Bước tiếp theo”. Không thêm Redis; session, transcript, revision và memory compactor
  hiện có được giữ nguyên.
- Thêm `tests/integration/test_guided_conversation.py` và regression tests cho fixed action vocabulary,
  ba field trong một câu, correction, dirty guard, hai lần không hiểu, đủ dữ liệu, route ngoài phạm vi,
  model response lỗi giữ draft, lời đáp ngắn và golden flow không quá sáu lượt.
- Baseline trước sửa: targeted conversation/core `88 passed`. Gate cuối trên Python 3.12.7:
  targeted core/grounded/DeepAgent `99 passed`; Ruff lint/format pass; Mypy strict pass trên 111 source
  file; full Pytest `429 passed, 1 skipped`, coverage `81.49%`. Warning duy nhất là deprecation từ
  `fastapi.testclient`; live-model test vẫn skip chủ động. Full-index `release_audit.py` vẫn không
  hoàn tất trong timeout 184 giây trên Windows; clean-state scan xác nhận diff không có conflict,
  whitespace error, tracked `.env`/log/key hoặc file ngoài scope, và data checksum hợp lệ. Bounded
  staged audit trên đúng 13 file thay đổi pass cho secret, PII, conflict và artifact nhạy cảm.
- Giới hạn bàn giao: `demoweb/**` bị khóa ngoài scope và vẫn map các key cũ; web owner phải cập nhật
  presentation/quick-reply mapping sang chín key mới trước E2E trình duyệt. Không đọc/sửa `.env`,
  không gọi provider thật, không sửa OCR hoặc AI provider.

## 2026-07-19 — OCR kiểm tra nhẹ tài liệu ở bước 2 đăng ký tạm trú

- Thay OCR CT01 cũ bằng một luồng OCR duy nhất, tách worker khỏi API hội thoại. Luồng mới chỉ hỗ trợ
  `1.004194` và hai loại tài liệu: giấy tờ chứng minh chỗ ở hợp pháp khi dữ liệu không khai thác được,
  và ý kiến đồng ý của cha/mẹ/người giám hộ khi người đăng ký là người chưa thành niên.
- OCR dùng OpenAI Responses API với model cấu hình riêng (`VNEGUIDE_OCR_MODEL`, mặc định `gpt-5.5`),
  không dùng key/model chatbot. Kết quả chỉ gồm các tiêu chí cố định, độ tin cậy và trạng thái
  `pass`/`needs_review`/`fail`; không trả raw OCR, không tự điền draft và không đưa ra kết luận pháp lý.
- Bước 2 và chatbot dùng chung hai card tải tệp. `pass` cho phép tiếp tục; `needs_review` yêu cầu người
  dùng xác nhận đã tự kiểm tra; chỉ `fail` khi model nhận diện rõ sai loại tài liệu. Lỗi provider/timeout
  chuyển sang kiểm tra thủ công, không khóa hồ sơ vô thời hạn. Nộp hồ sơ trên demo vẫn chỉ là mô phỏng.
- Thêm BFF server-only, polling job, giới hạn MIME/kích thước, token worker không lộ ra trình duyệt;
  thêm OCR service vào Docker Compose. Chỉ dùng tài liệu tổng hợp/ẩn danh trong môi trường demo.
- Thêm hai ảnh PNG tổng hợp để thử trực tiếp tại `tests/fixtures/ocr/demo_documents/` và script tái tạo
  `tests/fixtures/ocr/generate_demo_documents.py`. Ảnh có watermark không có giá trị pháp lý và không
  chứa dữ liệu cá nhân thật.
- Gate đã đạt: Ruff lint/format, mypy strict (107 source), full pytest `408 passed, 1 skipped`, coverage
  `82.38%`; frontend `npm run check` đạt lint, typecheck, 35 test và Next production build (26 page/route).
  Data package audit đạt. Live smoke bằng hai PNG tổng hợp qua `gpt-5.5` đều `pass`: giấy chỗ ở có bốn
  tiêu chí ở mức `0.98–0.99` trong 7,218 ms; giấy đồng ý có bốn tiêu chí ở mức `0.98–0.99` trong
  3,781 ms. Full-index release audit chạm timeout 6 phút trên Windows; bounded audit tương đương trên
  37 file staged đạt (30 file text, không có secret/PII/conflict marker). Máy kiểm tra không có Docker CLI
  trong `PATH`, nên chưa chạy được `docker compose config`.
- Không sửa conversation core, rule engine, schema draft hay ground truth. Phần OCR CT01 trong các mục
  cũ phía dưới đã bị mục này thay thế và không còn được sử dụng.

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
