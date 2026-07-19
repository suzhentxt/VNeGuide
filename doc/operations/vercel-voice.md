# Vercel web + VPS voice deployment

This profile keeps the existing production split intact:

```text
Browser
  -> Vercel Next.js BFF /api/stt/transcribe
  -> HTTPS voice adapter on the VPS /v1/audio/transcriptions
  -> private Qwen3-ASR service

Browser
  -> Vercel Next.js BFF /api/tts/speech
  -> OpenAI TTS over HTTPS

Browser
  -> Vercel Next.js BFF /api/chat/*
  -> Render VNeGuide Chat API
```

The VPS adapter, not Vercel, performs media probing and WAV conversion. This is required because the
Vercel Function runtime does not provide the repository's `ffprobe` and `ffmpeg` executables. The
adapter must stay behind trusted HTTPS and a dedicated bearer token. Do not point Vercel at the raw,
unauthenticated ASR port.

## VPS prerequisites

Expose only the adapter through one of these options:

1. A named Cloudflare Tunnel with a stable hostname (preferred when a Cloudflare-managed domain is
   available).
2. A dedicated DNS hostname routed through the existing Caddy instance with a publicly trusted
   certificate.

Keep the raw Qwen endpoint private to the Docker network or bind it to loopback. Validate the Caddy
configuration before reload and do not recreate unrelated containers using ports 80/443.

On the current VPS, attach the existing `vneguide-stt` container to `vn-en-translator_default` with
the network alias `vneguide-stt`. The adapter then calls it directly at
`http://vneguide-stt:9208/v1/audio/transcriptions`; block the old host-published port 9208 on the
public interface. This changes neither the translator nor the containers bound to 80/443/9000.

The tracked adapter deployment is in [`deployment/voice-adapter/`](../../deployment/voice-adapter/).
Its bearer secret must be stored as a root-owned `0440` file on the VPS and copied separately into the
Vercel secret `VNEGUIDE_STT_API_KEY`. Never commit the value.

## Vercel environment profile

Set these variables for the intended Production/Preview environments in the existing Vercel project:

```dotenv
VNEGUIDE_API_BASE_URL=https://vneguide-api.onrender.com

VNEGUIDE_STT_ENABLED=1
VNEGUIDE_STT_BASE_URL=https://voice.example.com/v1
VNEGUIDE_STT_MODEL=Qwen/Qwen3-ASR-0.6B-hf
VNEGUIDE_STT_LANGUAGE=vi
VNEGUIDE_STT_SEND_LANGUAGE=0
VNEGUIDE_STT_API_KEY=<dedicated-adapter-bearer-token>
VNEGUIDE_STT_ALLOW_INSECURE_HTTP=0
VNEGUIDE_STT_TIMEOUT_SECONDS=50
VNEGUIDE_STT_MAX_BYTES=4000000
VNEGUIDE_STT_MAX_DURATION_SECONDS=60
VNEGUIDE_STT_CONVERT_TO_WAV=0
VNEGUIDE_STT_PROVIDER_VALIDATES_MEDIA=1

VNEGUIDE_TTS_ENABLED=1
VNEGUIDE_TTS_BASE_URL=https://api.openai.com/v1
VNEGUIDE_TTS_MODEL=gpt-4o-mini-tts
VNEGUIDE_TTS_VOICE=marin
VNEGUIDE_TTS_API_KEY=<tts-provider-key>
VNEGUIDE_TTS_ALLOW_INSECURE_HTTP=0
VNEGUIDE_TTS_TIMEOUT_SECONDS=50
VNEGUIDE_TTS_MAX_RESPONSE_BYTES=4000000
```

`4,000,000` bytes stays below Vercel's 4.5 MB Function request/response payload limit with margin.
Both voice routes declare a 60-second Function duration. The 50-second upstream timeout leaves time
for the BFF to return a typed error before the Function deadline. If real CPU ASR cannot meet this
budget, shorten recordings or move ASR to a GPU; do not silently increase the limit without checking
the Vercel plan and Fluid Compute settings.

`VNEGUIDE_STT_PROVIDER_VALIDATES_MEDIA=1` is a trust boundary. It is only valid with the hardened VPS
adapter, which enforces the same size/duration/MIME policy and performs `ffprobe`/`ffmpeg`. It cannot be
combined with `VNEGUIDE_STT_CONVERT_TO_WAV=1` in the BFF.

Environment changes apply only to new Vercel deployments. Create a fresh deployment after setting or
rotating secrets. The project Root Directory remains `demoweb`; no model key may use a
`NEXT_PUBLIC_*` name.

## Verification and rollback

Verify in this order without personal audio:

1. Adapter `/health` over public HTTPS returns healthy without disclosing configuration.
2. Adapter transcription returns `401` with no/wrong bearer token.
3. A short synthetic Vietnamese WAV succeeds with the correct token.
4. `GET /api/stt/transcribe` and `GET /api/tts/speech` on Vercel return `enabled: true`.
5. A synthetic browser recording is transcribed into the input but is not automatically submitted.
6. Chat text still reaches Render and TTS produces Vietnamese MP3.
7. Oversized, over-duration, invalid-container, and unsupported-MIME inputs fail safely.

Rollback does not require touching Render or the VPS HTTPS service: set
`VNEGUIDE_STT_ENABLED=0`/`VNEGUIDE_TTS_ENABLED=0` and deploy Vercel again. Text chat remains available.
