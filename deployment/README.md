# VNeGuide deployment

Thư mục này đóng gói FastAPI, Next.js và gateway thành một release baseline có thể build. API chạy
một Uvicorn worker vì session store hiện nằm trong bộ nhớ của một process. Gateway công khai một
origin duy nhất: `/health` đi tới API, các route còn lại đi tới Next.js.

> Trạng thái release: hạ tầng đã build và smoke được, nhưng frontend hợp nhất từ `tuan` vẫn hiển thị
> luồng Hôn nhân và gia đình ngoài data package. Không dùng preview này để tuyên bố sản phẩm đã đạt
> đúng ba thủ tục cho tới khi branch UI đúng scope được merge và browser E2E đạt.

## Chạy local

Yêu cầu Docker Engine/Compose. Không cần secret khi dùng mock provider:

```bash
VNEGUIDE_LLM_PROVIDER=mock VNEGUIDE_MODEL=mock-scripted \
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

Compose nhận cấu hình dev qua environment. Không ghi key vào YAML, image, shell history hoặc biến
`NEXT_PUBLIC_*`. Lệnh `read -s` dưới đây tránh đưa key vào shell history, nhưng key vẫn có thể hiện
trong `docker inspect`; production phải dùng secret manager của nền tảng thay vì Compose environment.

```bash
export VNEGUIDE_LLM_PROVIDER=litellm
export VNEGUIDE_MODEL='<model-id>'
export VNEGUIDE_LITELLM_BASE_URL='https://gateway.example'
read -rsp 'LiteLLM API key: ' VNEGUIDE_LITELLM_API_KEY && echo
export VNEGUIDE_LITELLM_API_KEY
docker compose -f deployment/docker-compose.yml up --build --detach --wait
unset VNEGUIDE_LITELLM_API_KEY
```

HTTP tới LiteLLM bị tắt mặc định. Chỉ bật `VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=1` trên mạng dev
tin cậy và chỉ dùng dữ liệu tổng hợp. Public/production phải dùng HTTPS.

## Speech-to-text với Qwen3-ASR-1.7B (phương án 1)

Ở phương án này, VPS chạy VNeGuide **chỉ làm proxy/BFF**. Trình duyệt gửi đoạn ghi âm tới route cùng
origin `POST /api/stt/transcribe`; Next.js chuyển tiếp tới một GPU service riêng có API tương thích
OpenAI tại `/v1/audio/transcriptions`. Model `Qwen/Qwen3-ASR-1.7B` không chạy trên VPS ứng dụng và
không tạo thêm port public trên VPS đó. STT mặc định tắt, không nằm trong dependency/healthcheck của
API, web hoặc gateway; lỗi hay downtime của GPU service không được làm chat văn bản mất health.

Gateway áp giới hạn riêng cho audio POST: body tối đa 10 MiB, 5 request/phút/IP với burst 2,
và tối đa một request đồng thời/IP. BFF từ chối sớm thời lượng do client khai báo trên 60 giây và
chờ provider tối đa 180 giây; gateway chờ tối đa 195 giây để BFF có thời gian trả lỗi có cấu trúc.
Không tăng giới hạn upload toàn site và không buffer toàn bộ audio xuống đĩa ở Nginx.

Header thời lượng từ browser **không phải ranh giới tin cậy**. Trước khi bật production, GPU service
hoặc ingress ngay trước Qwen phải probe media thật và từ chối audio trên 60 giây trước inference.
GPU provider cũng phải có quota theo key, giới hạn concurrency và giới hạn chi phí; rate limit theo IP
ở VPS chỉ là lớp bảo vệ đầu tiên, không chống được bot phân tán.

### Bật remote STT

GPU endpoint phải dùng HTTPS hợp lệ trong production. Tạo secret thành file ngoài repository; UID
`10001` là user không đặc quyền của web container. Không đưa key vào YAML, `.env`, biến
`NEXT_PUBLIC_*`, image hoặc command line:

Các lệnh dưới đây dành cho VPS hiện tại. Overlay `docker-compose.vps.yml` và env file dùng chung là
bắt buộc để giữ port `9000/13000/18000`, data mount và dịch vụ translator đang chạy; khi deploy sang
máy khác, thay chúng bằng overlay/secret manager tương ứng của môi trường đó.

```bash
sudo install -o 10001 -g 10001 -m 0400 /dev/null /opt/vneguide/shared/stt_api_key
sudoedit /opt/vneguide/shared/stt_api_key

export VNEGUIDE_STT_BASE_URL='https://stt-gpu.example/v1'
export VNEGUIDE_STT_API_KEY_SOURCE='/opt/vneguide/shared/stt_api_key'
export VNEGUIDE_STT_MODEL='Qwen/Qwen3-ASR-1.7B'
docker compose \
  --env-file /opt/vneguide/shared/vneguide.env \
  -f deployment/docker-compose.yml \
  -f deployment/docker-compose.vps.yml \
  -f deployment/docker-compose.stt-remote.yml \
  config --quiet
docker compose \
  --env-file /opt/vneguide/shared/vneguide.env \
  -f deployment/docker-compose.yml \
  -f deployment/docker-compose.vps.yml \
  -f deployment/docker-compose.stt-remote.yml \
  up --build --detach --wait
```

`VNEGUIDE_STT_ALLOW_INSECURE_HTTP=0` là mặc định. Chỉ đặt thành `1` khi endpoint HTTP nằm trên mạng
dev cô lập, dùng audio tổng hợp và chấp nhận rủi ro nghe lén. Microphone của trình duyệt cũng chỉ hoạt
động trong secure context: dùng HTTPS cho domain public, hoặc `localhost`/SSH tunnel khi test. Truy
cập `http://<public-ip>:<port>` không phải cách test microphone hợp lệ.

Audio và transcript có thể chứa PII. Không log request body, transcript, header Authorization hoặc
provider response; cấu hình log của reverse proxy và APM phải tuân theo nguyên tắc này. Chỉ giữ dữ
liệu tạm trong thời gian request, trừ khi đã có consent và retention policy riêng.

Kiểm tra sau khi bật:

1. `/health` và chat văn bản vẫn đạt khi GPU endpoint bị tắt hoặc timeout.
2. `GET /api/stt/transcribe` báo STT đã bật nhưng không làm lộ base URL hoặc key.
3. Một audio tiếng Việt ngắn trả transcript vào ô nhập; transcript không được tự gửi.
4. File quá 10 MiB, audio quá 60 giây và MIME không hỗ trợ bị từ chối có kiểm soát.
5. Secret không xuất hiện trong `docker compose config`, `docker inspect`, log hoặc browser bundle.
6. GPU ingress tự đo thời lượng thật, chặn audio trên 60 giây và áp quota/concurrency trước inference.

Nếu HTTPS được đặt trước gateway bằng Caddy/reverse proxy, phải áp rate limit tại proxy đó hoặc cấu
hình `real_ip` chỉ tin đúng địa chỉ proxy nội bộ. Không tin `X-Forwarded-For` trực tiếp từ Internet;
nếu không, mọi người dùng có thể bị gom vào một IP hoặc client có thể giả IP.

Rollback STT không cần rollback cả release: chạy lại base Compose mà không kèm overlay rồi xóa
container cũ của web. Chat văn bản vẫn giữ nguyên:

```bash
docker compose \
  --env-file /opt/vneguide/shared/vneguide.env \
  -f deployment/docker-compose.yml \
  -f deployment/docker-compose.vps.yml \
  up --detach --wait --remove-orphans
```

Sau khi xác nhận STT đã tắt, có thể thu hồi key ở GPU provider và xóa file secret theo quy trình vận
hành của máy chủ. Nếu rollback toàn release, dùng lại image/tag bất biến trước đó như phần “Deploy
bền vững”.

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

Audit chỉ đọc bản staged/index của một số loại UTF-8 text tối đa 2 MB và chặn common secret pattern,
private key, `.env`/log nhạy cảm, conflict marker và số định danh 12 chữ số ngoài vùng fixture tổng
hợp. Nó không scan history/binary hoặc nhận diện mọi loại PII; kết quả chỉ hỗ trợ review và không
thay thế secret scanning phía GitHub hoặc đánh giá bảo vệ dữ liệu.

## Deploy bền vững

Hai Dockerfile là contract deploy độc lập:

- API cần volume/image chứa `data/`, bind `0.0.0.0:8000`, một worker, HTTPS ở ingress và secret từ
  secret manager.
- Web cần `VNEGUIDE_API_BASE_URL` trỏ tới API nội bộ; không public model key.
- Gateway/ingress route `/health` tới API và `/` tới web.
- Dùng immutable image digest hoặc release tag; giữ tag trước đó để rollback.
- Base image được khóa digest và Python runtime dependency được khóa version trong
  `deployment/requirements-api.lock`; lock chưa có artifact hash nên không đảm bảo byte-for-byte.

Không có credential của một cloud target cụ thể trong repo. Release Captain phải ghi URL, image
digest và lệnh rollback thực tế vào `doc/operations/release-evidence.md` sau khi deploy lâu dài.
