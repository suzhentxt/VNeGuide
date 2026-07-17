# Source Register và Data Governance

## 1. Nguồn gốc dữ liệu

Nguồn ưu tiên theo thứ tự:

1. Cổng Dịch vụ công Quốc gia và catalog thủ tục hành chính.
2. Quyết định công bố thủ tục của cơ quan có thẩm quyền.
3. Văn bản quy phạm pháp luật đang có hiệu lực.
4. Biểu mẫu/tờ khai chính thức đính kèm theo thủ tục hoặc văn bản.
5. Hướng dẫn của cơ quan thực hiện tại Hà Nội.

Không sử dụng blog, diễn đàn hoặc nội dung do LLM tạo làm nguồn quy tắc.

## 2. Seed sources

| ID | Nội dung | Nguồn |
|---|---|---|
| SRC-DVC-TRANSITION-2026 | Chuyển đổi vận hành Cổng DVCQG năm 2026 | https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-tin-tuc.html?new_id=982 |
| SRC-BIRTH-DVC | Thành phần hồ sơ khai sinh và biểu mẫu | https://dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=1.000110.000.00.00.H01 |
| SRC-RESIDENCE-DVC | Đăng ký thường trú, kênh nộp, thời gian và phí | https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=6007 |
| SRC-INTEROP-63-2024 | Liên thông khai sinh, thường trú, BHYT trẻ dưới 6 tuổi | https://vanban.chinhphu.vn/?classid=1&docid=210359&orggroupid=2&pageid=27160 |
| SRC-BUILD-DVC | Catalog cấp giấy phép xây dựng mới | https://thutuc.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=369206 |
| SRC-GEMINI-MODELS | Model catalog | https://ai.google.dev/gemini-api/docs/models |
| SRC-GEMINI-DOCS | PDF/document understanding | https://ai.google.dev/gemini-api/docs/document-processing |

Các URL seed chỉ là điểm bắt đầu. Trước khi publish procedure pack, reviewer phải xác nhận record đúng địa bàn Hà Nội, mã thủ tục, cơ quan thực hiện và phiên bản có hiệu lực tại ngày build.

## 3. Procedure-pack metadata

Mỗi pack bắt buộc có:

```yaml
procedure_id: birth-registration
procedure_code: "official-code"
jurisdiction: HN
version: "YYYY-MM-DD.N"
status: draft | reviewed | published | expired
effective_from: YYYY-MM-DD
last_verified_at: YYYY-MM-DD
reviewers:
  - name_or_id: reviewer-1
sources:
  - source_id: SRC-...
    retrieved_at: YYYY-MM-DDTHH:mm:ssZ
    content_hash: sha256:...
```

## 4. Quy trình ingestion và review

1. Tải trang/biểu mẫu ở offline ingestion; lưu URL, retrieved time và hash.
2. Parse thành draft schema nhưng giữ raw excerpt liên kết tới từng rule.
3. So sánh record theo jurisdiction, procedure code và effective date.
4. Reviewer thứ nhất kiểm tra checklist, điều kiện, phí, thời gian và cơ quan.
5. Reviewer thứ hai kiểm tra các rule ảnh hưởng must-have document hoặc rejection risk.
6. Chạy schema validation, source-link check và gold tests.
7. Publish version bất biến; thay đổi tạo version mới, không sửa ngầm version cũ.

## 5. Freshness policy

- Demo: kiểm tra lại toàn bộ nguồn ngay trước submission.
- Pilot: chạy source-diff hằng tuần và review thủ công khi hash thay đổi.
- Production: event/schedule ingestion, approval workflow và audit trail.
- Pack quá 30 ngày chưa kiểm chứng hiển thị cảnh báo nội bộ; quá 90 ngày không được dùng để tạo kết luận `pass` nếu chưa có owner phê duyệt.

## 6. Conflict policy

Khi hai nguồn chính thức mâu thuẫn:

1. Không để LLM tự chọn nguồn.
2. Ưu tiên văn bản còn hiệu lực và quyết định công bố áp dụng đúng Hà Nội.
3. Gắn pack ở trạng thái `blocked_for_review` nếu xung đột ảnh hưởng checklist, phí, thời gian hoặc cơ quan.
4. Trong demo, chuyển trường hợp sang `needs_review` và dẫn cả hai nguồn nếu chưa giải quyết được.

