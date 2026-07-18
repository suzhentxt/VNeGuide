# Bàn giao phiên release

## 2026-07-19 — Mem0 long-term memory opt-in (`refactor-code`)

- `mem0ai 2.0.12` đã cài trong `.venv`; adapter, local Qdrant, telemetry opt-out, anonymous scope và
  fail-closed runtime đã hoàn tất. Không có source Mem0 được copy vào Git.
- Memory chỉ lưu ba normalized accessibility preferences với `infer=False`; không lưu transcript/PII
  hoặc field form và không ảnh hưởng draft/rule/business fact.
- Full gate đạt `439 passed, 1 skipped`, coverage `81.49%`, Ruff/Mypy pass; release audit full-index vẫn
  timeout sau 60 giây theo giới hạn Windows đã biết.
- Trạng thái chạy chính xác: SDK/local `add/search` đã được smoke; provider runtime mặc định vẫn
  `disabled`. Muốn gọi embedding thật cần explicit external-consent config, API key và stable
  `memory_scope_token`. Không đọc hoặc sửa `.env` trong phiên này.

Bước tiếp theo cụ thể cho web owner: đọc `doc/operations/mem0-memory.md`, thêm consent/revoke + stable
HttpOnly memory token trong BFF, thêm scoped deletion endpoint, chạy browser E2E hai session cùng token,
rồi mới bật Mem0 trong production. Không dùng IP, User-Agent, email, số điện thoại hoặc số định danh làm
memory identity.

## 2026-07-19 — Conversation Core & Guided Q&A (`refactor-code`)

- Core đã hoàn tất fixed `next_action` vocabulary và toàn bộ regression bắt buộc; full Python gate đạt
  `429 passed, 1 skipped`, coverage `81.49%`, Ruff và Mypy strict đều pass.
- Full-index `release_audit.py` bị timeout sau 184 giây theo giới hạn đã biết trên Windows; diff-scoped
  clean-state scan, bounded staged audit 13 file và data checksum pass. Không hạ gate hoặc sửa audit
  script để che timeout.
- Deep Agents không sở hữu draft: `ConversationSession` tiếp tục quyết định revision/suggestion/rule;
  adapter chỉ re-compose FAQ. FAQ có pending procedure vẫn giữ action/prompt `confirm_procedure`.
- Correction chỉ tạo suggestion reviewable, không auto-write draft. Manual `dirty` value luôn thắng.
  Sau hai lần không hiểu cùng field hoặc hai lỗi extractor liên tiếp, core hướng dẫn nhập trực tiếp.
- Memory hiện có được giữ: session + transcript + revision + best-effort compaction; không thêm Redis.
- File cross-owner tối thiểu đã đổi vì contract/refactor seam: `src/vneguide/domain/enums.py` khóa chín
  wire value; `src/vneguide/agent/session_adapter.py` giữ FAQ confirmation bridge và chặn agent rewrite
  fallback. Không sửa `demoweb/**`, OCR hoặc AI provider.

Bước tiếp theo cụ thể cho web owner: cập nhật mapping `demoweb` từ key cũ sang
`fill_missing_field`/`review_suggestion`/`fix_validation`/`ready_to_continue`/
`needs_official_review`/`unsupported`, rồi chạy browser E2E golden flow. Backend/core không nên thêm
compatibility key thứ mười vì vocabulary đã được khóa đúng chín giá trị.

## OCR tài liệu bước 2 — trạng thái 2026-07-19

- OCR CT01 cũ đã được thay hoàn toàn bởi kiểm tra nhẹ hai loại tài liệu của thủ tục tạm trú `1.004194`.
  Không còn mapper/smoke/candidate sink cũ; OCR không ghi dữ liệu vào draft và không trả nội dung nhận dạng.
- Cấu hình worker bằng `VNEGUIDE_OCR_ENABLED=true`, `VNEGUIDE_OCR_OPENAI_API_KEY`,
  `VNEGUIDE_OCR_MODEL=gpt-5.5` và `VNEGUIDE_OCR_WORKER_TOKEN`. Web dùng
  `VNEGUIDE_OCR_API_BASE_URL` cùng token ở môi trường server; xem `.env.example` và
  `demoweb/.env.local.example`.
- Chạy worker: `.venv\Scripts\python.exe -m vneguide.ocr.worker --host 127.0.0.1 --port 8001`.
  Chạy backend API: `.venv\Scripts\python.exe -m uvicorn vneguide.api.app:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir src`.
  Chạy frontend trong terminal khác: `cd demoweb; npm run dev`.
- Hai tệp thử: `tests/fixtures/ocr/demo_documents/legal_dwelling_demo.png` và
  `tests/fixtures/ocr/demo_documents/minor_consent_demo.png`. Đây chỉ là dữ liệu tổng hợp; không dùng
  giấy tờ hoặc PII thật khi endpoint chưa được triển khai trên đường truyền/hạ tầng được phê duyệt.
- Live smoke `gpt-5.5` đã cho cả hai ảnh mẫu `pass`, mọi tiêu chí ở mức `0.98–0.99`. Full Python đạt
  `408 passed, 1 skipped`, coverage `82.38%`; frontend đạt lint/typecheck/35 test/build. JSON/checksum và
  parse tĩnh Compose đạt. Máy hiện tại không có Docker CLI trong `PATH`, nên chưa xác minh runtime Compose.
- Bước tiếp theo cụ thể: cấu hình key/token cục bộ, mở trang đăng ký tạm trú, sang bước 2, tải lần lượt
  hai ảnh mẫu và xác nhận UI hiển thị tiêu chí/status; sau đó mới đánh giá thêm bộ tài liệu tổng hợp đa dạng.

## Nhánh thử nghiệm chat core

- `experiment/chat-core-v2` đang tách từ `dev@48f9c1f` trong worktree riêng.
- Core mới phân biệt small talk với yêu cầu dịch vụ ngoài phạm vi: greeting/cảm ơn không báo ngoài
  MVP và vẫn giữ field đang điền. Chỉ một dịch vụ/thủ tục rõ ràng ngoài ba pack mới trả out-of-scope.
- Guided mode nhận câu hướng dẫn linh hoạt/kể cả lỗi gõ, giải thích từng field từ metadata đã review.
  API trả `field_type`/`input_hint`; chat render lần lượt nút enum/boolean hoặc input text/date/number,
  ghi field thật qua revision guard và tự hiện câu hỏi tiếp theo sau mọi thao tác xác nhận.
- Đề xuất lưu ví chỉ bật sau event hoàn tất bước kê khai và chuyển bước. Gate mới nhất: Python
  `277 passed, 2 skipped`, coverage `80.55%`, mypy 94 source; frontend lint/typecheck, 21 test và
  build 25 route đạt.
  BFF smoke greeting → help → requester type → họ tên → typo-help đạt, revision `0 → 1 → 2`.
- Nhánh đã có redesign: chat xác nhận dịch vụ rồi mở trang chi tiết để chọn tỉnh và
  phường/xã/cơ quan tiếp nhận; chỉ sau đó người dùng bấm `Nộp hồ sơ`. Wizard nhận nơi tiếp nhận từ URL
  đã xác nhận và không lặp lại bước chọn địa điểm.
- Nút nhờ trợ giúp tự gửi prompt ẩn; core hỏi tuần tự theo field catalog. Enum/boolean có lựa chọn ngay
  trong chat và lựa chọn cập nhật draft thật, ghi transcript bằng nhãn thân thiện rồi hỏi field kế
  tiếp. Agent cũng chủ động đề xuất lưu/autofill trong ví session và vẫn yêu cầu xác nhận dữ liệu.
- Gate mới nhất: full Python `275 passed, 2 skipped`, coverage `80.40%`, Ruff, mypy 94 source;
  frontend lint/typecheck, 21 unit test và build 25 route đều đạt. BFF smoke xác nhận help → chọn
  fixed value → draft revision `1` và câu hỏi kế tiếp; detail/submission trả `200`, API health `ok`.
- In-app Browser không khả dụng. Bước tiếp theo cụ thể là chạy browser E2E/manual keyboard cho
  confirm-service → chọn authority → nộp hồ sơ → nhờ trợ giúp → chọn option, rồi rebuild Docker để
  kiểm loader catalog trong runner.
- Chatbot local hiện dùng OpenAI Responses API với `gpt-5.6-luna`; `.env` nằm ở worktree chính, bị
  Git ignore và phải được truyền rõ bằng `--env-file`. Provider/three-procedure/BFF smoke đều đạt;
  case tạm trú trả đúng `submission_channel=online` trong khoảng `1.415 s` qua web.
- Route-scoped pure guidance hiện bypass model bằng whole-message allowlist; mixed/form input vẫn qua
  structured extraction. Context guard chặn dùng nhầm fact của route cũ sau out-of-scope, ambiguous,
  procedure switch hoặc provider failure.
- Câu mơ hồ “làm/xin giấy khai sinh” giờ được hỏi rõ giữa cấp bản sao được hỗ trợ và đăng ký khai
  sinh mới ngoài phạm vi, kể cả khi route tạm trú đang hoạt động. UI hiển thị “Hồ sơ chưa đủ thông
  tin” thay cho `ready_to_submit` khi còn missing field; backend rule status được giữ nguyên vì
  completeness là contract tách biệt.
- Chat widget và workspace provider được mount ở root layout: trang chủ và mọi route đều hiện đúng
  một nút trợ lý, trong khi form tạm trú vẫn chia sẻ cùng workspace với chat.
- Session nhớ câu hỏi làm rõ “bản sao hay đăng ký mới”, hiểu câu trả lời rút gọn và typo “bảo sao”.
  UI có nút trả lời nhanh, chữ lớn hơn và không lộ tên field kỹ thuật. Quan hệ “cho con tôi” được ghi
  nhớ nhưng chưa tự ánh xạ sang `authorized_person`; quyết định dữ liệu cần review nằm ở `OD-007`.
- Guided reply layer đạt full Python `272 passed, 2 skipped`, và A/B `12/12` fact/topic/source;
  dùng `VNEGUIDE_CHAT_CORE_VARIANT=baseline` để rollback tức thì.
- Provider/BFF smoke mới nhất dùng OpenAI/gpt-5.6-luna và xác nhận cả guidance lẫn structured field
  suggestion hoạt động bằng dữ liệu tổng hợp. Local demo đang chạy tại `http://127.0.0.1:13000`, API
  tại `http://127.0.0.1:18000`; process phải có network egress tới OpenAI API.
- Npm gate đạt `0 vulnerabilities`, 13 unit tests và build 25 route. Bước tiếp theo là review nhánh,
  sau đó chỉ cân nhắc merge khi A/B và public deployment được chấp thuận; không thay coverage
  threshold, dataset checksum hoặc source data.

## Trạng thái Git

- Nhánh hiện tại: local `dev`, nền `origin/dev@185279a3`.
- Rules/AI đã merge bằng `43ed537` từ `origin/agent/rules-ai-eval@4a7aac3`; OCR đã merge bằng
  `299cc69` từ `origin/agent/ocr-hero@2a155a0`.
- Chatbot toàn cục từ `agent/senior-conversation@22810e5` đã được tích hợp vào local `dev`;
  nhánh này chưa có phần NLG/xác nhận thủ tục cho người cao tuổi.
- Phạm vi runtime vẫn khóa đúng ba mã trong `data/README.md`: `2.000635`, `1.013314` và `1.004194`.
- BFF được nối sang contract backend bằng
  `PATCH /v1/chat/sessions/{session_id}/draft/fields/{field_id}`.
- Full Python/npm gate đã đạt trên merge result hiện tại.
- `.DS_Store`, `procedures.csv` và `view_parquet.py` không thuộc release và không được stage.

## Thay đổi từ Người 2

- Session context seed procedure ngay khi tạo phiên; create/GET trả top-level draft snapshot.
- Draft response có `values`, `revision`, `confirmed_fields`, `dirty_fields`, `pack_version`.
- Manual field edit có optimistic revision, validation theo catalog/rule và response lỗi typed.
- Accept/Edit/Reject đều kiểm tra revision; manual edit vô hiệu hóa pending suggestion cùng field.
- Extractor dùng compact turn context, giữ procedure qua small talk nhưng không gửi transcript/draft PII.
- Core tránh hỏi lặp bằng `asked_question_ids` và chuyển sang manual input khi câu trả lời tiếp tục mơ hồ.
- Session store khóa xuyên suốt mutation để tránh race với delete/expiry.

## Rules, AI và evaluation đang tích hợp

- Giữ public contract hiện hành `ExtractionTurnContext(active_procedure_code, expected_field_id)` để
  core/API/test cùng dùng một kiểu context. Context chỉ hỗ trợ hiểu câu trả lời ngắn; evidence vẫn phải
  xuất hiện trong tin nhắn người dùng hiện tại.
- Structured extraction chỉ nhận ba procedure code đã review và mở rộng output bằng
  `context_signals`, evidence và origin tách biệt khỏi form field.
- Text extractor chỉ tạo candidate cho signal có origin `intent_extraction` hoặc
  `user_declaration`; document/derived signal phải đến từ adapter tin cậy. Rule engine kiểm type,
  origin và promotion trước khi cho signal tham gia deterministic rule.
- Evaluation bổ sung 21 case tổng hợp cho ba thủ tục, hội thoại nhiều lượt/câu ngắn, ngoài phạm vi,
  ambiguous và cách diễn đạt ba miền. Fixture có checksum và live evaluator opt-in không ghi message,
  evidence, raw output hoặc secret vào report.
- Giới hạn cần giữ rõ: core hiện chưa persist candidate/evidence, chưa ghi nhận xác nhận của người dùng
  và chưa promote trusted-adapter `context_signals`. Vì vậy phần signal mới chưa chạy end-to-end trên
  web dù contract extractor/rules đã tồn tại.

## OCR CT01 đang tích hợp

- Adapter/worker chỉ hỗ trợ CT01 cho thủ tục `1.004194` và chỉ trả candidate
  `field_id`/`suggested_value`/`confidence`/`evidence` với `source=USER_UPLOAD`.
- OCR không tự ghi vào draft. `OcrCandidateSink` mới là port contract; core/API/UI chưa có sink để
  đưa candidate vào suggestion `pending`, nên chưa có OCR end-to-end trên web.
- Fixture chỉ dùng dữ liệu tổng hợp. Live smoke ba lượt trên CT01 tổng hợp đạt field recall `0.75`
  (9/12), chưa đủ để tuyên bố accuracy production và vẫn phải giữ fallback nhập tay.
- `VNEGUIDE_OCR_*` được đọc từ process environment; `--env-file` hiện chỉ nạp cấu hình LLM. Không
  gửi hồ sơ hoặc PII thật qua gateway HTTP chưa có TLS.
- Release Captain đã thêm extra `ocr` gồm Pillow/pypdfium2 và cài `.[api,dev,ocr]` trong CI để
  image/PDF preprocess tests thực sự chạy thay vì bị skip.
- Upload thiếu `Content-Length` hiện có thể bị buffer toàn bộ bởi `request.body()` trước khi kiểm cap
  8 MiB. Worker chỉ được bind localhost cho tới khi có đọc stream giới hạn và hardening phù hợp.

## Gate trên merge result Rules/AI + OCR

- Compileall pass; Ruff lint/format pass trên 90 Python file; Mypy strict pass trên 88 source file.
- Pytest `216 passed, 1 skipped`, coverage `80.44%`; skip duy nhất là live-provider test opt-in.
- OCR targeted `33 passed`; cả ảnh và PDF preprocess đều thực sự chạy với Pillow/pypdfium2.
- `npm ci`/audit pass với 0 vulnerability; lint, typecheck, 9 reducer test và Next production build
  25 route pass.
- Build chỉ generate đúng ba procedure slug. Gate không gọi model ngoài và không gửi PII.
- Staged release audit pass: 363 index file, 217 text file; không secret, PII ngoài fixture hoặc
  conflict marker.

## Gate sau khi tích hợp chatbot toàn cục

- Compileall, Ruff lint/format và Mypy strict pass trên merge result.
- Pytest `216 passed, 1 skipped`, coverage `80.42%`; skip duy nhất là live-model opt-in.
- Frontend lint/typecheck, `27/27` Node test và Next production build 25 route pass.
- Full-index `release_audit.py` không hoàn tất trong thời gian giới hạn trên Windows;
  staged-diff audit thay thế pass cho conflict marker, secret, `.env` và chuỗi 12 chữ số mới.

## Việc cần làm tiếp

1. Review và tích hợp `experiment/chat-core-v2`; không đưa `.env` hoặc artifact local vào commit.
2. Tách cấu hình OCR Qwen khỏi provider/model chatbot để hai process có thể chạy đồng thời mà không
   phải đổi `.env` qua lại.
3. Thiết kế state/API nội bộ để persist, confirm và promote `context_signals`; không nhận cờ
   confirmation/trust trực tiếp từ browser client.
4. Triển khai `OcrCandidateSink` qua suggestion pending/revision guard và nối upload API/UI; không cho
   OCR ghi trực tiếp vào draft.
5. Rebuild Docker; smoke local/public URL và ghi lại image digest, model/version, timestamp.

## Blocker còn lại

1. Context signal mới chưa được core persist/confirm/promote nên chưa có runtime E2E.
2. OCR chưa có API/UI sink; live recall hiện chỉ `0.75` và chunked upload chưa có streaming cap.
3. Container/public preview hiện dùng image trước merge mới và phải rebuild.
4. Chưa có durable cloud target hoặc video dự phòng được hai người review.
5. In-memory session store chỉ phù hợp một worker; cần shared store trước khi scale.

## Lệnh gate chuẩn

```bash
python -m pip install -e ".[api,dev,ocr]"
python -m compileall -q src tests
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

## Bàn giao chatbot toàn cục

- Root layout mount đúng một `ProcedureWorkspaceProvider` và một `ChatWidget`; launcher có mặt trên mọi
  trang, gồm trang chủ, danh mục và ba procedure.
- Context/revision guard chặn session cũ, suggestion cũ và field response cũ làm thay đổi form khác
  procedure. Form edits được serialize; session creation được single-flight trong một tab.
- General-session và procedure-session được tách scope. Khi chuyển scope hoặc draft không khớp, UI yêu
  cầu session mới, giữ form local rồi tuần tự đồng bộ field trước khi mở lại chat.
- Field chưa sync được replay khi quay lại procedure; retry message dừng nếu replay chỉ thành công
  một phần. Accept/Edit response cũ không ghi đè manual edit phát sinh trong lúc request chờ.
- Gate cuối: `cd demoweb && npm run check` pass với 27/27 test và build 25 route.
- HTTP smoke trên port tạm `3117`: năm route mục tiêu đều `200`, mỗi route có đúng một launcher; server
  tạm đã được dừng sau smoke.
- Việc tiếp theo: chạy browser E2E với backend/model thật cho open/close, general → procedure, A → B,
  manual field blur nhanh, rebind và mobile focus. Multi-tab session identity chưa thuộc phạm vi MVP này.

## Bàn giao hội thoại senior trên `agent/senior-conversation-v2`

- Base là local `dev@7fac2858`. Nhánh này thêm xác nhận thủ tục cho general chat, lời thoại dùng catalog
  label, phục hồi thinking prefix, soft-drop candidate evidence lỗi và NLG acknowledgement có allowlist.
- `pending_procedure_code` chỉ là state server nội bộ. API/web nhận `next_action=confirm_procedure`,
  `procedure=null`, draft revision `0`; assistant message luôn chứa cùng nội dung với top-level `reply`.
- Route-scoped session tiếp tục active ngay. General session chỉ active sau `Đúng`; `Không phải` xóa pending.
  Field trích ở lượt intent đầu tiên được cố ý không giữ trước khi xác nhận và sẽ được hỏi lại sau đó.
- Nếu chính lượt xác nhận còn nêu dữ liệu, ví dụ `Đúng, tôi nộp trực tuyến`, field của lượt đó được giữ
  dưới dạng suggestion pending; core vẫn không tự ghi vào draft hoặc tăng revision.
- Guard phủ nhận pending xử lý cả câu dài: phủ nhận không nêu thủ tục mới sẽ xóa pending; nếu extractor
  nhận diện một thủ tục khác đã review thì chỉ thay pending sang mã mới. Câu hỏi lại như `Đúng không ạ`
  không bị hiểu là phủ nhận hoặc xác nhận.
- Reply sau Accept/Reject/Edit và manual form edit được append vào assistant message mà không tăng
  `turn_number`; transcript web không còn mất câu hỏi vừa được đánh dấu trong `asked_question_ids`.
- Enum question liệt kê lựa chọn tiếng Việt theo đúng thứ tự value trong catalog. Chín boolean question
  có template riêng với quy ước `Có=True`; tên thủ tục dài `1.013314` dùng short label tập trung.
- Provider schema là catalog-derived compact schema dưới 5 KB; server validator vẫn là nguồn quyết định
  type, bound, procedure ownership và evidence. Không đưa validation nghiệp vụ sang model.
- LiteLLM extraction khóa `temperature=0` và có direct routing examples cho tạm trú/nhà ở. Live probe
  `Tôi muốn đăng ký tạm trú` đạt 5/5; flow `Đúng, tôi nộp trực tuyến` tạo đúng pending suggestion
  `submission_channel`. Core gửi `confirmation_required=true` trong bounded context và chỉ activate
  procedure sau khi outcome xác nhận cùng mã; câu phủ nhận/do dự không bị activate sớm.
- Gate cuối: compile/Ruff/Mypy pass; `252 passed, 1 skipped`, coverage `80.62%`; frontend `27/27` test và
  build 25 route pass. `zai-org/GLM-5.2` đạt provider smoke, route tạm trú 5/5, mixed-confirm và
  reject/switch regression trên dữ liệu giả.
- Full-index `release_audit.py` vẫn không hoàn tất trong thời gian hợp lý trên Windows và đã được dừng;
  bounded diff scan không thấy conflict marker, secret, tracked `.env` hoặc định danh 12 chữ số mới.
- Bước tiếp theo: merge nhánh này vào `dev`, sau đó chạy browser E2E cho nút mở chat, nhập intent, trả lời
  `Đúng`/`Không phải` và xác minh form route vẫn đồng bộ. Có thể thêm CTA `Đúng`/`Không phải` sau, nhưng
  text input hiện đã hoạt động và không cần thay API contract.
- Không chạy transcript hoặc hồ sơ thật qua gateway HTTP; chỉ dùng dữ liệu tổng hợp cho tới khi có HTTPS.
- Python `3.11.9` user-level đã được khôi phục đúng đường dẫn trong `.venv/pyvenv.cfg`; không cần tạo lại
  `.venv` trên máy này.
- Xác minh trên được thực hiện ngoài sandbox. Sandbox mặc định không được đọc executable Python trong
  user profile nên có thể báo nhầm `.venv` hỏng; terminal người dùng vẫn chạy `.venv` bình thường.

## Bàn giao grounded Q&A trên `agent/senior-conversation-v2`

- Base vẫn là `6d0194ac`; worktree chưa commit chứa Q&A deterministic cho đúng ba procedure, pack
  `2.1.0`, UI status mapper và synthetic evaluation. Không push.
- `informational` không được mang form field mutation. Core trả lời bằng source đã duyệt, đặt pending
  trước form, giữ nguyên state form khi đang active và chỉ cho tham khảo khi hỏi procedure khác.
- `recent_information_procedure_code`/`recent_information_topics` chỉ là conversation memory, không
  thuộc draft và không tăng revision. Reset/`Không phải` xóa pending Q&A memory.
- Gate đã có bằng chứng: renderer+conversation 91 test trước regression cuối, Chat API 5, form-sync
  15, Mypy 90 source file trước regression cuối, Ruff lint/format 93 file và frontend `npm run check`
  đạt 36 test + production build 25 route. Fixture Q&A 15 dòng parse/checksum đúng.
- Chưa được coi là hoàn tất cho tới khi chạy lại full Python gate sau regression/evaluation cuối,
  chạy live Q&A bằng GLM-5.2 với dữ liệu giả và tạo một commit follow-up. Next production build cuối
  đã đạt. Gateway là HTTP nên tuyệt đối không gửi PII/transcript thật.
- Blocker hiện tại là hạn mức chạy ngoài sandbox của phiên coding agent; không phải cần tạo lại `.venv`.

Lệnh tiếp theo cụ thể:

```powershell
.\.venv\Scripts\Activate.ps1
python -m ruff check src tests deployment
python -m ruff format --check src tests deployment
python -m mypy
python -m pytest --cov=vneguide --cov-report=term-missing
python -m vneguide.ai.smoke --env-file .env --confirm-live
Set-Location demoweb
npm.cmd run check
```

Sau gate, chạy một probe synthetic qua `StructuredExtractor` cho các câu “Đăng ký tạm trú cần giấy
gì và phí bao nhiêu?” và “Theo danh sách tức là gì?”, ghi model/version/timestamp nhưng không ghi raw
prompt, evidence hoặc secret. Chỉ khi pass mới commit; không push nếu chưa có yêu cầu mới.

## Bàn giao Vercel production 2026-07-18

- Project đã sẵn sàng tại `trinhs-projects-e6e09c31/vneguide`; Root Directory là `demoweb`, framework
  Next.js và production env `VNEGUIDE_API_BASE_URL` đã được cấu hình.
- Production deployment `HGBB73U7JGdaQay1V8DcU8tvNKGc` đã `READY` tại
  `https://vneguide.vercel.app/`; SSO Protection đã tắt theo xác nhận của chủ project.

Không dùng `vercel redeploy` với deployment `dpl_3McXuEUTANRxvYnBLGnQ1n1LXa8U`: source archive đó
thiếu toàn bộ `demoweb/src` do ignore pattern cũ. Fresh deploy từ commit mới là bắt buộc.

- Smoke công khai đạt: trang chủ/ba procedure `200`, backend health `200`, tạo chat session qua BFF
  `201`; portal-options thiếu query trả `400` đúng thiết kế. Preview vẫn phụ thuộc FastAPI
  `127.0.0.1:18000` cùng tunnel ngrok; tunnel hoặc máy local dừng thì chatbot trên Vercel cũng dừng.
- Bằng chứng sau smoke: ngrok `ERR_NGROK_3200` khi process local kết thúc; BFF hiển thị
  `invalid_backend_response` vì endpoint offline trả HTML thay vì JSON. Phải deploy FastAPI lên host
  bền vững hoặc giữ đồng thời process API/ngrok trên máy demo.

## Bàn giao Render API 2026-07-18

- `render.yaml` đã sẵn sàng cho Python service `vneguide-api` trên Free plan/Singapore, dùng
  constraint lock hiện hành, một API process và health check `/health`.
- Targeted API gate đạt `29 passed`; image local build thành công và container health `200`.
- Service `srv-d9dqule1a83c73b989s0`, deploy `dep-d9dr0nf41pts73docp7g` đang `live` tại
  `https://vneguide-api.onrender.com`; direct model smoke đạt health `200`, session `201`, message
  `200`. Secret chỉ tồn tại trong Render Environment.
- Vercel production env đã trỏ sang Render; deployment `8tf1DLcUwfYtJFw18UyALrUn4zEW` `READY` và
  alias `https://vneguide.vercel.app` giữ nguyên. E2E create `201`/1.178 giây, message
  `200`/5.039 giây.
- Render Free sleep sau 15 phút idle và restart làm mất session in-memory; nâng plan hoặc thêm shared
  store trước demo tải cao. Lần gọi đầu sau sleep có thể cần retry do cold start.

## Bàn giao CI release audit 2026-07-19

- Check `python` của PR #5 từng fail vì regex PII cũ nhận UUID, SHA-256, mã thủ tục dot-delimited và
  placeholder 12 chữ số trong corpus từ `dev` là CCCD.
- Bản sửa không allowlist `data/procedures`; scanner tiếp tục quét toàn bộ merge result và regression
  test vẫn bắt số định danh 12 chữ số đứng độc lập.
- Xác minh local: Ruff/format/mypy đạt; pytest `279 passed`, `2 skipped`, coverage `80.55%`; branch
  audit `385/239` và merge-result audit `17379/11569` đều đạt.
- Next tracing root làm Docker artifact nằm tại `/app/app/server.js`; `web.Dockerfile` đã đồng bộ
  entrypoint và asset path theo artifact này. Compose smoke trên cổng riêng xác nhận ba service
  healthy, API `3/3` và web `3/3` trả `200`; project test đã được `down --volumes`.

## Bàn giao README cho ban giám khảo 2026-07-19

- Bắt đầu review tại phần “Dành cho ban giám khảo — bản đồ chấm 100 điểm” trong `README.md`; mỗi tiêu
  chí có code/evidence hoặc nhãn mục tiêu pilot rõ ràng.
- Không đổi số liệu pilot thành claim thực tế khi chưa có baseline người dùng thật. Các blocker vẫn
  phải công khai: session chưa durable, preview không có SLA, OCR chưa nối upload UI, browser E2E và
  video dự phòng chưa hoàn tất.
- Bước trình bày tiếp theo: chạy preflight public URL, record video theo
  `doc/operations/demo-and-pitch.md` và để hai người review offline trước giờ chấm.

## Bàn giao lỗi routing alias 2026-07-19

- Local `dev` có fallback routing từ procedure pack: nếu model trả sai `ambiguous`/`unsupported` cho
  một tên hoặc alias duy nhất đã review, core chọn đúng procedure thay vì báo ngoài phạm vi.
- Transcript “làm bản sao giấy khai sinh” → “cấp bản sao Giấy khai sinh” được khóa bằng regression;
  alias của `1.004194` và `1.013314` cũng được kiểm tra. Câu “làm giấy khai sinh” không có từ “bản
  sao/trích lục” vẫn đi qua clarification an toàn.
- Full Python gate đạt `284 passed`, `2 skipped`, coverage `80.65%`; Ruff, format và mypy đạt.
- `origin/dev` đã nhận bản sửa `7ea8ff5d` và cấu hình Render `e341b55a`. Service hiện theo branch
  `dev`; deploy `dep-d9dt5lvaqgkc73cvj7ug` đã `live` và public smoke đúng transcript đạt `200/200`,
  cùng procedure `2.000635`, không còn false out-of-scope.
- Bước tiếp theo: chạy browser manual bằng một session mới sau cold start và record video dự phòng;
  không dùng session cũ vì Render restart làm mất memory.

## Bàn giao khóa nhánh Vercel 2026-07-19

- `demoweb/vercel.json` đã khai báo chỉ `dev` được kích hoạt Git deployment; các branch khác khớp
  wildcard `false` và không còn tạo Preview Deployment sau khi nhận commit cấu hình này.
- Setting cloud vẫn đang là `link.productionBranch=main`. Bước tiếp theo bắt buộc: mở project
  `vneguide` trên Vercel, vào `Settings → Environments → Production → Branch Tracking`, nhập `dev`
  và Save. Sau đó push một commit mới vào `dev` để xác minh deployment có target `production` và
  alias `vneguide.vercel.app` được cập nhật.

## Bàn giao routing thường trú 2026-07-19

- `data/catalog/procedure_packs/housing_condition_confirmation.json` version `2.0.1` coi “đăng ký
  thường trú” là routing shorthand của `1.013314`; đây không phải việc mở phạm vi sang thủ tục
  đăng ký thường trú `1.004222`.
- Regression exact transcript nằm trong `tests/unit/test_conversation.py`; full Python gate đạt
  `287 passed`, `2 skipped`, coverage `80.60%`.
- Bước tiếp theo sau khi push/redeploy: tạo session production mới và smoke hai lượt đúng transcript;
  Render restart làm mất session in-memory nên không tái sử dụng cookie cũ.

## Bàn giao chuẩn hóa phương ngữ 2026-07-19

- Nhánh `feature/vietnamese-dialect-normalization` có module deterministic/model-assisted, protected
  spans, evidence mapping và 15 fixture tổng hợp. Workbook nguồn được ignore và tuyệt đối không stage.
- Tầng deterministic mặc định luôn chạy. Model-assisted mặc định tắt; bật bằng
  `VNEGUIDE_LANGUAGE_MODEL_ASSISTED=1` khi chấp nhận thêm một model call cho câu còn dấu hiệu chưa
  chuẩn. Production không được log `NormalizationResult` vì chứa raw/normalized text trong memory.
- Full gate đạt `304 passed`, `2 skipped`, coverage `80.59%`; frontend `npm run check` và release
  audit đều đạt. Bước tiếp theo sau merge là smoke một session mới với các câu “tui muốn làm tạm
  chú”, “hộ khẩu photo có được hông” và “Tôi cần giấy nhà”; chỉ bật model-assisted sau khi đo latency,
  cost và tỉ lệ ambiguity trên traffic tổng hợp.

## Bàn giao audit tiêu chí và browser E2E 2026-07-19

- Browser suite nằm ở `demoweb/e2e/`, chạy production build + FastAPI mock bằng
  `cd demoweb && npm run test:e2e`. Baseline hiện tại: `15 passed, 1 skipped`; OCR test cố ý `fixme`
  cho tới khi có upload API/UI thật.
- BFF field route tự tạo lại session khi backend trả 404/410 hoặc procedure cookie không khớp route;
  header `X-VNeGuide-Session-Recreated: 1` khiến workspace rebase revision nhưng giữ các local field
  chưa đồng bộ.
- Form tạm trú chỉ chặn severity `error`/`needs_review`; severity `info` được render trong “Thông tin
  tham khảo”. Draft còn missing field không được core báo `ready_to_submit`.
- Ma trận readiness ở `doc/operations/judging-readiness.md`; không đổi 82/100 evidence coverage thành
  claim điểm thi. Bốn bằng chứng ngoài code còn thiếu: usability test người dùng mục tiêu, sponsor/LOI
  pilot, DPIA/security assessment độc lập và video backup được hai người review.
- Bước tiếp theo cụ thể: commit/push thay đổi này lên `dev`, chờ CI xanh, xác minh Vercel/Render deploy
  đúng SHA mới rồi append deployment ID/timestamp vào `release-evidence.md`. Sau đó record video; không
  đưa video, PII hoặc secret vào Git.

## Bàn giao README chi tiết 2026-07-19

- Phần đầu README hiện có executive summary và value flow, trong đó phương ngữ/ASR là năng lực sản
  phẩm nhìn thấy ngay thay vì chỉ nằm sâu trong mục kiến trúc.
- Mục AI-Native có pipeline và ví dụ synthetic cho normalization, protected spans, ambiguity và raw
  evidence mapping. Giữ nguyên nhãn offline baseline, không trình bày `100%` fixture như accuracy
  production.
- Sau khi merge/push `dev`, chờ GitHub Actions E2E và Vercel/Render deploy đúng SHA mới; public smoke
  bằng session mới rồi mới cập nhật evidence deployment.
- GitHub runner hiện dùng npm 11.16.0; khi đổi Playwright/Next dependency phải regenerate và kiểm
  `npm ci` bằng cùng major/minor để tránh optional peer bị thiếu trong lockfile.

## Bàn giao OpenAI + routing phương ngữ 2026-07-19

- Local API giờ tự đọc `.env` nếu file tồn tại; không cần nhớ đặt
  `VNEGUIDE_LLM_ENV_FILE=.env`. Environment của Render vẫn có ưu tiên cao hơn và `.env` không được
  stage/commit.
- Live provider smoke và FastAPI transcript đã chứng minh key gọi được OpenAI Responses API với
  `gpt-4o-mini`. Grounded FAQ/small talk có thể bypass model theo thiết kế; intent và structured field
  extraction vẫn gọi provider.
- “Tui ưng mần tạm trú” route tới `1.004194`. “tôi muốn xin giấy tờ thường trú” được hỏi làm rõ;
  lượt tiếp “tôi muốn đăng ký thường trú” route tới `1.013314` và chỉ trả xác nhận Mẫu số 02, chưa tạo
  suggestion hoặc hỏi field.
- Full Python gate đạt `309 passed`, `2 skipped`, coverage `80.61%`; npm gate đạt 22 test và build 25
  route. Bước tiếp theo sau push là chờ CI xanh, chờ Render deploy đúng SHA rồi public smoke bằng
  session mới; in-app Browser không khả dụng trong phiên này.

## Bàn giao STT phương án 1 — 2026-07-19

- App-side integration đã hoàn thành trên nhánh `agent/stt-integration`: browser → Next BFF
  `/api/stt/transcribe` → remote OpenAI-compatible Qwen3-ASR-1.7B → draft chat. Không auto-send.
- Base stack giữ STT disabled và health độc lập. Overlay kích hoạt là
  `deployment/docker-compose.stt-remote.yml`; trên VPS hiện tại luôn ghép thêm
  `deployment/docker-compose.vps.yml` và `--env-file /opt/vneguide/shared/vneguide.env` để không đụng
  translator hoặc đổi các port `9000/13000/18000`.
- VPS hiện tại không có GPU và data mount hiện chỉ khoảng 448 KiB; không được cố chạy model 1.7B tại
  đó. Việc kích hoạt còn thiếu hai input vận hành: URL/key của GPU endpoint có hard duration/quota và
  một domain HTTPS hợp lệ (hoặc chỉ test microphone qua SSH tunnel/localhost).
- Gate app-side: Python targeted 7/7, frontend 44/44 + lint/typecheck/build, BFF smoke success/415/400;
  bounded staged audit 18 file đạt sau khi full-index audit timeout 120 giây. Browser interaction chưa
  chạy do không có browser instance trong phiên này.
- App-side release đã deploy tại `/opt/vneguide/releases/48c7582e-stt1`; health đạt, STT status trả
  `enabled=false`, chat create/get/delete đạt `201/200/204`, translator/Caddy không bị recreate. Web
  image mới là `sha256:52c3598c24c97b76a2f6e1ebc7f88ca33c72459310e92600c6a36290717065bd`.
- Rollback: cấu hình gateway cũ ở
  `/opt/vneguide/shared/nginx-http.conf.before-stt-20260719`, web image cũ có tag
  `vneguide-web:rollback-df97f0321f25`, release cũ là `/opt/vneguide/releases/df97f0321f25`.
- Bước tiếp theo cụ thể: người vận hành cung cấp GPU URL/key và HTTPS domain; xác minh GPU ingress tự
  probe duration/quota, bật overlay STT cùng overlay VPS, chạy audio tiếng Việt tổng hợp, kiểm tra
  transcript chỉ nằm trong textarea và thử actual-duration trên 60 giây.
