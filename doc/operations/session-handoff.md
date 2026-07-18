# Bàn giao phiên release

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

1. Push `dev`, sau đó xác minh SHA remote trỏ tới commit tài liệu bàn giao mới nhất.
2. Thiết kế state/API nội bộ để persist, confirm và promote `context_signals`; không nhận cờ
   confirmation/trust trực tiếp từ browser client.
3. Triển khai `OcrCandidateSink` qua suggestion pending/revision guard và nối upload API/UI; không cho
   OCR ghi trực tiếp vào draft.
4. Rebuild Docker; smoke local/public URL và ghi lại image digest, model/version, timestamp.

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
