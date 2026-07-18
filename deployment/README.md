# VNeGuide deployment

Thư mục này đóng gói FastAPI, Next.js và gateway thành một release stack có thể tái lập. API chạy
một Uvicorn worker vì session store hiện nằm trong bộ nhớ của một process. Gateway công khai một
origin duy nhất: `/health` đi tới API, các route còn lại đi tới Next.js.

> Trạng thái release: hạ tầng đã build và smoke được, nhưng frontend hợp nhất từ `tuan` vẫn hiển thị
> luồng Hôn nhân và gia đình ngoài data package. Không dùng preview này để tuyên bố sản phẩm đã đạt
> đúng ba thủ tục cho tới khi branch UI đúng scope được merge và browser E2E đạt.

## Chạy local

Yêu cầu Docker Engine/Compose. Không cần secret khi dùng mock provider:

```bash
docker compose -f deployment/docker-compose.yml up --build --detach --wait
python deployment/scripts/smoke.py \
  --api-url http://127.0.0.1:8080 \
  --web-url http://127.0.0.1:8080 \
  --provider mock \
  --model mock-scripted
```

Các endpoint local:

- `http://127.0.0.1:8080`: gateway dùng cho demo và smoke.
- `http://127.0.0.1:8080/health`: health API qua gateway.
- `http://127.0.0.1:8000`: API trực tiếp, chỉ cần khi debug.
- `http://127.0.0.1:3000`: Next.js trực tiếp, chỉ cần khi debug.

Dừng stack:

```bash
docker compose -f deployment/docker-compose.yml down
```

## Cấu hình model

Compose nhận cấu hình qua environment. Không ghi key vào YAML, image, shell history hoặc biến
`NEXT_PUBLIC_*`.

```bash
export VNEGUIDE_LLM_PROVIDER=litellm
export VNEGUIDE_MODEL='<model-id>'
export VNEGUIDE_LITELLM_BASE_URL='https://gateway.example'
export VNEGUIDE_LITELLM_API_KEY='<secret>'
docker compose -f deployment/docker-compose.yml up --build --detach --wait
```

HTTP tới LiteLLM bị tắt mặc định. Chỉ bật `VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1` trên mạng dev
tin cậy và chỉ dùng dữ liệu tổng hợp. Public/production phải dùng HTTPS.

## Public preview bằng ngrok

Preview này phụ thuộc máy chạy Docker và không thay thế hosting bền vững:

```bash
ngrok start --all \
  --config "$HOME/Library/Application Support/ngrok/ngrok.yml" \
  --config deployment/ngrok.example.yml
```

Lấy URL HTTPS từ output ngrok rồi chạy:

```bash
python deployment/scripts/smoke.py \
  --api-url https://<preview-host> \
  --web-url https://<preview-host> \
  --samples 5 \
  --provider mock \
  --model mock-scripted
```

Report ghi timestamp UTC, base Git revision và trạng thái dirty, package version, provider/model label,
số mẫu, HTTP status và latency min/median/p95/max. Smoke chỉ gọi `/health` và web marker, không gọi
model; label không chứng minh model connectivity/accuracy. Không đưa prompt, response, API key hoặc
PII vào report.

## Quality và security

```bash
python deployment/scripts/release_audit.py
cd demoweb
npm audit --audit-level=moderate
```

Audit chỉ đọc file Git theo dõi và chặn secret pattern phổ biến, private key, `.env`/log nhạy cảm,
conflict marker và số định danh 12 chữ số ngoài vùng fixture tổng hợp. Kết quả scan hỗ trợ review,
không thay thế secret scanning phía GitHub hoặc đánh giá bảo vệ dữ liệu.

## Deploy bền vững

Hai Dockerfile là contract deploy độc lập:

- API cần volume/image chứa `data/`, bind `0.0.0.0:8000`, một worker, HTTPS ở ingress và secret từ
  secret manager.
- Web cần `VNEGUIDE_API_BASE_URL` trỏ tới API nội bộ; không public model key.
- Gateway/ingress route `/health` tới API và `/` tới web.
- Dùng immutable image digest hoặc release tag; giữ tag trước đó để rollback.

Không có credential của một cloud target cụ thể trong repo. Release Captain phải ghi URL, image
digest và lệnh rollback thực tế vào `doc/operations/release-evidence.md` sau khi deploy lâu dài.
