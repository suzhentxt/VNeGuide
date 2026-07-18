# Evaluation cases

Chứa test case có ground truth cho intent, slot extraction, hội thoại nhiều lượt và yêu cầu ngoài phạm vi. Không chứa dữ liệu cá nhân thật.

`terminal_acceptance_cases.json` khóa ba procedure code đã duyệt trong `data/README.md` và một ca ngoài phạm vi. Người 2–3 có thể dùng cùng fixture này cho extractor và conversation engine; Người 4 chỉ kiểm tra cấu trúc/coverage cho đến khi domain contract được merge.

`chat_core_ab_cases.json` chứa 12 câu hỏi tổng hợp, cân bằng trên ba thủ tục và bốn topic chính.
Chạy `python -m tests.evals.run_chat_core_ab` để so baseline với `CatalogReplyComposer`. Gate yêu cầu
fact coverage của guided tối thiểu 85%, tăng ít nhất 25 điểm phần trăm, source grounding 100% và
không thêm model call. Report chỉ có số liệu tổng hợp và timestamp.
