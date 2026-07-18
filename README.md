# VNeGuide — Trợ lý AI hồ sơ dịch vụ công

VNeGuide là trợ lý AI giúp người dân **chuẩn bị** và **kiểm tra trước** hồ sơ thủ tục hành chính
(TTHC) — đúng ngay từ lần nộp đầu tiên, giảm phải đi lại nhiều lần. Dự án tham gia cuộc thi
**Vietnam AI Innovation 2026**. Bài dự thi nằm tại [`dany-dichvucong-ai/`](dany-dichvucong-ai/);
repo này (`VAIC_UET`) là bản triển khai thực tế (MVP) đang chạy.

VNeGuide chỉ hỗ trợ **hướng dẫn, kiểm tra và chuẩn bị hồ sơ**; kết quả không phải quyết định hành
chính. Phạm vi runtime hiện hành được khóa bởi [`data/README.md`](data/README.md).

> Ghi chú trung thực: MVP đã xây dựng (BUILT) hỗ trợ **3 thủ tục** và dùng provider abstraction
> `mock`/`openai`/`litellm`. Kế hoạch dự thi (`dany-dichvucong-ai/`) mở rộng **5 thủ tục** và dùng
> **FPT AI Factory** — phần này mang tính lộ trình (PLANNED), được đánh dấu rõ trong từng mục dưới.

---

## Đánh giá theo tiêu chí VAIC 2026 (tổng 100 điểm)

Mỗi mục dưới liệt kê bằng chứng cụ thể kèm nguồn file và nhãn trạng thái:
**[BUILT]** đã triển khai · **[PLANNED]** kế hoạch/chưa xây · **[TBD]** chưa rõ/cần xác minh.
Snapshot gate mới nhất: 2026-07-19 (xem [`doc/operations/progress.md`](doc/operations/progress.md)).

### 1. Chất lượng triển khai kỹ thuật — 20 điểm

- **Stack đa lớp, tách biệt rõ** [BUILT]: Backend Python 3.11 (FastAPI + Uvicorn) + Frontend
  Next.js 16 (React 19, TypeScript 5, Tailwind 4, shadcn). Xem [`pyproject.toml`](pyproject.toml),
  [`demoweb/package.json`](demoweb/package.json).
- **Ranh giới module chặt chẽ** [BUILT]: Gói `src/vneguide/` chia thành `domain/` (contract+enum+
  model), `data/` (loader/repo), `ai/` (provider+extractor), `core/` (orchestration+state),
  `rules/` (validation), `cli/` (terminal I/O), `api/` (FastAPI), `ocr/` (CT01). CLI không chứa
  business logic; không tự tạo enum/field name riêng từng module (xem [`AGENTS.md`](AGENTS.md)).
  ~50 file source Python.
- **Quality gate đầy đủ** [BUILT]: `ruff check` + `ruff format --check` + `mypy --strict` + `pytest
  --cov` + `release_audit.py` ở Python; `npm ci` + `npm audit --audit-level=moderate` + `npm run
  check` (lint+typecheck+test+build) ở frontend. Lệnh chuẩn trong
  [`doc/operations/session-handoff.md`](doc/operations/session-handoff.md).
- **Kết quả gate mới nhất (2026-07-19)** [BUILT]: Python `279 passed, 2 skipped`, coverage
  `80.55%`, mypy strict trên `94` source file; frontend lint/typecheck + `21` unit test; Next
  production build `25` route, `0 vulnerabilities` (npm audit).
- **CI/CD tự động** [BUILT]: GitHub Actions tại `.github/workflows/quality.yml` chạy 3 job trên
  mỗi PR/push nhánh `main`/`dev`/`integration`: (1) Python gate, (2) Web gate, (3) Container build
  + smoke với mock provider. Concurrency group hủy run trùng. Có Dependabot
  (`.github/dependabot.yml`).
- **Container hóa 3 service** [BUILT]: [`deployment/docker-compose.yml`](deployment/docker-compose.yml)
  gồm `api` (FastAPI), `web` (Next.js), `gateway` (nginx 1.29-alpine, pinned digest). Hai Dockerfile
  `api.Dockerfile`/`web.Dockerfile`. Gateway đơn nhất port 8080, healthcheck `/health`.
- **Test đa tầng** [BUILT]: 37 file test trong `tests/unit/` (20), `tests/integration/` (8),
  `tests/evals/` (8) + `tests/fixtures/`; 6 file test TypeScript trong `demoweb/src/` (reducer,
  presentation, reply-options, guided-application, procedure-selection, chat-scope).
- **A/B deterministic** [BUILT]: `python -m tests.evals.run_chat_core_ab` đạt `12/12` fact/topic/
  source, không thêm model call (xem [`doc/operations/progress.md`](doc/operations/progress.md)).

### 2. Kiến trúc AI-Native & Đổi mới sáng tạo — 20 điểm

- **AI native, không gắn thêm (bolt-on)** [BUILT]: LLM chỉ đảm nhiệm **phân loại ý định** và
  **trích xuất trường có evidence**; quy tắc nghiệp vụ (required field, phí, thời hạn, căn cứ pháp
  lý) do rule engine deterministic và data package đã review quyết định. Xem
  [`src/vneguide/rules/engine.py`](src/vneguide/rules/engine.py), [`src/vneguide/ai/extractor.py`](src/vneguide/ai/extractor.py).
- **Provider abstraction** [BUILT]: [`src/vneguide/ai/providers/base.py`](src/vneguide/ai/providers/base.py)
  định nghĩa `LLMProvider` Protocol `generate_structured(StructuredRequest) -> object`. Ba impl:
  `MockLLMProvider` (test), `OpenAIResponsesProvider` (Responses API + JSON schema strict, chỉ
  stdlib `urllib`), `LiteLLMChatCompletionsProvider` (gateway tự host, hỗ trợ Qwen
  `enable_thinking=false`). Chọn provider bằng `VNEGUIDE_LLM_PROVIDER`; API key không bao giờ lộ
  trong `repr`.
- **Structured extraction, không chat tự do** [BUILT]: `StructuredExtractor` gửi `json_schema` +
  `schema_name` cho provider, validate mọi giá trị trả về bằng `ExtractionCatalog`. Tối đa 2 lần
  thử, timeout 20s, giới hạn input 8.000 ký tự. Thất bại → `ExtractionOutcome(status="fallback")`,
  không bao giờ lọt dữ liệu chưa kiểm.
- **Kiểm chứng 3 tầng** [BUILT]: (1) rule deterministic từng trường, (2) cross-rule so sánh dữ liệu,
  (3) LLM chỉ xử phần suy luận ngữ nghĩa người dùng nhập. Mô tả tại
  [`dany-dichvucong-ai/docs/architecture.md`](dany-dichvucong-ai/docs/architecture.md) và
  [`dany-dichvucong-ai/docs/kb-schema.md`](dany-dichvucong-ai/docs/kb-schema.md).
- **Grounded reply composer** [BUILT]: [`src/vneguide/core/replies.py`](src/vneguide/core/replies.py)
  `CatalogReplyComposer` trả lời deterministic về phí/thời gian/hồ sơ/các bước/cơ quan/kênh nộp/kết
  quả **trực tiếp từ procedure pack đã review**, không gọi model. Biến
  `VNEGUIDE_CHAT_CORE_VARIANT=guided` (mặc định) bật layer này; `baseline` để rollback/A-B tức thì.
- **OCR adapter** [BUILT]: [`src/vneguide/ocr/`](src/vneguide/ocr/) (10 file) dùng Qwen
  `Qwen/Qwen3.5-9B` multimodal qua LiteLLM đọc CT01 của thủ tục `1.004194`; chỉ trả candidate
  `field_id`/`suggested_value`/`confidence`/`evidence`, không tự ghi draft.
- **Khóa phạm vi bằng enum** [BUILT]: [`src/vneguide/domain/enums.py`](src/vneguide/domain/enums.py)
  `ProcedureCode` hardcode đúng 3 mã; API trả `scope_warning` nếu procedure ngoài tập hỗ trợ.
- **Đổi mới**: Kiến trúc lai deterministic+LLM 3 tầng, kết hợp data package có checksum và kết quả
  validation truy vet `source_id`, là cách tiếp cận gốc cho công cụ TTHC Việt Nam. Bản 48h là tập con
  hợp lệ của kiến trúc scale-up (xem
  [`dany-dichvucong-ai/docs/architecture.md`](dany-dichvucong-ai/docs/architecture.md)) — không cần
  viết lại logic khi mở rộng.

### 3. Tính khả thi kinh doanh & Lộ trình Pilot — 20 điểm

- **Vấn đề thực** [BUILT]: Người dân không biết chuẩn bị gì, không biết điền đúng/sai, hệ thống hỗ
  trợ quá tải (xem [`doc/Requirement.md`](doc/Requirement.md),
  [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md) mục 1.2).
- **Đối tượng** [BUILT]: Người làm thủ tục lần đầu, người lớn tuổi, người ít rành công nghệ, người
  làm thay người thân (xem [`doc/Product and UX.md`](doc/Product%20and%20UX.md)).
- **3 thủ tục MVP đã xây** [BUILT]: `2.000635` bản sao giấy khai sinh, `1.013314` xác nhận nhà ở,
  `1.004194` đăng ký tạm trú — đủ làm minh chứng khả thi trong 48h.
- **5 thủ tục kế hoạch** [PLANNED]: Bản dự thi mở rộng thêm đăng ký khai sinh, CCCD, kết hôn, giấy
  phép xây dựng (xem [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md) mục 1.3).
- **Lộ trình triển khai 4 pha** [PLANNED]: Phase 0 (5 thủ tục hackathon) → Phase 1 (pilot 1 địa
  phương, toàn bộ TTHC 1 sở, đưa `kb-data.json` vào DB) → Phase 2 (đa sở/đa tỉnh, tách service,
  Knowledge Graph) → Phase 3 (quốc gia, tích hợp DVCQG, VNeID/SSO, API Gateway, Hybrid RAG). Xem
  [`dany-dichvucong-ai/docs/architecture.md`](dany-dichvucong-ai/docs/architecture.md) mục 2.3.
- **Đường tích hợp** [BUILT]: REST API, widget nhúng 1 dòng script, trang portal mô phỏng, không
  cài app, xác thực API key (FR-IN-01..05 trong
  [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md)). Backend hiện có 7 endpoint
  OpenAPI (xem [`doc/Architecture & Delivery.md`](doc/Architecture%20%26%20Delivery.md)).
- **Chi phí & model** [PLANNED]: FPT AI Factory (nhà tài trợ), DeepSeek-V4-Flash ~18 VNĐ/lượt,
  credit ~820k VNĐ; fallback Gemini Flash free tier; FPT Award $2.000 Cloud Credits cho top 5 đội
  dùng FPT AI Factory (xem [`dany-dichvucong-ai/docs/plan.md`](dany-dichvucong-ai/docs/plan.md)).
  Lưu ý: MVP hiện dùng OpenAI/LiteLLM/mock [BUILT]; FPT AI Factory chưa tích hợp — sẽ qua provider
  `litellm` đã có sẵn.

### 4. UX AI-Native & Tư duy thiết kế — 15 điểm

- **Hội thoại thu nhận (intake) tự nhiên** [BUILT]: AI chỉ hỏi câu cần thiết, nhớ lượt trước, hiểu
  câu trả lời rút gọn và cả lỗi gõ (ví dụ `bảo sao` → bản sao). Xem
  [`doc/Product and UX.md`](doc/Product%20and%20UX.md) mục 4.2.
- **Điền từng trường ngay trong chat** [BUILT]: Nút `Nhờ trợ lý điền cùng tôi` tự gửi câu hướng dẫn
  ẩn; core hỏi tuần tự theo field catalog, render lựa chọn enum/boolean thành nút lớn ngay trong chat,
  ghi field thật qua revision guard và tự hỏi field kế tiếp. Transcript không lộ tên field kỹ thuật.
- **Workspace chia sẻ chat + form** [BUILT]: Chat Panel và Form dùng chung `Shared Case Draft
  Store`; ghi nguồn dữ liệu `manual`/`assistant`/`wallet`. `SuggestionCard` cho Accept/Reject/Edit.
  Xem [`doc/Architecture & Delivery.md`](doc/Architecture%20%26%20Delivery.md) mục 2,
  [`demoweb/src/components/`](demoweb/src/components/).
- **Tiếng Việt-first, không lộ thuật ngữ** [BUILT]: Toàn bộ giao diện và nội dung tiếng Việt tự
  nhiên; không hiện tên field/enum kỹ thuật cho người dùng (NFR-04 trong
  [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md)).
- **Mobile-first, thân người lớn tuổi** [PLANNED/BUILT]: Giao diện responsive (NFR-05); nút trả lời
  nhanh lớn, chữ lớn hơn, chấp nhận cách diễn đạt ba miền. Nguyên tắc trong
  [`doc/Product and UX.md`](doc/Product%20and%20UX.md).
- **Đích chạm tối thiểu 48px** [TBD]: Nguyên tắc "nút lớn" được áp dụng nhưng chưa có con số pixel
  cụ thể trong tài liệu; được ghi nhận trong [`doc/operations/progress.md`](doc/operations/progress.md)
  mục "control tối thiểu 48 px cho người lớn tuổi".
- **Đồng bộ form an toàn** [BUILT]: `draftRevision` tăng sau mỗi commit; phản hồi stale bị từ chối
  (HTTP 409); dirty-field tracking ngăn AI ghi đè field người dùng đã xác nhận; không gửi form theo
  từng phím gõ (chỉ khi blur/lưu/xác nhận).

### 5. An toàn AI, Grounding & Độ tin cậy — 15 điểm

- **LLM không được tự sinh quy định** [BUILT]: Nội dung quy định hiển thị cho người dân bắt buộc truy
  vet về `source_id` đã review; LLM chỉ phân loại/trích xuất, không thêm/bỏ giấy tờ, phí, thời hạn
  hay căn cứ pháp lý (NFR-01 trong
  [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md);
  [`AGENTS.md`](AGENTS.md)).
- **Truy vet `source_id`** [BUILT]: Mọi field/rule/checklist/guidance step mang `source_ids`;
  `ProcedureRepository._source_problems()` kiểm mọi source tham chiếu phải tồn tại và
  `SourceStatus.APPROVED`; `ValidationResult` kèm `source_ids` trong output. Xem
  [`src/vneguide/data/repository.py`](src/vneguide/data/repository.py).
- **Data package review workflow** [BUILT]: Mỗi pack có `Approval` (owner, reviewers, approved_at);
  `PackStatus` gồm `DRAFT`/`NEEDS_REVIEW`/`APPROVED`/`STALE`/`RETIRED`; `audit()` ép mọi pack phải
  `APPROVED` lúc runtime (xem
  [`data/docs/review_workflow.md`](data/docs/review_workflow.md)).
- **Checksum SHA-256** [BUILT]: `verify_checksums()` kiểm 13 file `.sha256` trong
  [`data/qa/`](data/qa/) cho mọi pack/catalog/schema/gold test; LF-normalized để ổn định đa nền tảng.
- **Fail-closed guards** [BUILT]: Mọi lỗi provider (timeout, refusal, output sai, config sai) →
  `ExtractionOutcome(status="fallback")` với classification rỗng, không trả dữ liệu chưa kiểm.
  Guard ngữ cảnh chặn dùng nhầm fact route cũ sau `unsupported`/`ambiguous`/procedure switch.
- **Khóa phạm vi & out-of-scope** [BUILT]: `ProcedureCode` enum hardcode 3 mã; rule
  `BIRTH-SCOPE-001/002`, `TEMP-SCOPE-001` trả `ValidationStatus.OUT_OF_SCOPE`. Câu mơ hồ "làm/xin
  giấy khai sinh" được hỏi rõ giữa bản sao (hỗ trợ) và đăng ký mới (ngoài phạm vi).
- **Không gửi PII cho model** [BUILT]: Extractor chỉ nhận compact turn context
  (active_procedure_code + expected_field_id), không gửi transcript/draft chứa PII; không gửi form
  theo từng phím gõ (NFR-10: không bao giờ log dữ liệu cá nhân người dùng nhập form).
- **Che PII khi hiển thị** [BUILT]: [`src/vneguide/cli/renderer.py`](src/vneguide/cli/renderer.py)
  `_mask()` che trường định danh (CCCD) trước khi in.
- **HTTPS bắt buộc ở production** [BUILT]: LiteLLM insecure HTTP mặc định tắt
  (`VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=0`); production phải HTTPS; HTTP chỉ cho gateway dev tin
  cậy + dữ liệu giả (NFR-09).
- **Trạng thái pháp lý** [BUILT]: `LegalRef.status` (`active`/`replaced`/`upcoming`) — văn bản đã
  thay thế không trình bày như đang áp dụng; văn bản chưa hiệu lực ghi "sẽ áp dụng từ [ngày]" (xem
  [`dany-dichvucong-ai/docs/kb-schema.md`](dany-dichvucong-ai/docs/kb-schema.md) mục 3).
- **Live smoke opt-in** [BUILT]: `tests/integration/test_live_smoke.py` đánh dấu `@pytest.mark.live`,
  tắt mặc định; smoke container dùng `--provider mock`.
- **Revision guard** [BUILT]: `PATCH .../draft/fields/{field_id}` và `/suggestions/{id}` trả HTTP
  409 `stale_revision`/`stale_suggestion` khi xung đột (xem
  [`src/vneguide/api/app.py`](src/vneguide/api/app.py)).
- **Release audit** [BUILT]: `deployment/scripts/release_audit.py` chặn identifier 12 chữ số ngoài
  fixture zone, conflict marker, secret và file ngoài scope.

### 6. Trình bày & Bảo vệ giải pháp — 10 điểm

- **Pitch script 3 phút** [BUILT]: [`doc/operations/demo-and-pitch.md`](doc/operations/demo-and-pitch.md)
  kịch bản timeline: 0:00–0:20 vấn đề, 0:20–0:35 phạm vi 3 mã, 0:35–1:50 hero demo (tạm trú:
  suggestion/edit/accept), 1:50–2:15 demo lỗi (stale revision 409, model timeout fallback),
  2:15–2:40 trust (rules, sources, revision guard, HTTPS), 2:40–3:00 kết luận.
- **Sơ đồ kiến trúc** [BUILT]: Mermaid flowchart trong
  [`doc/Architecture & Delivery.md`](doc/Architecture%20%26%20Delivery.md) mục 2; 3 sơ đồ ASCII
  (48h / scale-up / bảng mapping) trong
  [`dany-dichvucong-ai/docs/architecture.md`](dany-dichvucong-ai/docs/architecture.md); context
  diagram Mermaid trong [`dany-dichvucong-ai/docs/srs.md`](dany-dichvucong-ai/docs/srs.md) mục 2.1.
- **Rollback runbook** [BUILT]: [`doc/operations/rollback.md`](doc/operations/rollback.md) — khi nào
  rollback, bước container/local preview, revert bằng `git revert` (không `git reset --hard`), bằng
  chứng hậu rollback (commit digest, UTC timestamp, root cause, secret rotation).
- **Kế hoạch video dự phòng** [PLANNED]: Shot list 5 cảnh (title+disclaimer, /health+revision, hero
  tạm trú, out-of-scope+stale+timeout, source/procedure codes); output
  `VNeGuide-demo-backup-YYYYMMDD.mp4` 1080p H.264 AAC. **Trạng thái: chưa record** — bị chặn chờ merge
  nhánh UI đúng scope (xem [`doc/operations/demo-and-pitch.md`](doc/operations/demo-and-pitch.md)).
- **Preflight checklist** [BUILT]: 7 bước trước demo trong
  [`doc/operations/demo-and-pitch.md`](doc/operations/demo-and-pitch.md) — smoke 5 mẫu, kiểm
  revision/timestamp, `pytest`+`npm run check`, chỉ dùng dữ liệu giả, mở 3 case trong scope + 1 ngoài,
  tắt thông báo, kiểm video dự phòng.
- **One-pager** [BUILT]: [`doc/Product and UX.md`](doc/Product%20and%20UX.md) đóng vai trò one-pager:
  vấn đề, mục tiêu, phạm vi 3 mã, flow cốt lõi, cách tiếp cận AI, mục tiêu đánh giá, kế hoạch bàn giao.
- **Nhật ký cộng tác AI** [BUILT]: [`dany-dichvucong-ai/docs/nhat-ky-ai.md`](dany-dichvucong-ai/docs/nhat-ky-ai.md)
  ghi 4 phiên 17/07/2026 (phân tích, push GitHub, nghiên cứu use-case, review plan, chọn LLM, thiết
  kế KB schema); file phiên gốc trong `~/.claude/projects/` giữ nguyên trạng để nộp.
- **Deploy production thật** [BUILT]: Frontend Vercel `https://vneguide.vercel.app/` (READY), backend
  Render `https://vneguide-api.onrender.com` (live, `openai`/`gpt-4o-mini`, secret qua Dashboard).
  E2E thật Vercel→Render→OpenAI bằng dữ liệu tổng hợp: create session `201`/1.178 giây, message
  `200`/5.039 giây, reply hỏi đúng `requester_type` (xem
  [`doc/operations/progress.md`](doc/operations/progress.md) mục "Deploy Render FastAPI").
- **Caveat minh bạch** [BUILT]: Giới hạn còn lại — browser E2E manual và OCR API/UI sink chưa đạt;
  Render Free sleep sau idle nên session in-memory có thể mất khi restart (xem
  [`deployment/README.md`](deployment/README.md)).

---

## Trạng thái hiện tại & giới hạn (snapshot 2026-07-19)

| Mục | Trạng thái |
| --- | --- |
| Backend/data đúng 3 thủ tục | Đạt |
| Frontend catalog/route đúng 3 thủ tục | Đạt |
| Revisioned form-edit contract + draft snapshot | Đạt |
| Full Python/npm gate trên merge result | Đạt (279 passed, cov 80.55%) |
| BFF gọi đúng backend revisioned | Đạt (BFF smoke) |
| OCR adapter/worker candidate-only + synthetic gate | Đạt (33 passed) |
| Manual edit sync qua browser E2E | Chưa (in-app browser không khả dụng) |
| Rebuild/smoke container từ merge mới | Đạt (Compose local healthy, smoke mock gateway đạt) |
| OCR API/UI sink + browser E2E thật | Chưa |
| Public hosting bền vững | Đạt (Vercel `vneguide.vercel.app` + Render API `vneguide-api.onrender.com`, E2E thật Vercel→Render→OpenAI) |
| Video dự phòng record + review | Chưa |

Giới hạn kỹ thuật cần giữ: LLM chỉ phân loại/trích xuất; session store in-memory chỉ phù hợp một
worker; frontend có banner mô phỏng Hackathon và `noindex`; không tiếp nhận dữ liệu cá nhân thật.
Chi tiết trong [`doc/operations/progress.md`](doc/operations/progress.md) và
[`doc/operations/session-handoff.md`](doc/operations/session-handoff.md).

---

## Yêu cầu

- Python 3.11 trở lên.
- Không cần API key khi dùng mock provider và chạy test mặc định.
- API key cần cho mọi luồng dùng provider thật, gồm CLI, HTTP API và live smoke chủ động.

## Cài đặt

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[api,dev,ocr]"
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[api,dev,ocr]'
cp .env.example .env
```

`.env` đã được Git bỏ qua. Runtime không đọc secret lúc import. Lệnh smoke provider và HTTP API chỉ
đọc file khi được chỉ định rõ bằng `--env-file`; các luồng khác vẫn nhận cấu hình từ environment.
File mẫu mặc định dùng `mock`; chỉ đổi sang LiteLLM/OpenAI khi đã có endpoint HTTPS và secret hợp lệ.

## Chạy chatbot

Lệnh thống nhất:

```powershell
python -m vneguide.cli
```

CLI nạp session factory từ `VNEGUIDE_SESSION_FACTORY`, mặc định là `vneguide.core:create_session`. Factory do lớp tích hợp core cung cấp và phải trả về session có phương thức `send(message) -> TurnResult`. Thiết kế này giữ CLI độc lập với LLM, rule engine và state machine.

Các lệnh trong phiên:

- `/status`: in lại trạng thái hồ sơ gần nhất.
- `/reset`: hủy state hiện tại và tạo session mới.
- `/quit`: đóng session và thoát.

Mỗi lượt hiển thị câu trả lời, thủ tục nhận diện, dữ liệu trích xuất, hồ sơ nháp, trường còn thiếu, lỗi validation, nguồn tham khảo và bước tiếp theo. Các field định danh phổ biến như `cccd` được che trước khi hiển thị.

Hook mặc định `vneguide.core:create_session` đã được triển khai. Với mock provider không có response dựng sẵn, core trả fallback an toàn; để hội thoại bằng model thật cần cấu hình provider/model/key theo phần bên dưới. CLI không chứa business logic của core.

Core mặc định dùng biến thể `guided`. Khi route đã khóa đúng một trong ba mã thủ tục, câu hỏi thuần
guidance như “Lệ phí bao nhiêu?” được trả trực tiếp trước structured extraction; chatbot vì vậy vẫn
trình bày được phí, thời gian, hồ sơ, các bước, cơ quan, kênh nộp và kết quả khi provider chậm hoặc
tạm thời không khả dụng. Matcher dùng whole-message allowlist; câu chứa field, thủ tục khác hoặc nội
dung hỗn hợp vẫn đi qua extractor. Nội dung được render từ procedure pack đã review và giữ
`source_id`; lớp này không đọc transcript/draft và không được thay đổi rule, revision hoặc suggestion.
Đặt `VNEGUIDE_CHAT_CORE_VARIANT=baseline` để rollback/A-B mà không đổi API.

## Chạy HTTP API và demoweb

Browser gọi Next.js BFF tại `/api/chat/*`; BFF giữ session ID trong cookie `HttpOnly` và gọi Python
API ở phía server. API key model không được đưa vào biến `NEXT_PUBLIC_*`.

Terminal 1 — chạy Python Chat API:

```powershell
.venv\Scripts\Activate.ps1
python -m vneguide.api --env-file .env
```

`--env-file` là opt-in tường minh cho local development; file chỉ được đọc các khóa LLM trong danh
sách cho phép. Có thể bỏ tùy chọn này khi provider/model/key đã được đặt trực tiếp trong process
environment.

Terminal 2 — chạy Next.js:

```powershell
Copy-Item demoweb\.env.local.example demoweb\.env.local
Set-Location demoweb
npm ci
npm run dev
```

Mặc định BFF gọi `http://127.0.0.1:8000`. Có thể đổi bằng `VNEGUIDE_API_BASE_URL` trong `demoweb/.env.local`. Kiểm tra API bằng `GET /health`.

Demoweb hiện chỉ hiển thị đúng ba thủ tục đã khóa trong `data/README.md`: `2.000635`, `1.013314` và
`1.004194`. Luồng đăng ký kết hôn cũ đã bị loại khỏi route hỗ trợ.

Trước khi vào hồ sơ, chat xác nhận dịch vụ rồi mở trang chi tiết thủ tục để người dùng chọn
tỉnh/thành phố và phường/xã/cơ quan tiếp nhận; nút `Nộp hồ sơ` chỉ bật khi lựa chọn hợp lệ và mang
nơi tiếp nhận sang hồ sơ, wizard không hỏi lại bước này. URL nộp hồ sơ thiếu `confirmed=1` bị trả
`307` về trang chi tiết; xác nhận từ modal hoặc chat mới tạo URL hợp lệ.

Hồ sơ đi theo bốn bước dùng trực tiếp field catalog đã review: nơi tiếp nhận, kê khai, giấy tờ, kiểm
tra/nhận kết quả. Enum/boolean/date/number dùng control dễ hiểu; field bắt buộc do catalog quyết
định, không do LLM. Nút `Nhờ trợ lý điền cùng tôi` tự gửi câu lệnh hướng dẫn ẩn; core hỏi từng mục
một, render lựa chọn enum/boolean ngay trong chat và ghi field thật qua revision guard, không lộ tên
field kỹ thuật trong transcript.

Shared workspace ghi nguồn dữ liệu `manual`/`assistant`/`wallet`. BFF `/api/chat/field` gọi endpoint
backend revisioned; manual edit được kiểm tra stale revision và đánh dấu field đã xác nhận/dirty.
Đề xuất lưu/điền lại từ ví session chỉ bật sau khi gate kê khai đạt; dữ liệu autofill vẫn phải được
xác nhận trên biểu mẫu trước khi qua bước tiếp theo.

## OCR CT01 (candidate-only)

Module `vneguide.ocr` chỉ xử lý fixture hoặc tài liệu CT01 của thủ tục `1.004194` và chỉ trả candidate;
chưa có đường upload từ demoweb/API và không tự ghi vào draft. Khi chạy worker, export
`VNEGUIDE_OCR_ENABLED`, `VNEGUIDE_OCR_WORKER_TOKEN` cùng các giới hạn OCR vào process environment.
Tùy chọn `--env-file` của worker chỉ nạp provider/model/key LLM, không nạp các biến `VNEGUIDE_OCR_*`.
Xem contract, giới hạn dữ liệu và lệnh smoke tại
[`src/vneguide/ocr/README.md`](src/vneguide/ocr/README.md).

## Cấu hình provider

Các biến mẫu nằm trong `.env.example`:

```text
VNEGUIDE_LLM_PROVIDER=mock
VNEGUIDE_MODEL=mock-scripted
VNEGUIDE_LITELLM_BASE_URL=https://litellm.example.invalid
VNEGUIDE_LITELLM_API_KEY=
VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=0
VNEGUIDE_LITELLM_DISABLE_THINKING=1
VNEGUIDE_API_KEY=
VNEGUIDE_SESSION_FACTORY=vneguide.core:create_session
VNEGUIDE_CHAT_CORE_VARIANT=guided
VNEGUIDE_RUN_LIVE_SMOKE=0
VNEGUIDE_API_HOST=127.0.0.1
VNEGUIDE_API_PORT=8000
VNEGUIDE_SESSION_TTL_SECONDS=1800
VNEGUIDE_SESSION_MAX_ACTIVE=100
VNEGUIDE_OCR_ENABLED=0
VNEGUIDE_OCR_WORKER_TOKEN=
VNEGUIDE_OCR_MAX_QUEUED_JOBS=2
VNEGUIDE_OCR_JOB_TIMEOUT_SECONDS=300
VNEGUIDE_OCR_RESULT_TTL_SECONDS=600
VNEGUIDE_WEB_PORT=3000
VNEGUIDE_GATEWAY_PORT=8080
```

Không commit `.env`, API key, dữ liệu cá nhân thật hoặc transcript chứa số định danh đầy đủ. Dữ liệu test trong repo phải là dữ liệu giả.

`VNEGUIDE_LLM_PROVIDER` là tên provider (`mock`, `openai` hoặc `litellm`), không phải URL.
Để dùng LiteLLM, đổi provider thành `litellm`, đặt model ID đã deploy và cung cấp endpoint/key hợp lệ.
`openai` tiếp tục dùng endpoint HTTPS chính thức đã khóa cứng. `litellm` dùng base URL riêng và
tự nối `/v1/chat/completions`. HTTP bị từ chối mặc định; chỉ bật
`VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1` cho gateway dev tin cậy và dữ liệu tổng hợp. Bearer key,
prompt và phản hồi đều không được mã hóa khi đi qua HTTP; dữ liệu hành chính thật phải dùng HTTPS.

## Quality gates

```powershell
python -m ruff check src tests deployment
python -m ruff format --check src tests deployment
python -m mypy
python -m pytest
python deployment/scripts/release_audit.py
Set-Location demoweb
npm ci
npm audit --audit-level=moderate
npm run check
```

Chạy coverage:

```powershell
python -m pytest --cov=vneguide --cov-report=term-missing
```

Đánh giá A/B deterministic cho câu trả lời nghiệp vụ của đúng ba thủ tục:

```powershell
python -m tests.evals.run_chat_core_ab
```

Lệnh chỉ in metrics tổng hợp, model là `null` vì reply layer không gọi model và không ghi tin nhắn,
draft hoặc dữ liệu cá nhân vào report.

Smoke trực tiếp provider, không phụ thuộc `core` hoặc CLI, bằng đúng một câu tổng hợp không có PII:

```powershell
python -m vneguide.ai.smoke --env-file .env --confirm-live
```

Kết quả thành công có prefix `MODEL_SMOKE_OK`; lệnh không in prompt, raw response, evidence hoặc
API key. `--confirm-live` là bắt buộc để tránh vô tình gửi request mạng.

Live-model integration test là gate chủ động, không chạy mặc định. Hook
`vneguide.core:create_session` đã được triển khai; cấu hình provider, model và key trong environment
rồi chạy:

```powershell
$env:VNEGUIDE_RUN_LIVE_SMOKE="1"
$env:VNEGUIDE_LITELLM_API_KEY="<secret>" # hoặc VNEGUIDE_API_KEY với provider openai
python -m pytest tests/integration/test_live_smoke.py -m live
```

## Container, public smoke và rollback

Stack release giữ đồng thời LiteLLM/OpenAI/mock provider, FastAPI, Next.js và một gateway chung:

```powershell
$env:VNEGUIDE_LLM_PROVIDER="mock"
$env:VNEGUIDE_MODEL="mock-scripted"
docker compose -f deployment/docker-compose.yml up --build --detach --wait
python deployment/scripts/smoke.py `
  --api-url http://127.0.0.1:8080 `
  --web-url http://127.0.0.1:8080 `
  --samples 5 `
  --provider mock `
  --model mock-scripted
```

API demo chạy một worker vì session store nằm trong memory. Hướng dẫn public preview, model secret,
metrics và deploy bền vững nằm trong [`deployment/README.md`](deployment/README.md). Quy trình phục
hồi không force-push nằm trong [`doc/operations/rollback.md`](doc/operations/rollback.md); kịch bản
pitch/video nằm trong [`doc/operations/demo-and-pitch.md`](doc/operations/demo-and-pitch.md).

## Cấu trúc repository

```text
data/
├── catalog/       # Procedure packs, field catalog, rules và source register
├── contracts/     # JSON Schema dùng để validate data package
├── evaluation/    # Bộ dữ liệu đánh giá có ground truth
├── references/    # Tài liệu nguồn được lưu cục bộ
├── qa/            # Checksum kiểm tra tính toàn vẹn
├── docs/          # Quy trình review và quyết định của data package
└── */             # Dataset discovery/RAG seed

doc/               # Requirement, product, architecture và tài liệu vận hành
src/vneguide/      # Source code ứng dụng
tests/             # Unit, integration và evaluation tests
```

## Cấu trúc source code

```text
src/vneguide/
├── domain/     # Contract, enum và model dùng chung — Người 1
├── data/       # Loader/repository truy cập data package — Người 1
├── ai/         # Provider và structured extraction — Người 2
├── core/       # Conversation orchestrator và state — Người 3
├── rules/      # Required fields và validation — Người 3
└── cli/        # Terminal I/O và renderer — Người 4

tests/
├── unit/
├── integration/
└── evals/
```

CLI chỉ gọi public integration port, không chứa business rule và không định nghĩa lại domain model.

## Quy ước dữ liệu

- `data/catalog/` là nguồn dữ liệu runtime đã chuẩn hóa; không tạo bản sao trong `src/`.
- `src/vneguide/data/` chỉ chứa code đọc và kiểm tra data package.
- Tài liệu nguồn chỉ lưu tại `data/references/`.
- Dataset discovery không được dùng trực tiếp để kết luận nghiệp vụ.
- Không commit `.env`, API key, cache, log hoặc dữ liệu cá nhân thật.
