# Bàn giao phiên release

## Trạng thái Git

- Nhánh: `integration/release-dev`.
- Merge `tuan`: `4865ceb`; tài liệu scope: `ff06998`; release baseline: `a8e182f`.
- Đã merge `origin/dev` tại `e65b31b`; commit này nối model với web, tăng BFF timeout, tự phục hồi
  session hết hạn và mang bản format `session_store.py` từ API owner.
- Conflict được giới hạn và đã resolve ở `.env.example`, `progress.md` và `session-handoff.md`; giữ cả LiteLLM,
  FastAPI, Next.js và cấu hình Compose.
- Repo đối thủ, DOCX, CSV, `.DS_Store` và `view_parquet.py` không được stage.
- Chưa merge/push `dev` vì Definition of Done sản phẩm còn blocker.

## Runtime preview

Docker/ngrok hiện phục vụ image đã rebuild sau merge `e65b31b`.

- Docker Compose: API `8000`, web `3000`, gateway `8080`.
- Ngrok preview: `https://moschate-terri-dereistically.ngrok-free.dev`.
- Smoke `2026-07-18T08:48:03.132143Z`: public `/` và `/health` đều 5/5 HTTP 200.
- Runtime xác nhận `provider=mock`, `model=mock-scripted`; smoke không gọi model.
- Image: API `sha256:c72a78e6a5b5...9e4f`, web `sha256:b87a68c910cf...c0b7`.
- Preview là tunnel tạm, mất khi process/máy dừng và không được ghi là production.

Tắt stack khi không cần demo:

```bash
docker compose -f deployment/docker-compose.yml down
```

Ngrok phải được dừng riêng bằng `Ctrl+C` trong terminal đang chạy.

## Thay đổi nhận từ `origin/dev`

- API hỗ trợ opt-in model config bằng `python -m vneguide.api --env-file .env`; không tự đọc secret
  khi import.
- Composition root truyền env-file được chỉ định vào provider config.
- BFF timeout là 60 giây để bao phủ retry provider có giới hạn.
- Widget tạo session mới và retry đúng một lần khi backend trả 404/410 cho session cũ.
- Retry 404/410 mới chỉ được source review và compile/build; chưa có component/browser test hành vi.
- Root layout giảm cảnh báo hydration do extension trình duyệt.
- Test mới kiểm CLI args/env-file và model config runtime.
- Bằng chứng live model ở commit nguồn chỉ dùng dữ liệu tổng hợp; phải đo lại nếu cần claim model,
  version hoặc latency cho artifact release cuối.

## Blocker cần owner khác xử lý

1. UI owner thay luồng Hôn nhân và gia đình bằng route/form cho `2.000635`, `1.013314`, `1.004194`.
2. API/form contract cần `draft.values` và mutation/policy cho manual edit trực tiếp nếu flow yêu cầu.
3. OCR owner cung cấp adapter/upload contract/UI và typed failure; test hiện chỉ kiểm generic fallback.
4. Sau UI merge, mở browser tab để chạy/chụp browser E2E và record video dự phòng.
5. Chọn cloud target/cấp credential để thay ngrok bằng URL lâu dài.
6. In-memory session store chỉ phù hợp một API worker; cần shared store trước khi scale.
7. Workflow đang dùng major action tags; pin action SHA là hardening còn lại trước production.

## Việc Release Captain làm tiếp

1. Sau khi UI/OCR owner giao branch, merge từng branch vào integration và chạy gate sau từng merge.
2. Viết browser/component test cho retry session 404/410 và test timeout gateway có delay thật.
3. Rebuild Compose, smoke local/public và cập nhật evidence sau mỗi merge ảnh hưởng runtime.
4. Chạy limited staged-text audit; xác nhận file cá nhân/untracked không lọt vào commit.
5. Record/review video; chốt rollback image/tag.
6. Chỉ merge/push `dev` khi DoD thực sự đạt; không force-push shared branch.

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

Chạy API/model có opt-in:

```bash
python -m vneguide.api --env-file .env
python -m vneguide.ai.smoke --env-file .env --confirm-live
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

Rollback bằng `git revert` và image digest theo `doc/operations/rollback.md`; không dùng reset hoặc
force-push trên branch dùng chung.
