# Bàn giao phiên release

## Trạng thái Git

- Nhánh: `integration/release-dev`; origin/dev không thay đổi kể từ `1d3e566`.
- Merge `tuan`: `4865ceb`; tài liệu scope: `ff06998`.
- Release files đã được stage tách biệt; repo đối thủ, DOCX, CSV, `.DS_Store` và `view_parquet.py`
  không được stage.
- Chưa tạo commit release cuối và chưa merge/push `dev` vì DoD sản phẩm còn blocker.

## Runtime đang chạy trên máy release

- Docker Compose: API `8000`, web `3000`, gateway `8080`.
- Ngrok preview: `https://moschate-terri-dereistically.ngrok-free.dev`.
- Smoke gần nhất `2026-07-18T08:35:45.553122Z`: public `/` và `/health` đều 5/5 HTTP 200.
- Image đã smoke: API `sha256:a3e4771015bf...a092`, web `sha256:e8b84b8ea57d...ed1a`.
- Preview là tạm thời và mất khi process/máy dừng; không ghi URL này là production.

Tắt sạch khi không cần demo:

```bash
docker compose -f deployment/docker-compose.yml down
```

Ngrok process phải được dừng riêng bằng `Ctrl+C` trong terminal đã chạy nó.

## Blocker cần owner khác xử lý

1. UI owner thay toàn bộ Hôn nhân và gia đình bằng route/form cho `2.000635`, `1.013314`, `1.004194`.
2. API/form contract cần `draft.values` và mutation/policy cho manual edit trực tiếp nếu flow yêu cầu.
3. OCR owner cung cấp adapter/upload contract/UI và typed failure; test hiện chỉ kiểm generic fallback.
4. API owner format `src/vneguide/api/session_store.py` bằng Ruff hiện hành hoặc người dùng cho phép
   Release Captain sửa file ngoài ownership.
5. Sau UI merge, mở browser tab để chạy/chụp browser E2E và record video dự phòng.
6. Chọn cloud target/cấp credential để thay ngrok bằng URL lâu dài.

## Thứ tự tích hợp tiếp theo

1. `git fetch origin --prune` và xác nhận branch owner cụ thể.
2. Merge từng branch vào `integration/release-dev`; chạy Python/web gate sau mỗi merge.
3. Chạy `tests/integration/test_release_flows.py`, browser E2E và public smoke.
4. Cập nhật duy nhất `progress.md`, `session-handoff.md` và `release-evidence.md` bằng kết quả thật.
5. Record/review video; chốt rollback image/tag.
6. Commit/push integration, merge vào `dev`, chạy gate lần cuối rồi chỉ Release Captain push `dev`.

Không dùng force-push hoặc reset shared branch. Nếu rollback, dùng commit `git revert` theo
`doc/operations/rollback.md`.

## Lệnh gate chuẩn

```bash
python -m pip install -e ".[api,dev]"
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

Metrics/public smoke:

```bash
python deployment/scripts/smoke.py \
  --api-url https://<release-host> \
  --web-url https://<release-host> \
  --samples 5 \
  --provider <provider> \
  --model <model-version>
```
