# Checklist trạng thái sạch

## Trước khi commit hoặc bàn giao

- [ ] `git status --short` không có file ngoài scope.
- [ ] Không còn `<<<<<<<`, `=======` hoặc `>>>>>>>` trong source và tài liệu.
- [ ] JSON trong `data/catalog/` và `data/contracts/` parse được.
- [ ] JSONL trong `data/evaluation/` parse được từng dòng.
- [ ] Mọi `local_file` trong source register trỏ tới file tồn tại.
- [ ] Checksum được cập nhật nếu artifact tương ứng thay đổi.
- [ ] Không có secret, `.env`, log chứa PII hoặc dữ liệu cá nhân thật.
- [ ] Test liên quan đã chạy; nếu không chạy được phải ghi rõ lý do.
- [ ] `progress.md` phản ánh đúng trạng thái đã xác minh.
- [ ] `session-handoff.md` nêu một bước tiếp theo cụ thể nếu còn việc dở.
