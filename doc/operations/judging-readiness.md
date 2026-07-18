# Mức sẵn sàng theo tiêu chí chấm VAIC

Ngày audit: 2026-07-19. Phạm vi audit là artifact trong repository, CI và production preview. Đây là
đánh giá **độ phủ bằng chứng nội bộ**, không phải điểm do ban giám khảo cam kết trao.

## Kết luận điều hành

Repo đã có một MVP chạy được, có kiến trúc AI tách lớp, đúng ba thủ tục, public preview và các kiểm
soát grounding/human-in-the-loop đáng kể. Repo chưa thể trung thực tuyên bố “đáp ứng trọn 100/100” vì
bốn loại bằng chứng phải được tạo ngoài code vẫn còn thiếu: thử nghiệm người dùng mục tiêu, cam kết
đơn vị pilot, security/privacy assessment độc lập và video demo dự phòng.

| Tiêu chí | Tối đa | Độ phủ evidence nội bộ | Trạng thái | Khoảng trống quyết định |
| --- | ---: | ---: | --- | --- |
| Triển khai kỹ thuật & chiều sâu kỹ thuật | 20 | 18 | Mạnh | Session chưa durable; chưa có load/SLA test trên hạ tầng pilot |
| Kiến trúc AI-Native & đổi mới | 20 | 18 | Mạnh | Chưa có live accuracy/ablation report trên tập eval đủ lớn |
| Khả thi kinh doanh & lộ trình pilot | 20 | 13 | Có kế hoạch, thiếu xác nhận thị trường | Chưa có LOI/đơn vị pilot, user validation và unit economics thực đo |
| UX AI-Native & tư duy thiết kế | 15 | 12 | Có luồng và automation | Chưa có moderated usability test với người lớn tuổi; chưa có audit WCAG độc lập |
| An toàn AI, grounding & độ tin cậy | 15 | 13 | Mạnh ở application layer | Chưa có DPIA, penetration test, production rate limit và red-team report độc lập |
| Trình bày, demo & bảo vệ | 10 | 8 | Demo/runbook sẵn | Chưa record và review video dự phòng |
| **Tổng độ phủ evidence** | **100** | **82** | **Đủ để trình diễn, chưa production/pilot-ready** | Hoàn thành checklist ngoài code bên dưới |

## 1. Triển khai kỹ thuật — 20

### Bằng chứng đã có

- Next.js/BFF, FastAPI, conversation core, rules và data package có ranh giới rõ ràng.
- Contract revisioned chống stale update; sửa tay không bị AI ghi đè; session mất/đổi thủ tục được
  tạo lại trong BFF.
- Python lint/format/mypy/test/coverage, frontend lint/type/unit/build và Playwright E2E là quality
  gate trong `.github/workflows/quality.yml`.
- Vercel và Render đều bám branch `dev`; public web và `/health` trả HTTP 200.
- Dependency audit, limited secret/PII/conflict scan và container smoke có lệnh tái lập.

### Không được claim quá mức

- Render Free + in-memory session không có SLA, persistence hoặc khả năng scale ngang.
- Public synthetic smoke chứng minh wiring hoạt động, không chứng minh tải, độ chính xác nghiệp vụ hay
  availability production.

## 2. Kiến trúc AI-Native & đổi mới — 20

### Bằng chứng đã có

- LLM làm routing/extraction có schema và evidence; rule deterministic sở hữu required field, phí,
  thời hạn và kết luận trạng thái.
- Suggestion-first: AI không tự commit và không tự nộp hồ sơ.
- Chat và form dùng chung draft/revision; guided help có thể thao tác từng trường.
- OpenAI/LiteLLM/mock dùng chung provider contract; timeout, malformed output và refusal có fallback.
- Chuẩn hóa phương ngữ/ASR hai tầng bảo vệ định danh và giữ ánh xạ raw → normalized evidence.

### Bằng chứng nên bổ sung

- Báo cáo accuracy theo từng intent/field/dialect trên model production, gồm model/version, timestamp,
  cost, latency và failure taxonomy.
- Ablation: so sánh chatbot thuần LLM với schema + rules + confirmation để chứng minh giá trị thiết kế.

## 3. Khả thi kinh doanh & lộ trình pilot — 20

### Bằng chứng đã có

- Nhóm khách hàng B2G/B2B2G, value proposition, mô hình tích hợp procedure pack và pilot 12 tuần.
- KPI go/no-go tách rõ mục tiêu khỏi kết quả MVP: task success, giảm thời gian, giảm hồ sơ bổ sung,
  grounding, safety và availability.
- Kiến trúc mở rộng theo catalog/rule/source thay vì nhân bản prompt cho từng thủ tục.

### Bắt buộc tạo ngoài repository trước khi claim pilot-ready

1. Chọn một đơn vị một cửa/đơn vị vận hành và có email/LOI xác nhận sponsor, owner và phạm vi.
2. Phỏng vấn hoặc usability test ít nhất 5 người thuộc nhóm mục tiêu; lưu protocol, consent, insight và
   thay đổi thiết kế, không lưu PII trong repo public.
3. Đo token/session, hạ tầng/session, thời gian hỗ trợ và baseline hồ sơ bổ sung để lập unit economics.
4. Chốt DPA/DPIA, data retention, support/incident owner và ngân sách hạ tầng pilot trả phí.

## 4. UX AI-Native & tư duy thiết kế — 15

### Bằng chứng đã có

- Xác nhận dịch vụ trước điều hướng; chào hỏi/làm rõ không bị gắn out-of-scope quá sớm.
- Một câu hỏi mỗi lượt, nhãn tiếng Việt đời thường, lựa chọn cố định bằng nút, Accept/Edit/Reject.
- “Nhờ trợ giúp” truyền ngữ cảnh trường hiện tại; form vẫn dùng được khi AI timeout.
- Playwright kiểm đúng ba route, hero tạm trú 5/5, edit, stale, reset, session recovery, timeout và
  out-of-scope; OCR UI hiện được đánh dấu chưa triển khai thay vì tạo bằng chứng giả.
- UI có semantic role/label, focus-visible, `aria-live`, responsive panel và cảnh báo demo/PII.

### Khoảng trống

- Chạy moderated task test trên mobile và desktop với người lớn tuổi/người lần đầu làm DVC.
- Chạy audit keyboard, screen reader, contrast và zoom 200%; phân loại blocker theo WCAG 2.2 AA.

## 5. An toàn AI, grounding & độ tin cậy — 15

### Bằng chứng đã có

- Phạm vi khóa đúng ba procedure pack; fact nghiệp vụ truy về `source_id` đã review.
- Strict output schema, allowlist field, evidence check, protected spans và ambiguity clarification.
- Revision guard, dirty-field protection, idempotent turn ID và confirmation trước commit.
- Server-only model key, HttpOnly session cookie, HTTPS preview, disclaimer, no-auto-submit và limited
  release audit.
- Draft thiếu field không còn được biểu diễn là `ready_to_submit`.

### Khoảng trống

- Production rate limit, durable encrypted session store, authentication/authorization và audit log.
- DPIA/threat model, retention/deletion verification, penetration test và prompt-injection red-team có
  báo cáo độc lập.
- Freshness owner và SLA review nguồn pháp lý trước pilot.

## 6. Trình bày, demo & bảo vệ — 10

### Bằng chứng đã có

- Public URL, health endpoint, kịch bản demo 3 phút, failure demo, rollback/runbook và Q&A phản biện.
- README phân biệt “đã triển khai”, “đã kiểm chứng” và “mục tiêu pilot”, tránh biến roadmap thành claim.
- Evidence ghi model/version/timestamp và giới hạn của từng loại smoke.

### Việc còn lại trước giờ chấm

1. Record video 1080p/H.264 theo `demo-and-pitch.md`, dùng dữ liệu tổng hợp; hai thành viên review.
2. Lưu hai bản ngoài Git và thử phát offline cả tiếng/hình.
3. Rehearse demo chính và failure fallback; mở sẵn URL/health, không để tab secret hoặc repo tham khảo.
4. Chụp evidence cuối cùng sau deploy đúng commit và ghi SHA/deployment ID/timestamp.

## Lệnh tái lập evidence

```bash
python -m ruff check src tests deployment
python -m ruff format --check src tests deployment
python -m mypy
python -m pytest --cov=vneguide --cov-report=term-missing
python deployment/scripts/release_audit.py

cd demoweb
npm ci
npm audit --audit-level=moderate
npm run check
npx playwright install chromium
npm run test:e2e
```

Public smoke không gửi PII:

```bash
python deployment/scripts/smoke.py \
  --api-url https://vneguide-api.onrender.com \
  --web-url https://vneguide.vercel.app \
  --provider openai \
  --model gpt-4o-mini
```

Chi tiết số liệu, SHA và deployment ID phải lấy từ
[`release-evidence.md`](release-evidence.md); không sao chép số cũ vào slide mà không chạy lại.
