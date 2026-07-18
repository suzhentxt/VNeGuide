# Rollback runbook

## Khi nào rollback

Rollback nếu `/health` lỗi, web không tải, schema/API không tương thích, session/revision sai, secret
hoặc PII xuất hiện, hay UI route ra ngoài đúng ba procedure code đã khóa.

## Container/local preview

1. Dừng nhận demo mới và lưu report không chứa PII.
2. Xem trạng thái: `docker compose -f deployment/docker-compose.yml ps`.
3. Xem log đã redact; không dán transcript người dùng vào issue.
4. Quay lại immutable image tag/digest trước đó trong manifest deploy rồi chạy `docker compose up -d`.
5. Chạy lại `deployment/scripts/smoke.py` cho `/health` và web.

Để tắt preview hoàn toàn:

```bash
docker compose -f deployment/docker-compose.yml down
```

Session store nằm trong memory nên restart sẽ xóa mọi session tạm. Đây là hành vi chấp nhận được cho
demo nhưng phải thông báo cho người test.

## GitHub/dev

Không dùng `git reset --hard` hoặc force-push shared branch. Tạo commit đảo ngược có thể audit:

```bash
git switch dev
git pull --ff-only origin dev
git revert <bad-release-commit>
git push origin dev
```

Nếu release gồm merge commit, Release Captain phải xác định đúng mainline trước khi chạy
`git revert -m`; không suy đoán parent. Chạy toàn bộ Python/web gates và smoke trên commit rollback
trước khi công bố khôi phục.

## Sau rollback

- Ghi commit/image digest, timestamp UTC, nguyên nhân và người quyết định vào release evidence.
- Rotate secret nếu có khả năng lộ; xóa secret khỏi history cần quy trình riêng và phối hợp repo admin.
- Mở issue cho root cause; không nới schema, quality threshold hoặc security scan để deploy lại.
