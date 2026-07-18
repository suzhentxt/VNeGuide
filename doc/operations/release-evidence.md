# Release evidence

Các QA case và smoke input được ghi ở đây đều dùng fixture tổng hợp. Limited pattern scan không đủ để
chứng minh toàn bộ repository/history không chứa PII thật.

## Snapshot 2026-07-18

| Hạng mục | Lệnh/bằng chứng | Kết quả |
| --- | --- | --- |
| Python install | `python -m pip install -e ".[api,dev]"` | Đạt trên Python 3.11.14 |
| Python gate | Ruff lint/format, Mypy, Pytest, coverage | Pass; 106 pass, 1 skip; coverage 81.93% |
| Python formatter | `ruff format --check src tests deployment` | Pass: 65 file formatted; owner fix nhận từ `e65b31b` |
| Release API integration | `pytest -q tests/integration/test_release_flows.py` | 12 pass; đúng ba mã, out-of-scope, hero 5/5, stale/reset/typed timeout/generic OCR fallback |
| Web install | `cd demoweb && npm ci` | Đạt bằng npm 11.6.2 và npm 11.16.0 trong Node 24 container |
| Dependency audit | `npm audit --audit-level=moderate` | 0 vulnerability sau khi nâng Next/shadcn và override PostCSS 8.5.16 |
| Web gate | `npm run check` | ESLint, TypeScript và Next production build đạt; 29 page |
| Container | `docker compose -f deployment/docker-compose.yml up --build --detach --wait` | API, web và gateway build/start/healthy; env files bị loại khỏi context; API runtime version-locked |
| Limited staged-text audit | `python deployment/scripts/release_audit.py` | Pass: 335 index file, 190 text file; không scan history/binary hoặc mọi loại PII |

## Deterministic acceptance

Backend/data có đúng ba procedure code: `2.000635`, `1.013314`, `1.004194`. Hero đăng ký tạm trú
được chạy độc lập năm lần và đạt 5/5; mỗi lượt kiểm năm checkpoint:

1. Tạo session với context `1.004194`.
2. Scripted extractor fixture tạo suggestion nhưng chưa tự ghi draft.
3. Edit suggestion tăng revision và đánh dấu dirty field.
4. Accept toàn bộ suggestion theo revision đã rebase.
5. Validation đạt `ready_to_submit`, sau đó reset làm session cũ trả 404.

Đây là API integration in-process bằng scripted extractor; không chạy Next/browser và không phải
bằng chứng live-model accuracy. Provider timeout đi qua `StructuredExtractor` và typed
`ProviderTimeout`. OCR chỉ đưa generic upstream failure `ocr_unreadable` tại integration boundary;
repo chưa có OCR upload/adapter nên chưa thể gọi đây là OCR E2E.

## Local gateway metrics

Timestamp UTC: `2026-07-18T08:50:23.102344+00:00`; base revision `44d399f0f421`, tracked tree clean,
không có staged diff; package `0.1.0`; provider/model label `mock/mock-scripted`; 5 mẫu mỗi endpoint.
Runtime container được kiểm tra riêng và khớp `mock/mock-scripted`, nhưng smoke không gọi model nên
đây không phải bằng chứng model connectivity hay accuracy.
Web probe yêu cầu HTML có marker `Bản mô phỏng Hackathon` và từ chối redirect khác origin.

| Endpoint | Success | Median | p95 |
| --- | ---: | ---: | ---: |
| `http://127.0.0.1:8080/health` | 5/5 HTTP 200 | 3.50 ms | 8.44 ms |
| `http://127.0.0.1:8080/` | 5/5 HTTP 200 | 4.97 ms | 20.12 ms |

## Public preview metrics

URL tạm thời: `https://moschate-terri-dereistically.ngrok-free.dev`. URL chỉ hoạt động khi ngrok và
Docker trên máy release còn chạy; đây không phải hosting bền vững.

Timestamp UTC: `2026-07-18T08:50:28.004246+00:00`; base revision `44d399f0f421`, tracked tree clean,
không có staged diff; package `0.1.0`; provider/model label `mock/mock-scripted`; 5 mẫu mỗi endpoint;
smoke không gọi model.

| Endpoint | Success | Median | p95 |
| --- | ---: | ---: | ---: |
| `/health` | 5/5 HTTP 200 | 277.84 ms | 326.07 ms |
| `/` | 5/5 HTTP 200 | 461.02 ms | 729.74 ms |

Image provenance của lần smoke:

- API `vneguide-api:latest`: `sha256:c72a78e6a5b53af4c584ebef2a277ffcf04665af45328982c7430f9772519e4f`.
- Web `vneguide-web:latest`: `sha256:b87a68c910cf52ee2006cc57e2c377365276902979da35e187937223f3bfc0b7`.

## Blocker không được che

- Next route manifest vẫn chỉ có `/hon-nhan-va-gia-dinh/**` và các mã ngoài scope. Public URL hoạt
  động về hạ tầng nhưng chưa đạt tiêu chí sản phẩm “đúng ba thủ tục”.
- API chưa trả `draft.values`/`pack_version`; chưa test được manual edit trực tiếp trên form qua wire.
- OCR adapter/upload/UI chưa có ở bất kỳ branch hiện thấy; chỉ test generic fallback.
- Retry web 404/410 đã compile/build nhưng chưa có component/browser test hành vi; gateway timeout
  có margin 75/60 giây nhưng chưa có delayed-response E2E.
- Không có browser tab trong phiên nên chưa chụp screenshot/video. Video backup chỉ có runbook và
  phải được record lại sau khi UI đúng scope được merge.
- Không có cloud credential/target để tạo URL lâu dài; ngrok URL là preview tạm thời.

## Render API candidate 2026-07-18

| Hạng mục | Bằng chứng | Kết quả |
| --- | --- | --- |
| Blueprint | Ruby/Psych parse `render.yaml` | Pass; secret chỉ có tên, `sync: false` |
| API targeted | `pytest` API main/store/chat/form sync | `29 passed` |
| Docker build | `docker build -f deployment/api.Dockerfile -t vneguide-api:render-test .` | Pass; manifest list `sha256:4e51b133bd7015466376f038d9ca0865cc64bed272bce965985390c3483d5dec` |
| Container health | `GET http://127.0.0.1:18001/health` | `200 {"status":"ok"}` |

Đây mới là deploy candidate local, chưa phải Render evidence. Chưa có service ID, public URL, deploy
ID hoặc Render image digest vì phiên không có Render credential/dashboard. Không ghi API key vào
report; live-model smoke chỉ chạy sau khi secret được nhập trong Render secret manager.
