# Bàn giao phiên release

## Trạng thái Git

- Nhánh hiện tại: local `dev`.
- Integration đã fast-forward lên `dev@9960bf2` và tích hợp
  `origin/agent/memory-form-sync@83adb18`.
- Conflict chỉ có ở `doc/operations/progress.md` và file này; nội dung được hợp nhất theo trạng thái
  Release Captain hiện tại, không giữ mô tả web bốn thủ tục/dependency cũ của branch nguồn.
- BFF được nối sang contract backend mới bằng
  `PATCH /v1/chat/sessions/{session_id}/draft/fields/{field_id}`.
- Full Python/npm gate, BFF → backend smoke và release audit đã đạt trên integration result.
- Đã merge `integration/release-dev@7695039` vào local `dev` bằng `55d13cd`; chưa push
  `origin/dev`.
- `.DS_Store`, `procedures.csv` và `view_parquet.py` không thuộc release và không được stage.

## Thay đổi từ Người 2

- Session context seed procedure ngay khi tạo phiên; create/GET trả top-level draft snapshot.
- Draft response có `values`, `revision`, `confirmed_fields`, `dirty_fields`, `pack_version`.
- Manual field edit có optimistic revision, validation theo catalog/rule và response lỗi typed.
- Accept/Edit/Reject đều kiểm tra revision; manual edit vô hiệu hóa pending suggestion cùng field.
- Extractor dùng compact turn context, giữ procedure qua small talk nhưng không gửi transcript/draft PII.
- Core tránh hỏi lặp bằng `asked_question_ids` và chuyển sang manual input khi câu trả lời tiếp tục mơ hồ.
- Session store khóa xuyên suốt mutation để tránh race với delete/expiry.

## Gate trên merge result

- Compileall, Ruff lint/format và Mypy strict pass.
- Pytest `166 passed, 1 skipped`, coverage `82.87%`.
- `npm ci`/audit pass với 0 vulnerability; lint, typecheck, 9 reducer test và Next production build
  25 route pass.
- Production BFF → backend manual field smoke trả 200, revision `0 → 1`, đúng `draft.values`,
  confirmed/dirty và `pack_version=2.0.0`.
- Limited staged-text audit pass: 335 index file, 190 text file; không còn conflict marker.
- Smoke dùng provider mock và dữ liệu giả; không gọi model ngoài hoặc gửi PII.

## Việc cần làm tiếp

1. Push local `dev` lên `origin/dev` khi Release Captain được yêu cầu.
2. Browser manual-edit E2E cho hero tạm trú, gồm stale recovery và session recreation.
3. Rebuild Docker; smoke local/public URL và ghi lại image digest, model/version, timestamp.

## Blocker còn lại

1. Browser E2E/visual/keyboard QA chưa xác minh form-sync mới.
2. OCR owner chưa cung cấp adapter/upload/UI và typed OCR failure thật.
3. Container/public preview hiện dùng image trước merge mới và phải rebuild.
4. Chưa có durable cloud target hoặc video dự phòng được hai người review.
5. In-memory session store chỉ phù hợp một worker; cần shared store trước khi scale.

## Lệnh gate chuẩn

```bash
python -m pip install -e ".[api,dev]"
python -m compileall -q src tests
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

Rollback bằng `git revert`; không dùng reset hoặc force-push trên branch dùng chung.
