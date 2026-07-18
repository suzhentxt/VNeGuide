# OCR kiểm tra tài liệu Đăng ký tạm trú

Đây là OCR duy nhất của VNeGuide. Worker chỉ kiểm tra nhẹ hai nhóm tài liệu tổng hợp/đã ẩn danh
cho thủ tục `1.004194`:

- `legal_dwelling`: giấy tờ chứng minh chỗ ở hợp pháp khi CSDL không khai thác được;
- `minor_consent`: ý kiến đồng ý của cha, mẹ hoặc người giám hộ.

OCR không xác minh chữ ký, danh tính, quyền sở hữu hay giá trị pháp lý. Kết quả chỉ là `pass`,
`needs_review` hoặc `fail`; không có raw text và không tự điền draft.

`pass` yêu cầu confidence tổng thể và từng tiêu chí bắt buộc đều đạt ít nhất `0.80`. Web chỉ trình bày
hai kết quả cuối cho người dùng: `Không hợp lệ` khi không đạt/nghi ngờ/lỗi, hoặc
`Hợp lệ, tài liệu sẽ cần kiểm tra chính thức` khi đạt ngưỡng nghiêm ngặt. Chỉ kết quả thứ hai mở gate.

## Chạy local

```powershell
python -m vneguide.ocr --host 127.0.0.1 --port 8010 --env-file .env
```

Frontend cần cùng worker token ở phía server:

```text
VNEGUIDE_OCR_BASE_URL=http://127.0.0.1:8010
VNEGUIDE_OCR_WORKER_TOKEN=<random-local-token>
```

Không đặt key hoặc worker token trong biến `NEXT_PUBLIC_*`.

## HTTP contract

- `GET /health`
- `POST /v1/ocr/jobs`
  - bearer worker token;
  - `X-Procedure-Code: 1.004194`;
  - `X-Document-Kind: legal_dwelling` hoặc `minor_consent`;
  - raw JPEG, PNG hoặc PDF; tối đa 8 MiB, 2 trang và 20 MP.
- `GET /v1/ocr/jobs/{job_id}` để poll.

Worker đọc upload theo stream và dừng khi vượt giới hạn. Ảnh được chuẩn hóa trong memory, gửi tới
OpenAI Responses API với `store: false`, rồi bị giải phóng. Không log upload, base64, prompt hoặc
model response.

## Tài liệu test thủ công

Upload hai file tổng hợp:

- `tests/fixtures/ocr/demo_documents/legal_dwelling_demo.png`
- `tests/fixtures/ocr/demo_documents/minor_consent_demo.png`

Sinh lại fixture bằng:

```powershell
python tests/fixtures/ocr/generate_demo_documents.py
```

Chạy test OCR:

```powershell
python -m pytest tests/unit/test_ocr*.py
```
