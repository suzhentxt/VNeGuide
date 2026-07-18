# Bàn giao phiên release

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

- Nhánh hiện tại: local `dev`, nền `origin/dev@f90b5e2`.
- Rules/AI đã merge bằng `43ed537` từ `origin/agent/rules-ai-eval@4a7aac3`; OCR đã merge bằng
  `299cc69` từ `origin/agent/ocr-hero@2a155a0`. Đích push là `origin/dev`.
- Phạm vi runtime vẫn khóa đúng ba mã trong `data/README.md`: `2.000635`, `1.013314` và `1.004194`.
- BFF được nối sang contract backend bằng
  `PATCH /v1/chat/sessions/{session_id}/draft/fields/{field_id}`.
- Full Python/npm gate và staged release audit đã đạt trên cây hợp nhất Rules/AI + OCR.
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
