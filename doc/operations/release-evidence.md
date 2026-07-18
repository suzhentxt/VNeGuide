# Release evidence

Tài liệu này chỉ ghi bằng chứng đã chạy. Dữ liệu đầu vào đều là fixture tổng hợp; không có PII thật.

## Snapshot 2026-07-18

| Hạng mục | Lệnh/bằng chứng | Kết quả |
| --- | --- | --- |
| Python install | `python -m pip install -e ".[api,dev]"` | Đạt trên Python 3.11.14 |
| Python gate | Ruff lint, Mypy, Pytest, coverage | Lint/type pass; 103 pass, 1 skip; coverage 81.60% |
| Python formatter | `ruff format --check src tests deployment` | Còn fail tại `src/vneguide/api/session_store.py` ngoài ownership Người 5 |
| Release API integration | `pytest -q tests/integration/test_release_flows.py` | 12 pass; đúng ba mã, out-of-scope, hero 5/5, stale/reset/typed timeout/generic OCR fallback |
| Web install | `cd demoweb && npm ci` | Đạt bằng npm 11.6.2 và npm 11.16.0 trong Node 24 container |
| Dependency audit | `npm audit --audit-level=moderate` | 0 vulnerability sau khi nâng Next/shadcn và override PostCSS 8.5.16 |
| Web gate | `npm run check` | ESLint, TypeScript và Next production build đạt; 29 page |
| Container | `docker compose -f deployment/docker-compose.yml up --build --detach --wait` | API, web và gateway build/start/healthy |
| Limited staged-text audit | `python deployment/scripts/release_audit.py` | Pass: 333 index file, 188 text file; không scan history/binary hoặc mọi loại PII |

## Deterministic acceptance

Backend/data có đúng ba procedure code: `2.000635`, `1.013314`, `1.004194`. Hero đăng ký tạm trú
được chạy độc lập năm lần và đạt 5/5; mỗi lượt kiểm năm checkpoint:

1. Tạo session với context `1.004194`.
2. Structured extraction tạo suggestion nhưng chưa tự ghi draft.
3. Edit suggestion tăng revision và đánh dấu dirty field.
4. Accept toàn bộ suggestion theo revision đã rebase.
5. Validation đạt `ready_to_submit`, sau đó reset làm session cũ trả 404.

Đây là API integration in-process bằng scripted extractor; không chạy Next/browser và không phải
bằng chứng live-model accuracy. Provider timeout đi qua `StructuredExtractor` và typed
`ProviderTimeout`. OCR chỉ đưa generic upstream failure `ocr_unreadable` tại integration boundary;
repo chưa có OCR upload/adapter nên chưa thể gọi đây là OCR E2E.

## Local gateway metrics

Timestamp UTC: `2026-07-18T08:35:44.176021+00:00`; base revision `ff06998752d4`, tracked tree dirty
do staged release changes; package `0.1.0`; provider/model label `mock/mock-scripted`; 5 mẫu mỗi
endpoint. Smoke không gọi model nên label không phải bằng chứng model connectivity hay accuracy.
Web probe yêu cầu HTML có marker `Bản mô phỏng Hackathon` và từ chối redirect khác origin.

| Endpoint | Success | Median | p95 |
| --- | ---: | ---: | ---: |
| `http://127.0.0.1:8080/health` | 5/5 HTTP 200 | 2.94 ms | 11.68 ms |
| `http://127.0.0.1:8080/` | 5/5 HTTP 200 | 6.28 ms | 12.93 ms |

## Public preview metrics

URL tạm thời: `https://moschate-terri-dereistically.ngrok-free.dev`. URL chỉ hoạt động khi ngrok và
Docker trên máy release còn chạy; đây không phải hosting bền vững.

Timestamp UTC: `2026-07-18T08:35:45.553122+00:00`; base revision `ff06998752d4`, tracked tree dirty
do staged release changes; package `0.1.0`; provider/model label `mock/mock-scripted`; 5 mẫu mỗi
endpoint; smoke không gọi model.

| Endpoint | Success | Median | p95 |
| --- | ---: | ---: | ---: |
| `/health` | 5/5 HTTP 200 | 270.57 ms | 351.28 ms |
| `/` | 5/5 HTTP 200 | 440.32 ms | 469.29 ms |

Image provenance của lần smoke:

- API `vneguide-api:latest`: `sha256:a3e4771015bf77a044d0c6754e96d49b36e4100fe531575fc416c29edb20a092`.
- Web `vneguide-web:latest`: `sha256:e8b84b8ea57dbd3e4a00dce2ad795a2e31a2c7477381d4da8c5f8b387f31ed1a`.

## Blocker không được che

- Next route manifest vẫn chỉ có `/hon-nhan-va-gia-dinh/**` và các mã ngoài scope. Public URL hoạt
  động về hạ tầng nhưng chưa đạt tiêu chí sản phẩm “đúng ba thủ tục”.
- API chưa trả `draft.values`/`pack_version`; chưa test được manual edit trực tiếp trên form qua wire.
- OCR adapter/upload/UI chưa có ở bất kỳ branch hiện thấy; chỉ test generic fallback.
- Không có browser tab trong phiên nên chưa chụp screenshot/video. Video backup chỉ có runbook và
  phải được record lại sau khi UI đúng scope được merge.
- Không có cloud credential/target để tạo URL lâu dài; ngrok URL là preview tạm thời.
