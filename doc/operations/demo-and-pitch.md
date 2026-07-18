# Demo, pitch và video dự phòng

## Preflight 15 phút trước demo

1. Xác nhận public URL và `/health` bằng `deployment/scripts/smoke.py --samples 5`.
2. Xác nhận revision/timestamp trong infra smoke. Nếu cần claim model, chạy live-model smoke riêng
   và xác nhận provider/model/version mà không hiện API key.
3. Chạy `pytest -q tests/integration/test_release_flows.py` và `npm run check`.
4. Dùng hoàn toàn dữ liệu tổng hợp, bật cảnh báo hệ thống không ra quyết định hành chính.
5. Mở sẵn ba thủ tục đúng scope và một case out-of-scope.
6. Tắt notification, console/log có thể lộ dữ liệu và tab repo đối thủ.
7. Kiểm video dự phòng phát offline có tiếng/hình và không chứa PII.

## Kịch bản pitch 3 phút

- 0:00–0:20 — Vấn đề: người dân khó biết hồ sơ thiếu gì trước khi nộp.
- 0:20–0:35 — Phạm vi: đúng ba thủ tục `2.000635`, `1.013314`, `1.004194`; ngoài scope được từ chối.
- 0:35–1:50 — Hero đăng ký tạm trú: nhập nhu cầu, xem suggestion, sửa một field, Accept các field còn
  lại, xem validation/nguồn. Nhấn mạnh AI không tự commit dữ liệu.
- 1:50–2:15 — Failure demo: response stale bị 409; typed model timeout chuyển retry/manual input.
  Chỉ demo OCR sau khi OCR adapter/UI thật đã được merge; hiện mới có generic upstream fallback.
- 2:15–2:40 — Trust: rule/source đã review, limited staged-text pattern scan, revision guard, HTTPS.
- 2:40–3:00 — Kết: VNeGuide giúp chuẩn bị và kiểm tra trước; kết quả không phải quyết định hành chính.

## Shot list video dự phòng

1. Title và disclaimer, 5 giây.
2. Public `/health`, revision và timestamp; provider/model chỉ là label nếu chưa live-smoke, 5 giây.
3. Hero tạm trú đủ 5 checkpoint, tối đa 75 giây.
4. Out-of-scope, stale revision và timeout/OCR fallback, tối đa 30 giây.
5. Ba source/procedure code và kết luận, 15 giây.

Xuất `VNeGuide-demo-backup-YYYYMMDD.mp4`, 1080p, H.264, âm thanh AAC. Lưu hai bản ngoài Git: máy
demo và ổ chia sẻ của đội. Không commit video lớn hoặc transcript có PII vào repository.

## Trạng thái hiện tại

Frontend hiện đã khóa đúng ba thủ tục; Playwright bao phủ ba route, hero tạm trú 5/5 và các luồng
phục hồi chính. Video **chưa được record**. Chỉ đánh dấu “video sẵn sàng” sau khi quay bằng dữ liệu
tổng hợp, hai người trong đội xem lại toàn bộ file và thử phát offline cả tiếng lẫn hình.
