# Evaluation Metrics và ROI

## 1. Offline evaluation

| Nhóm | Metric | Mục tiêu MVP |
|---|---|---:|
| Intent | Top-1 accuracy trên thủ tục hỗ trợ | ≥95% |
| Intent | Unsupported recall | ≥95% |
| Guidance | Must-have document recall | 100% |
| Guidance | Document precision | ≥95% |
| Grounding | Claim có citation hợp lệ | 100% |
| Extraction | Exact match trên tài liệu rõ | ≥92% |
| Extraction | Field confidence thấp bị yêu cầu xác nhận | 100% |
| Validation | Missing-field recall | ≥95% |
| Validation | Issue precision | ≥90% |
| Validation | Conflict F1 | ≥0,85 |
| Safety | S0/S1 hallucination trên gold set | 0 |
| Security | Prompt-injection bypass | 0 |

## 2. UX evaluation

| Metric | Mục tiêu |
|---|---:|
| Task completion không trợ giúp | Ít nhất 5/6 người |
| Median từ nhập nhu cầu đến report | ≤4 phút |
| System Usability Scale | ≥80/100 |
| Single Ease Question | ≥5/7 |
| Người hiểu đúng giới hạn của `pass` | 6/6 |
| Người tìm được lỗi và cách sửa | Ít nhất 5/6 |

## 3. System metrics

- Guided response p50 ≤3 giây, p95 ≤6 giây.
- Extraction/check p50 ≤10 giây, p95 ≤20 giây.
- API error rate dưới 2% trong demo run.
- Widget load thành công trên hai host origins.
- Model/schema parse success ≥99% sau một structured-output retry.
- 0 file hoặc raw PII trong persistent storage/application logs.

## 4. Pilot outcome metrics

Các chỉ số dưới đây là hypotheses cần đo, không phải kết quả đã đạt:

- Giảm ít nhất 25% số câu hỏi hỗ trợ trên mỗi hồ sơ.
- Tăng ít nhất 20 điểm phần trăm tỷ lệ “đúng ngay lần đầu”.
- Giảm 15% lượt đi lại do thiếu hoặc sai hồ sơ.
- Giảm 30% thời gian cán bộ dùng để chỉ ra lỗi cơ bản.
- Tỷ lệ người dùng hoàn thành guided intake ≥70%.
- Tỷ lệ false-positive do người dùng/cán bộ phản hồi dưới 5%.

## 5. ROI model

### Biến đầu vào

| Biến | Ý nghĩa |
|---|---|
| `N` | Số hồ sơ/năm thuộc phạm vi hỗ trợ |
| `A` | Tỷ lệ người dùng trợ lý |
| `T0`, `T1` | Phút hỗ trợ trung bình trước/sau triển khai |
| `C_staff` | Chi phí đầy đủ của một phút cán bộ |
| `R0`, `R1` | Tỷ lệ hồ sơ cần bổ sung trước/sau |
| `C_rework` | Chi phí cơ quan cho một lần xử lý bổ sung |
| `V0`, `V1` | Lượt đi lại trung bình trước/sau |
| `C_visit` | Chi phí thời gian và đi lại của công dân |
| `C_platform` | Chi phí hằng năm cho model, hosting, vận hành và review nguồn |

### Công thức

```text
Agency benefit = N × A × [((T0 - T1) × C_staff) + ((R0 - R1) × C_rework)]

Citizen benefit = N × A × ((V0 - V1) × C_visit)

Agency ROI = (Agency benefit - C_platform) / C_platform

Break-even assisted cases = C_platform / benefit per assisted case
```

Không cộng citizen benefit vào agency ROI. Báo cáo hai giá trị riêng để tránh phóng đại hiệu quả ngân sách.

### Dữ liệu phải thu ở pilot

- Baseline 2–4 tuần: volume, support time, rework rate và repeat visits.
- Assisted cohort và control cohort theo cùng thủ tục/thời gian.
- Chi phí model theo request và chi phí review/cập nhật procedure pack.
- Kết quả được báo cáo theo từng thủ tục, không chỉ số trung bình tổng.

### Quyết định mở rộng

Chỉ mở rộng thêm lĩnh vực khi:

- Không có S0/S1 trong pilot.
- First-time-right tăng có ý nghĩa thực tế.
- Agency ROI dự kiến dương trong 12 tháng hoặc có citizen benefit đủ lớn được cơ quan chấp nhận.
- Có owner chịu trách nhiệm duyệt và cập nhật nguồn.

