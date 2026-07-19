import { NextRequest, NextResponse } from "next/server";

import {
  getSttConfig,
  isSttRequested,
  SttConfigurationError,
  sttPublicDefaults,
} from "@/lib/server/stt-config";
import {
  SttAudioConversionError,
  SttAudioValidationError,
  convertToWav,
  validateAudioDuration,
} from "@/lib/server/stt-audio";
import { SttProviderError, transcribeAudio } from "@/lib/server/stt-client";

export const runtime = "nodejs";
export const maxDuration = 60;

const MIME_TYPES = new Map<string, string>([
  ["audio/webm", "recording.webm"],
  ["audio/ogg", "recording.ogg"],
  ["audio/wav", "recording.wav"],
  ["audio/x-wav", "recording.wav"],
  ["audio/mpeg", "recording.mp3"],
  ["audio/mp3", "recording.mp3"],
  ["audio/mp4", "recording.m4a"],
  ["audio/x-m4a", "recording.m4a"],
  ["audio/aac", "recording.aac"],
  ["audio/flac", "recording.flac"],
]);

class InvalidAudioError extends Error {
  constructor(readonly kind: "empty" | "too_large") {
    super(kind);
  }
}

function json(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "no-store, max-age=0" },
  });
}

function errorResponse(
  code: string,
  message: string,
  status: number,
  retryable = false,
) {
  return json({ error: { code, message, retryable } }, status);
}

async function readLimitedBody(
  body: ReadableStream<Uint8Array> | null,
  maxBytes: number,
) {
  if (!body) throw new InvalidAudioError("empty");
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new InvalidAudioError("too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  if (total === 0) throw new InvalidAudioError("empty");
  const audio = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    audio.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return audio;
}

export async function GET() {
  if (!isSttRequested()) {
    return json({
      enabled: false,
      max_bytes: sttPublicDefaults.maxBytes,
      max_duration_seconds: sttPublicDefaults.maxDurationSeconds,
    });
  }

  try {
    const config = await getSttConfig();
    return json({
      enabled: true,
      max_bytes: config.maxBytes,
      max_duration_seconds: config.maxDurationSeconds,
    });
  } catch {
    return json({
      enabled: false,
      max_bytes: sttPublicDefaults.maxBytes,
      max_duration_seconds: sttPublicDefaults.maxDurationSeconds,
    });
  }
}

export async function POST(request: NextRequest) {
  let config;
  try {
    config = await getSttConfig();
  } catch (error) {
    if (error instanceof SttConfigurationError) {
      return errorResponse(
        "stt_unavailable",
        "Nhập liệu bằng giọng nói chưa được cấu hình trên máy chủ.",
        503,
        true,
      );
    }
    return errorResponse("stt_unavailable", "Dịch vụ giọng nói tạm thời chưa sẵn sàng.", 503, true);
  }

  const rawContentType = request.headers.get("content-type")?.toLowerCase() ?? "";
  const mimeType = rawContentType.split(";", 1)[0].trim();
  const filename = MIME_TYPES.get(mimeType);
  if (!filename) {
    return errorResponse(
      "unsupported_audio_type",
      "Định dạng âm thanh này chưa được hỗ trợ. Hãy dùng WebM, OGG, WAV, MP3, M4A, AAC hoặc FLAC.",
      415,
    );
  }

  const durationHeader = request.headers.get("x-vneguide-audio-duration-ms")?.trim();
  const durationMs = durationHeader ? Number(durationHeader) : Number.NaN;
  if (Number.isFinite(durationMs) && durationMs > config.maxDurationSeconds * 1000) {
    return errorResponse(
      "invalid_audio_duration",
      `Bản ghi phải dài không quá ${config.maxDurationSeconds} giây.`,
      400,
    );
  }

  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > config.maxBytes) {
    return errorResponse("audio_too_large", "Tệp âm thanh vượt quá dung lượng cho phép.", 413);
  }

  let audio: Uint8Array;
  try {
    audio = await readLimitedBody(request.body, config.maxBytes);
  } catch (error) {
    if (error instanceof InvalidAudioError && error.kind === "too_large") {
      return errorResponse("audio_too_large", "Tệp âm thanh vượt quá dung lượng cho phép.", 413);
    }
    return errorResponse("empty_audio", "Không nhận được dữ liệu âm thanh.", 400);
  }

  if (!config.providerValidatesMedia) {
    try {
      await validateAudioDuration(audio, config.maxDurationSeconds);
    } catch (error) {
      if (error instanceof SttAudioValidationError && error.kind === "too_long") {
        return errorResponse(
          "invalid_audio_duration",
          `Bản ghi phải dài không quá ${config.maxDurationSeconds} giây.`,
          400,
        );
      }
      return errorResponse(
        "invalid_audio",
        "Không thể xác minh định dạng hoặc thời lượng của tệp âm thanh.",
        422,
      );
    }
  }

  let sttAudio = audio;
  let sttMimeType = mimeType;
  let sttFilename = filename;
  if (config.convertToWav) {
    try {
      sttAudio = await convertToWav(audio);
    } catch (error) {
      if (error instanceof SttAudioConversionError) {
        return errorResponse(
          "audio_conversion_failed",
          "Không thể xử lý định dạng âm thanh. Hãy thử ghi âm lại hoặc dùng tệp WAV.",
          422,
        );
      }
      return errorResponse(
        "stt_unavailable",
        "Chưa thể xử lý âm thanh lúc này. Nội dung đã nhập vẫn được giữ nguyên.",
        502,
        true,
      );
    }
    sttMimeType = "audio/wav";
    sttFilename = "recording.wav";
  }

  try {
    const result = await transcribeAudio(sttAudio, sttMimeType, sttFilename, config);
    return json(result);
  } catch (error) {
    if (error instanceof SttProviderError) {
      if (error.kind === "bad_audio") {
        return errorResponse(
          "speech_not_recognized",
          "Không nhận dạng được lời nói trong bản ghi. Hãy thử nói gần mic hơn.",
          422,
        );
      }
      if (error.kind === "format_rejected") {
        return errorResponse(
          "unsupported_audio_type",
          "Định dạng âm thanh chưa được nhà cung cấp hỗ trợ. Hãy thử ghi âm lại hoặc dùng tệp WAV.",
          415,
        );
      }
      if (error.kind === "rate_limited") {
        return errorResponse(
          "stt_rate_limited",
          "Dịch vụ giọng nói đang bận. Hãy đợi một chút rồi thử lại.",
          429,
          true,
        );
      }
      if (error.kind === "timeout") {
        return errorResponse(
          "stt_timeout",
          "Nhận dạng giọng nói quá thời gian chờ. Hãy thử một bản ghi ngắn hơn.",
          504,
          true,
        );
      }
    }
    return errorResponse(
      "stt_unavailable",
      "Chưa thể nhận dạng giọng nói lúc này. Nội dung đã nhập vẫn được giữ nguyên.",
      502,
      true,
    );
  }
}
