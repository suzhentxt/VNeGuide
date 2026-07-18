# Qwen CT01 OCR worker

Module này chỉ nhận ảnh/PDF CT01 cho thủ tục `1.004194` và chỉ trả suggestion. Nó không
ghi trực tiếp vào draft/form. Core/API cần đưa từng candidate qua cùng luồng
Accept/Reject/Edit của text suggestion.

## Runtime được chọn

OCR dùng chính model `Qwen/Qwen3.5-9B` và LiteLLM Chat Completions multimodal được cấu hình
trong file `.env` của repository. Không dùng MinerU, vLLM hoặc model OCR thứ hai.

Qwen nhận ảnh JPEG đã chuẩn hóa trong memory và trả layout block có schema chặt. Mapper xác định
sau đó chỉ lấy các giá trị hiển thị rõ trên CT01 và kiểm tra chúng bằng field catalog/rule engine đã
review. Model không được quyết định required field, giấy tờ, phí, thời hạn hoặc kết luận pháp lý.

Dependency ảnh/PDF được khai báo trong extra `ocr`:

```powershell
python -m pip install -e ".[api,ocr]"
```

## Chạy worker

Không ghi worker token vào source. Đặt token ở process environment rồi đọc cấu hình model từ `.env`:

```powershell
$env:VNEGUIDE_OCR_ENABLED = "1"
$env:VNEGUIDE_OCR_WORKER_TOKEN = "<random-local-secret>"
python -m vneguide.ocr --env-file C:\Users\admin\VAIC_UET\.env `
  --host 127.0.0.1 --port 8010
```

`--env-file` chỉ nạp cấu hình LLM. Các biến `VNEGUIDE_OCR_*` phải được export vào process
environment như ví dụ trên; chỉ ghi chúng trong `.env` sẽ không bật worker.

Không bind worker ra ngoài localhost. API không có Swagger/OpenAPI và không log raw upload.

## Contract HTTP

- `GET /health`
- `POST /v1/ocr/jobs`
  - bearer token;
  - `Content-Type`: `image/jpeg`, `image/png` hoặc `application/pdf`;
  - `X-Procedure-Code: 1.004194`;
  - `X-Form-Id: CT01`;
  - body là raw bytes, tối đa 8 MiB và 2 trang.
- `GET /v1/ocr/jobs/{job_id}` để poll.

Kết quả thành công trả `field_id`, `suggested_value`, `confidence`, `evidence` và
`source=USER_UPLOAD`. Sai loại giấy tờ, model lỗi hoặc timeout trả `manual_input` và không
có candidate.

## Ranh giới dữ liệu

`.env` hiện có thể trỏ tới gateway HTTP bên ngoài máy. HTTP không mã hóa ảnh trên đường truyền.
Chỉ dùng fixture/dữ liệu giả cho tới khi gateway có HTTPS; không gửi CT01, CCCD hoặc PII thật.

Timeout hiện là timeout mềm ở biên job. Request quá hạn chuyển sang nhập tay và kết quả muộn bị bỏ,
nhưng Python thread đang chờ gateway chỉ kết thúc khi HTTP call trả về. Worker chạy như process riêng
để có thể restart khi cần.

## Smoke và metric

Lệnh sau chỉ gửi ảnh CT01 tổng hợp được tạo trong memory; không đọc ảnh người dùng:

```powershell
python -m vneguide.ocr.smoke --env-file .env --runs 3 --confirm-live
```

Lệnh trả exit code `1` nếu không nhận đúng toàn bộ 4 field ở mọi lượt. Kết quả thực đo ngày
2026-07-18 với `Qwen/Qwen3.5-9B`: field recall `0.75` (9/12), latency trung bình `6,688 giây`,
lớn nhất `8,407 giây`; cả ba lượt nhận đúng loại CT01 nhưng mỗi lượt thiếu một field. Đây là baseline
thật, chưa phải cam kết accuracy production.

Eval adapter không gọi model nằm ở `tests/evals/test_ocr_ct01_acceptance.py`; nó kiểm tra clear,
blurred, rotated và wrong-document fixture, field precision/recall cùng latency mapper.

Chạy toàn bộ test OCR, gồm raster ảnh/PDF:

```powershell
python -m pip install -e ".[api,dev,ocr]"
python -m pytest tests/unit/test_ocr*.py tests/evals/test_ocr_ct01_acceptance.py
```

## Điểm nối tích hợp

`OcrCandidateSink` là port bàn giao cho Core/API. Consumer phải chuyển candidate sang suggestion
`pending` với revision guard rồi mới dùng Accept/Reject/Edit. Adapter OCR không có method ghi draft,
vì vậy nhánh Người 4 không tạo đường auto-commit và không sửa `core`, `api` hay `demoweb`.
