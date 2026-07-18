# Bàn giao phiên release

## Trạng thái Git

- Nhánh hiện tại: local `dev`, đang tích hợp `origin/agent/rules-ai-eval@4a7aac3` trên nền release
  hiện hành. Gate trên cây hợp nhất Rules/AI chưa chạy lại nên chưa được tính là bằng chứng release.
- Integration đã fast-forward lên `dev@9960bf2`, tích hợp
  `origin/agent/memory-form-sync@83adb18`, rồi merge vào local `dev` bằng `55d13cd`.
- Phạm vi runtime vẫn khóa đúng ba mã trong `data/README.md`: `2.000635`, `1.013314` và `1.004194`.
- BFF được nối sang contract backend bằng
  `PATCH /v1/chat/sessions/{session_id}/draft/fields/{field_id}`.
- Full Python/npm gate, BFF → backend smoke và release audit đã đạt trên baseline `dev` trước lượt
  hợp nhất Rules/AI này.
- `.DS_Store`, `procedures.csv` và `view_parquet.py` không thuộc release và không được stage.

## Thay đổi từ Người 2

- Session context seed procedure ngay khi tạo phiên; create/GET trả top-level draft snapshot.
- Draft response có `values`, `revision`, `confirmed_fields`, `dirty_fields`, `pack_version`.
- Manual field edit có optimistic revision, validation theo catalog/rule và response lỗi typed.
- Accept/Edit/Reject đều kiểm tra revision; manual edit vô hiệu hóa pending suggestion cùng field.
- Extractor dùng compact turn context, giữ procedure qua small talk nhưng không gửi transcript/draft PII.
- Core tránh hỏi lặp bằng `asked_question_ids` và chuyển sang manual input khi câu trả lời tiếp tục mơ hồ.
- Session store khóa xuyên suốt mutation để tránh race với delete/expiry.

## Rules, AI và evaluation đang tích hợp

- Giữ public contract hiện hành `ExtractionTurnContext(active_procedure_code, expected_field_id)` để
  core/API/test cùng dùng một kiểu context. Context chỉ hỗ trợ hiểu câu trả lời ngắn; evidence vẫn phải
  xuất hiện trong tin nhắn người dùng hiện tại.
- Structured extraction chỉ nhận ba procedure code đã review và mở rộng output bằng
  `context_signals`, evidence và origin tách biệt khỏi form field.
- Text extractor chỉ tạo candidate cho signal có origin `intent_extraction` hoặc
  `user_declaration`; document/derived signal phải đến từ adapter tin cậy. Rule engine kiểm type,
  origin và promotion trước khi cho signal tham gia deterministic rule.
- Evaluation bổ sung 21 case tổng hợp cho ba thủ tục, hội thoại nhiều lượt/câu ngắn, ngoài phạm vi,
  ambiguous và cách diễn đạt ba miền. Fixture có checksum và live evaluator opt-in không ghi message,
  evidence, raw output hoặc secret vào report.
- Giới hạn cần giữ rõ: core hiện chưa persist candidate/evidence, chưa ghi nhận xác nhận của người dùng
  và chưa promote trusted-adapter `context_signals`. Vì vậy phần signal mới chưa chạy end-to-end trên
  web dù contract extractor/rules đã tồn tại.

## Gate trên baseline `dev` trước merge Rules/AI

- Compileall, Ruff lint/format và Mypy strict pass.
- Pytest `166 passed, 1 skipped`, coverage `82.87%`.
- `npm ci`/audit pass với 0 vulnerability; lint, typecheck, 9 reducer test và Next production build
  25 route pass.
- Production BFF → backend manual field smoke trả 200, revision `0 → 1`, đúng `draft.values`,
  confirmed/dirty và `pack_version=2.0.0`.
- Limited staged-text audit pass: 335 index file, 190 text file; không còn conflict marker.
- Smoke dùng provider mock và dữ liệu giả; không gọi model ngoài hoặc gửi PII.
- Đây chỉ là bằng chứng của baseline `dev`. Sau khi giải quyết xong Rules/AI và OCR phải chạy lại
  targeted Rules/AI tests, full Python gate, web gate và release audit trên đúng merge result trước
  khi push.

## Việc cần làm tiếp

1. Hoàn tất conflict Rules/AI và OCR, sau đó kiểm tra không còn conflict marker hoặc file ngoài scope.
2. Chạy targeted tests cho extractor, rules và evaluator; tiếp theo chạy toàn bộ Python/npm gate trên
   merge result.
3. Thiết kế state/API nội bộ để persist, confirm và promote `context_signals`; không nhận cờ
   confirmation/trust trực tiếp từ browser client.
4. Rebuild Docker; smoke local/public URL và ghi lại image digest, model/version, timestamp.

## Blocker còn lại

1. Gate Rules/AI và OCR trên merge result chưa chạy lại.
2. Context signal mới chưa được core persist/confirm/promote nên chưa có runtime E2E.
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
