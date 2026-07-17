# AI Product Canvas và Failure Modes

## 1. AI Product Canvas

| Thành phần | Đặc tả |
|---|---|
| Người dùng | Công dân Hà Nội; người hỗ trợ thân nhân; cán bộ một cửa |
| Nhu cầu | Xác định đúng thủ tục, chuẩn bị đúng giấy tờ và sửa lỗi trước khi nộp |
| Giá trị | Giảm thời gian tìm hiểu, hồ sơ bị trả lại, lượt đi lại và câu hỏi lặp lại |
| Quyết định hỗ trợ | Chọn thủ tục, xác định nhánh checklist, ưu tiên lỗi cần sửa |
| Tác vụ AI | Intent routing, hỏi làm rõ, diễn giải dễ hiểu, trích xuất ảnh/PDF, so sánh ngữ nghĩa |
| Tác vụ deterministic | Checklist, điều kiện bắt buộc, format, trạng thái và source/version control |
| Dữ liệu | DVCQG, biểu mẫu theo lĩnh vực, văn bản pháp luật, procedure packs, hồ sơ mẫu |
| Human-in-the-loop | Reviewer duyệt rule pack; người dùng xác nhận OCR; cán bộ xử lý `needs_review` |
| Feedback | Helpful/not helpful, issue được chấp nhận/sửa, latency, rule/model version; không lưu PII |
| Ranh giới | Không nộp hồ sơ, không cam kết chấp thuận, không tư vấn tranh chấp |
| Lợi thế | Kết hợp rule-first, nguồn chính thức và pre-check đa tài liệu thay vì chatbot hỏi đáp chung |

## 2. Nguyên tắc phân chia trách nhiệm

| Thành phần | Được phép | Không được phép |
|---|---|---|
| LLM router | Nhận diện nhu cầu và missing discriminators | Tự quyết định checklist |
| LLM explainer | Diễn đạt procedure pack bằng ngôn ngữ dễ hiểu | Thêm phí, thời gian, giấy tờ hoặc điều kiện |
| LLM extractor | Trích xuất value/evidence/confidence | Điền giá trị không nhìn thấy |
| Semantic checker | Phát hiện khác biệt cần xem xét | Kết luận pháp lý về danh tính/quyền sở hữu |
| Rule engine | Áp dụng quy tắc đã duyệt | Suy diễn ngoài rule/version hiện tại |

## 3. Failure-mode register

| ID | Failure mode | Tác động | Detection | Kiểm soát/fallback |
|---|---|---|---|---|
| FM-01 | Dùng quy định cũ | Checklist sai | `last_verified_at`, diff nguồn | Version pack, banner hết hạn, review trước publish |
| FM-02 | Trộn trung ương và địa phương | Sai phí/cơ quan | Jurisdiction mismatch test | Khóa `HN`, không merge record thiếu metadata |
| FM-03 | LLM tự thêm yêu cầu | Gây chuẩn bị thừa/sai | Citation entailment test | Guidance chỉ render từ rule pack |
| FM-04 | LLM bỏ sót yêu cầu | Hồ sơ bị trả lại | Must-have recall | Deterministic checklist và gold set |
| FM-05 | OCR đọc sai | False error hoặc bỏ sót | Confidence/evidence | Bắt xác nhận, trường thấp trả `null` |
| FM-06 | False conflict | Người dùng sửa sai | Semantic threshold | Chuẩn hóa dấu/tên/địa chỉ; chuyển `needs_review` |
| FM-07 | Intent routing sai | Hướng dẫn sai thủ tục | Confidence và user confirm | Dừng dưới 0,75, cho đổi thủ tục |
| FM-08 | Prompt injection trong file | Bypass rule | Adversarial tests | File là untrusted data, output schema đóng |
| FM-09 | Rò rỉ PII | Rủi ro pháp lý/niềm tin | Log inspection | Dữ liệu mẫu, memory-only, redact logs |
| FM-10 | Model timeout/quota | Luồng bị ngắt | Metrics/error code | Timeout, retry một lần, hướng dẫn tĩnh, thử lại |
| FM-11 | Source không truy cập được | Không cập nhật được | Ingestion health | Dùng snapshot đã duyệt, cảnh báo tuổi dữ liệu |
| FM-12 | Người dùng quá tin AI | Quyết định sai | Usability interview | Disclaimer theo ngữ cảnh và link cơ quan chính thức |
| FM-13 | File độc hại/quá lớn | Abuse/DoS | MIME, size, rate | Magic-byte check, 10 MB/10 trang, rate limit |
| FM-14 | UX khó dùng | Bỏ cuộc | Task completion/SUS | Mobile-first, progressive disclosure, plain language |

## 4. Severity policy

- **S0 — Critical:** làm lộ dữ liệu, hướng dẫn trái nguồn hoặc bypass an toàn; chặn release.
- **S1 — High:** bỏ sót giấy tờ bắt buộc hoặc sai thủ tục; chặn release.
- **S2 — Medium:** false positive, diễn giải khó hiểu hoặc lỗi một nhánh hiếm; sửa trước pilot.
- **S3 — Low:** lỗi trình bày không ảnh hưởng quyết định; đưa vào backlog.

