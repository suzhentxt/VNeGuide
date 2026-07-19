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

Các lệnh dưới đây dành cho VPS hiện tại. Overlay tracked `docker-compose.vps.yml` khóa API/web/gateway
lần lượt ở `127.0.0.1:18000`, `127.0.0.1:13000` và `0.0.0.0:9000`, đồng thời giữ data mount chỉ đọc
và shared Nginx config. Luôn ghép Compose theo đúng thứ tự `base -> VPS -> STT`; không chạy riêng base
Compose vì port `8000` đang thuộc translator.

Giữ cấu hình STT không bí mật trong một env file riêng, root-owned. Việc tách file này khỏi
`vneguide.env` giúp rollback chắc chắn đưa `VNEGUIDE_STT_ENABLED` về mặc định `0`:

```bash
sudo install -o root -g root -m 0600 /dev/null /opt/vneguide/shared/stt.env
sudoedit /opt/vneguide/shared/stt.env
```

Nội dung `/opt/vneguide/shared/stt.env`:

```dotenv
VNEGUIDE_STT_ENABLED=1
VNEGUIDE_STT_BASE_URL=https://stt-gpu.example/v1
VNEGUIDE_STT_MODEL=Qwen/Qwen3-ASR-1.7B
VNEGUIDE_STT_LANGUAGE=
VNEGUIDE_STT_PROMPT=
VNEGUIDE_STT_API_KEY_SOURCE=/opt/vneguide/shared/stt_api_key
VNEGUIDE_STT_ALLOW_INSECURE_HTTP=0
VNEGUIDE_STT_TIMEOUT_SECONDS=180
VNEGUIDE_STT_MAX_BYTES=10485760
VNEGUIDE_STT_MAX_DURATION_SECONDS=60
```

Với OpenAI transcription, thay ba dòng provider bằng cấu hình sau; `vi` là mã ISO-639-1 và được gửi
server-side để giảm độ trễ/nhầm ngôn ngữ:

```dotenv
VNEGUIDE_STT_BASE_URL=https://api.openai.com/v1
VNEGUIDE_STT_MODEL=gpt-4o-mini-transcribe
VNEGUIDE_STT_LANGUAGE=vi
VNEGUIDE_STT_PROMPT=Nội dung là tiếng Việt về thủ tục hành chính Việt Nam. Hãy chép lại nguyên văn bằng tiếng Việt có dấu; giữ nguyên tên riêng, mã thủ tục và thuật ngữ; không dịch sang ngôn ngữ khác.
```

API key nằm trong file riêng, không nằm trong `stt.env`. Giữ owner số `10001` vì Compose file-secret
được bind vào container chạy bằng UID đó:

```bash
sudo install -o 10001 -g 10001 -m 0400 /dev/null /opt/vneguide/shared/stt_api_key
sudoedit /opt/vneguide/shared/stt_api_key
sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' /opt/vneguide/shared/stt_api_key
sudo test -s /opt/vneguide/shared/stt_api_key
```

### Preflight và kích hoạt trên VPS hiện tại

Chạy từ release mà symlink `current` đang trỏ tới. Dùng `sudo docker compose` vì user vận hành không
có quyền trực tiếp với Docker socket:

```bash
cd "$(readlink -f /opt/vneguide/current)"

COMPOSE=(
  sudo docker compose
  --env-file /opt/vneguide/shared/vneguide.env
  --env-file /opt/vneguide/shared/stt.env
  -f deployment/docker-compose.yml
  -f deployment/docker-compose.vps.yml
  -f deployment/docker-compose.stt-remote.yml
)

"${COMPOSE[@]}" config --quiet
sudo docker exec vneguide-gateway-1 nginx -t
sudo ss -ltnp | grep -E ':(8000|9000|13000|18000)([[:space:]]|$)'
curl -fsS http://127.0.0.1:9000/health

TRANSLATOR_ID_BEFORE="$(
  sudo docker inspect -f '{{.Id}}' vn-en-translator-translator-1
)"
CADDY_ID_BEFORE="$(
  sudo docker inspect -f '{{.Id}}' vn-en-translator-caddy-1
)"
```

App-side STT đã nằm trong web image của release này. Chỉ recreate `web`; không build lại, không kéo
theo dependency và không chạy `down`/`remove-orphans`:

```bash
"${COMPOSE[@]}" up \
  --detach \
  --no-deps \
  --no-build \
  --force-recreate \
  --wait \
  --wait-timeout 200 \
  web

curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1:9000/api/stt/transcribe
test "$TRANSLATOR_ID_BEFORE" = "$(
  sudo docker inspect -f '{{.Id}}' vn-en-translator-translator-1
)"
test "$CADDY_ID_BEFORE" = "$(
  sudo docker inspect -f '{{.Id}}' vn-en-translator-caddy-1
)"
```

Status STT phải đổi thành `enabled=true`; hai phép `test` cuối phải thoát `0`, chứng minh translator và
Caddy không bị recreate. Sau đó chỉ dùng audio tiếng Việt tổng hợp, không PII, để thử transcription.

### Demo microphone riêng qua SSH tunnel

Khi chưa có domain HTTPS, chạy lệnh sau trên máy người kiểm thử rồi mở `http://localhost:19000`.
`localhost` là secure context được browser cho phép dùng microphone; không cần mở port `9000` ở cloud
firewall cho máy người kiểm thử:

```bash
ssh -N \
  -p 22 \
  -i <private-key> \
  -L 19000:127.0.0.1:9000 \
  aiadmin@85.211.245.209
```

Caddy của translator hiện giữ port `80/443` và dùng TLS nội bộ cho địa chỉ IP. Không sửa/recreate
Caddy, không bind thêm service vào `443`, và không trỏ VNeGuide qua Caddy cho tới khi có hostname mới,
DNS/certificate hợp lệ cùng kế hoạch edge-network/trusted-proxy rõ ràng. Khi có kế hoạch đó, phải giữ
route translator hiện tại và kiểm tra lại `X-Forwarded-Proto`, secure cookie, real client IP và rate
limit ở edge.

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
4. File quá 10 MiB, audio quá 60 giây, media không đọc được và MIME không hỗ trợ bị từ chối có kiểm
   soát; thời lượng phải được đo từ chính media thay vì tin header của browser.
5. Secret không xuất hiện trong `docker compose config`, `docker inspect`, log hoặc browser bundle.
6. BFF tự đo thời lượng thật trước khi gọi provider; GPU ingress tự quản lý quota/concurrency trước
   inference nếu dùng provider tự host.

Nếu HTTPS được đặt trước gateway bằng Caddy/reverse proxy, phải áp rate limit tại proxy đó hoặc cấu
hình `real_ip` chỉ tin đúng địa chỉ proxy nội bộ. Không tin `X-Forwarded-For` trực tiếp từ Internet;
nếu không, mọi người dùng có thể bị gom vào một IP hoặc client có thể giả IP.

Rollback STT không cần rollback cả release. Bỏ cả STT overlay lẫn `stt.env`, giữ VPS overlay và chỉ
recreate `web`; API, gateway, translator và Caddy tiếp tục chạy:

```bash
BASE=(
  sudo docker compose
  --env-file /opt/vneguide/shared/vneguide.env
  -f deployment/docker-compose.yml
  -f deployment/docker-compose.vps.yml
)

"${BASE[@]}" config --quiet
"${BASE[@]}" up \
  --detach \
  --no-deps \
  --no-build \
  --force-recreate \
  --wait \
  --wait-timeout 120 \
  web

curl -fsS http://127.0.0.1:9000/api/stt/transcribe
```

Status phải trở lại `enabled=false`. Chỉ sau đó mới thu hồi key ở GPU provider và xử lý file secret
theo quy trình vận hành của máy chủ. Nếu rollback toàn release, dùng lại image/tag bất biến trước đó
như phần “Deploy bền vững”.

## Text-to-speech tiếng Việt qua provider từ xa

TTS chạy trong Next.js BFF, không thêm service hoặc port. Trình duyệt gọi cùng origin
`POST /api/tts/speech` với đúng JSON `{ "assistant_index": 0, "segment_index": 0 }`; BFF dùng cookie phiên
hiện tại để lấy lại tin nhắn `assistant`, chia đoạn ở server rồi mới gọi endpoint tương thích OpenAI
`/v1/audio/speech`. Client không được gửi văn bản tùy ý tới provider và transcript người dùng không phải
nguồn TTS. Trước lần phát đầu tiên trong mỗi tab, UI phải xin xác nhận vì câu trả lời có thể chứa thông tin
cá nhân và sẽ được gửi tới provider; bấm hủy thì không có request TTS. GET cùng route chỉ trả trạng thái
bật/tắt, không làm lộ provider hay secret.

Tiếng Việt được xác định bởi nội dung assistant và `VNEGUIDE_TTS_INSTRUCTIONS`; Speech API không dùng biến
`language=vi` như STT. Cấu hình mặc định đọc rõ, tự nhiên, giữ nguyên tên riêng, mã thủ tục và số liệu. UI phải
thông báo “Giọng đọc do AI tạo”, không autoplay và chỉ phát khi người dùng chủ động bấm nút nghe.

Gateway chỉ áp giới hạn tại exact route TTS: JSON tối đa 8 KiB, 10 POST/phút/IP với burst 3, một request
đồng thời/IP và chờ BFF tối đa 130 giây. GET trạng thái không tiêu thụ quota POST. BFF giới hạn mỗi MP3 ở
8 MiB; Nginx chuyển tiếp response mà không buffer xuống đĩa. TTS mặc định tắt và không tham gia healthcheck; provider lỗi không được làm
chat văn bản hoặc STT mất health.

### Tạo cấu hình và secret TTS riêng

TTS phải có env file và secret file riêng, không trỏ trực tiếp vào file STT/LLM. Production nên cấp một
credential riêng để theo dõi quota và thu hồi độc lập. Tạo env file chỉ chứa cấu hình không bí mật:

```bash
sudo install -o root -g root -m 0600 /dev/null /opt/vneguide/shared/tts.env
sudoedit /opt/vneguide/shared/tts.env
```

Nội dung `/opt/vneguide/shared/tts.env` cho tiếng Việt:

```dotenv
VNEGUIDE_TTS_ENABLED=1
VNEGUIDE_TTS_BASE_URL=https://api.openai.com/v1
VNEGUIDE_TTS_MODEL=gpt-4o-mini-tts
VNEGUIDE_TTS_VOICE=marin
VNEGUIDE_TTS_INSTRUCTIONS=Nói tiếng Việt tự nhiên, rõ ràng, với nhịp độ vừa phải. Giữ nguyên tên riêng, mã thủ tục và số liệu.
VNEGUIDE_TTS_FORMAT=mp3
VNEGUIDE_TTS_SPEED=1
VNEGUIDE_TTS_API_KEY_SOURCE=/opt/vneguide/shared/tts_api_key
VNEGUIDE_TTS_ALLOW_INSECURE_HTTP=0
VNEGUIDE_TTS_TIMEOUT_SECONDS=60
VNEGUIDE_TTS_MAX_MESSAGE_CHARACTERS=4000
VNEGUIDE_TTS_SEGMENT_CHARACTERS=600
VNEGUIDE_TTS_MAX_RESPONSE_BYTES=8388608
```

Tạo file key ngoài repository. UID/GID `10001` khớp user không đặc quyền của web container; Compose mount
file read-only với mode `0400` tại `/run/secrets/vneguide_tts_api_key`:

```bash
sudo install -o 10001 -g 10001 -m 0400 /dev/null /opt/vneguide/shared/tts_api_key
sudoedit /opt/vneguide/shared/tts_api_key
sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' /opt/vneguide/shared/tts_api_key
sudo test -s /opt/vneguide/shared/tts_api_key
```

Production giữ `VNEGUIDE_TTS_ALLOW_INSECURE_HTTP=0`. Chỉ bật HTTP cho provider dev trên mạng cô lập với
dữ liệu tổng hợp. Không log nội dung tin nhắn, audio, Authorization, key hoặc raw provider response.

### Kích hoạt mà không đổi port hoặc service khác

Trên VPS hiện tại, ghép Compose đúng thứ tự `base -> VPS -> STT -> TTS`. TTS là overlay cuối để chỉ bổ sung
environment/secret cho `web`; nó không khai báo `ports`. Nếu một môi trường không dùng STT, bỏ đồng thời
`stt.env` và overlay STT, nhưng thứ tự các overlay còn lại không đổi.

```bash
cd "$(readlink -f /opt/vneguide/current)"

COMPOSE=(
  sudo docker compose
  --env-file /opt/vneguide/shared/vneguide.env
  --env-file /opt/vneguide/shared/stt.env
  --env-file /opt/vneguide/shared/tts.env
  -f deployment/docker-compose.yml
  -f deployment/docker-compose.vps.yml
  -f deployment/docker-compose.stt-remote.yml
  -f deployment/docker-compose.tts-remote.yml
)

"${COMPOSE[@]}" config --quiet
sudo docker exec vneguide-gateway-1 nginx -t
sudo ss -ltnp | grep -E ':(80|443|8000|9000|13000|18000)([[:space:]]|$)'
curl -fsS http://127.0.0.1:9000/health

TRANSLATOR_ID_BEFORE="$(sudo docker inspect -f '{{.Id}}' vn-en-translator-translator-1)"
CADDY_ID_BEFORE="$(sudo docker inspect -f '{{.Id}}' vn-en-translator-caddy-1)"
GATEWAY_ID_BEFORE="$(sudo docker inspect -f '{{.Id}}' vneguide-gateway-1)"
```

Backup shared Nginx config rồi cập nhật **cùng file bind-mount**; không recreate gateway. Backup gốc không
được ghi đè khi chạy lại. Nếu config mới không hợp lệ, khôi phục backup trước khi tiếp tục:

```bash
if ! sudo test -e /opt/vneguide/shared/nginx-http.conf.before-tts; then
  sudo cp -p \
    /opt/vneguide/shared/nginx-http.conf \
    /opt/vneguide/shared/nginx-http.conf.before-tts
fi
sudo cp deployment/nginx.conf /opt/vneguide/shared/nginx-http.conf

if ! sudo docker exec vneguide-gateway-1 nginx -t; then
  sudo cp \
    /opt/vneguide/shared/nginx-http.conf.before-tts \
    /opt/vneguide/shared/nginx-http.conf
  exit 1
fi
sudo docker exec vneguide-gateway-1 nginx -s reload
```

Web image của release phải đã chứa app-side TTS. Chỉ recreate `web`; không dùng `down`, không pull/build và
không kéo dependency:

```bash
"${COMPOSE[@]}" up \
  --detach \
  --no-deps \
  --no-build \
  --force-recreate \
  --wait \
  --wait-timeout 120 \
  web

curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1:9000/api/stt/transcribe
curl -fsS http://127.0.0.1:9000/api/tts/speech
test "$TRANSLATOR_ID_BEFORE" = "$(sudo docker inspect -f '{{.Id}}' vn-en-translator-translator-1)"
test "$CADDY_ID_BEFORE" = "$(sudo docker inspect -f '{{.Id}}' vn-en-translator-caddy-1)"
test "$GATEWAY_ID_BEFORE" = "$(sudo docker inspect -f '{{.Id}}' vneguide-gateway-1)"
sudo ss -ltnp | grep -E ':(80|443|8000|9000|13000|18000)([[:space:]]|$)'
```

Status TTS phải báo `enabled=true`; STT và health vẫn đạt. Ba container ID phải giữ nguyên, chứng minh chỉ
web được recreate và gateway chỉ reload tại chỗ. Kiểm thử bằng một câu assistant tiếng Việt tổng hợp không
có PII; xác minh MP3 phát được, pause/resume/stop hoạt động, bắt đầu STT dừng TTS và mỗi thời điểm chỉ có một
audio. Không dùng transcript/hồ sơ thật qua gateway HTTP.

### Rollback TTS độc lập

Bỏ cả `tts.env` lẫn overlay TTS để default trong base đưa TTS về `enabled=false`; vẫn giữ STT. Chỉ recreate
web, sau đó khôi phục shared Nginx config và reload gateway tại chỗ:

```bash
WITHOUT_TTS=(
  sudo docker compose
  --env-file /opt/vneguide/shared/vneguide.env
  --env-file /opt/vneguide/shared/stt.env
  -f deployment/docker-compose.yml
  -f deployment/docker-compose.vps.yml
  -f deployment/docker-compose.stt-remote.yml
)

"${WITHOUT_TTS[@]}" config --quiet
"${WITHOUT_TTS[@]}" up \
  --detach \
  --no-deps \
  --no-build \
  --force-recreate \
  --wait \
  --wait-timeout 120 \
  web

sudo cp \
  /opt/vneguide/shared/nginx-http.conf.before-tts \
  /opt/vneguide/shared/nginx-http.conf
sudo docker exec vneguide-gateway-1 nginx -t
sudo docker exec vneguide-gateway-1 nginx -s reload

curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1:9000/api/stt/transcribe
curl -fsS http://127.0.0.1:9000/api/tts/speech
```

TTS phải trở lại `enabled=false`, trong khi STT và chat văn bản vẫn hoạt động. Nếu lỗi nằm trong web image
chứ không phải feature flag, pin lại image/tag web bất biến trước TTS rồi chạy lại đúng lệnh `up ... web`;
không rollback API, gateway, translator hoặc Caddy. Chỉ thu hồi key TTS sau khi rollback đã được xác minh.

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
