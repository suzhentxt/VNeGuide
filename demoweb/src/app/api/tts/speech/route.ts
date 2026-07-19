import { NextRequest, NextResponse } from "next/server";

import { callChatApi, CHAT_SESSION_COOKIE } from "@/lib/server/chat-api";
import {
  getTtsConfig,
  isTtsRequested,
  TtsConfigurationError,
} from "@/lib/server/tts-config";
import { synthesizeSpeech, TtsProviderError } from "@/lib/server/tts-client";
import { assistantSpeechSegments, TtsTextError } from "@/lib/server/tts-text";

export const runtime = "nodejs";
export const maxDuration = 60;

const MAX_REQUEST_BYTES = 1_024;
const MAX_SESSION_RESPONSE_BYTES = 256 * 1024;
const MAX_MESSAGE_ORDINAL = 10_000;

class RequestBodyError extends Error {
  constructor(readonly kind: "invalid" | "too_large") {
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

async function readLimitedBytes(
  body: ReadableStream<Uint8Array> | null,
  maximum: number,
) {
  if (!body) throw new RequestBodyError("invalid");
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maximum) {
        await reader.cancel();
        throw new RequestBodyError("too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  if (total === 0) throw new RequestBodyError("invalid");

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

async function readLimitedJson(
  body: ReadableStream<Uint8Array> | null,
  maximum: number,
) {
  const bytes = await readLimitedBytes(body, maximum);
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  } catch (error) {
    if (error instanceof RequestBodyError) throw error;
    throw new RequestBodyError("invalid");
  }
}

function parseSpeechRequest(value: unknown) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new RequestBodyError("invalid");
  }
  const body = value as Record<string, unknown>;
  const keys = Object.keys(body).sort();
  if (keys.length !== 2 || keys[0] !== "assistant_index" || keys[1] !== "segment_index") {
    throw new RequestBodyError("invalid");
  }
  if (
    !Number.isSafeInteger(body.assistant_index) ||
    !Number.isSafeInteger(body.segment_index) ||
    (body.assistant_index as number) < 0 ||
    (body.assistant_index as number) > MAX_MESSAGE_ORDINAL ||
    (body.segment_index as number) < 0 ||
    (body.segment_index as number) > MAX_MESSAGE_ORDINAL
  ) {
    throw new RequestBodyError("invalid");
  }
  return {
    assistantIndex: body.assistant_index as number,
    segmentIndex: body.segment_index as number,
  };
}

export async function GET() {
  if (!isTtsRequested()) return json({ enabled: false });
  try {
    await getTtsConfig();
    return json({ enabled: true });
  } catch {
    return json({ enabled: false });
  }
}

export async function POST(request: NextRequest) {
  let config;
  try {
    config = await getTtsConfig();
  } catch (error) {
    if (error instanceof TtsConfigurationError) {
      return errorResponse(
        "tts_unavailable",
        "Tính năng đọc tiếng Việt chưa được cấu hình trên máy chủ.",
        503,
        true,
      );
    }
    return errorResponse("tts_unavailable", "Giọng đọc tạm thời chưa sẵn sàng.", 503, true);
  }

  const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
  if (!sessionId) {
    return errorResponse(
      "session_not_found",
      "Phiên trò chuyện chưa được khởi tạo.",
      404,
    );
  }

  const contentType = request.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (contentType !== "application/json") {
    return errorResponse(
      "invalid_tts_request",
      "Yêu cầu giọng đọc không hợp lệ.",
      415,
    );
  }
  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES) {
    return errorResponse("tts_request_too_large", "Yêu cầu giọng đọc quá lớn.", 413);
  }

  let payload: ReturnType<typeof parseSpeechRequest>;
  try {
    payload = parseSpeechRequest(await readLimitedJson(request.body, MAX_REQUEST_BYTES));
  } catch (error) {
    if (error instanceof RequestBodyError && error.kind === "too_large") {
      return errorResponse("tts_request_too_large", "Yêu cầu giọng đọc quá lớn.", 413);
    }
    return errorResponse("invalid_tts_request", "Yêu cầu giọng đọc không hợp lệ.", 400);
  }

  let session: unknown;
  try {
    const backend = await callChatApi(
      `/v1/chat/sessions/${encodeURIComponent(sessionId)}`,
      { signal: request.signal },
    );
    if (!backend.ok) {
      try {
        await backend.body?.cancel();
      } catch {
        // The internal response body is intentionally not forwarded.
      }
      if (backend.status === 404) {
        return errorResponse("session_not_found", "Không tìm thấy phiên trò chuyện.", 404);
      }
      if (backend.status === 410) {
        return errorResponse("session_expired", "Phiên trò chuyện đã hết hạn.", 410);
      }
      return errorResponse(
        "chat_api_unavailable",
        "Chưa thể đọc lại nội dung trò chuyện lúc này.",
        503,
        true,
      );
    }
    session = await readLimitedJson(backend.body, MAX_SESSION_RESPONSE_BYTES);
  } catch (error) {
    const timeout =
      error instanceof DOMException &&
      (error.name === "TimeoutError" || error.name === "AbortError");
    return errorResponse(
      timeout ? "chat_api_timeout" : "chat_api_unavailable",
      timeout
        ? "Trợ lý phản hồi quá thời gian khi chuẩn bị giọng đọc."
        : "Chưa thể đọc lại nội dung trò chuyện lúc này.",
      timeout ? 504 : 503,
      true,
    );
  }

  let segments: string[];
  try {
    segments = assistantSpeechSegments(
      session,
      payload.assistantIndex,
      config.maxMessageCharacters,
      config.segmentCharacters,
    );
  } catch (error) {
    if (error instanceof TtsTextError) {
      if (error.kind === "not_found") {
        return errorResponse(
          "assistant_message_not_found",
          "Không tìm thấy câu trả lời cần đọc trong phiên hiện tại.",
          404,
        );
      }
      if (error.kind === "too_long") {
        return errorResponse(
          "tts_text_too_long",
          "Câu trả lời quá dài để tạo giọng đọc.",
          413,
        );
      }
      if (error.kind === "empty") {
        return errorResponse(
          "tts_text_empty",
          "Câu trả lời không có nội dung để đọc.",
          422,
        );
      }
    }
    return errorResponse(
      "invalid_chat_session",
      "Dữ liệu phiên trò chuyện không hợp lệ để tạo giọng đọc.",
      502,
      true,
    );
  }

  if (payload.segmentIndex >= segments.length) {
    return errorResponse(
      "tts_segment_not_found",
      "Đoạn giọng đọc được yêu cầu không tồn tại.",
      400,
    );
  }

  try {
    const audio = await synthesizeSpeech(
      segments[payload.segmentIndex],
      config,
      request.signal,
    );
    const body = new Uint8Array(audio.byteLength);
    body.set(audio);
    return new NextResponse(body.buffer, {
      status: 200,
      headers: {
        "Cache-Control": "no-store, max-age=0",
        "Content-Length": String(body.byteLength),
        "Content-Type": "audio/mpeg",
        "X-Content-Type-Options": "nosniff",
        "X-VNeGuide-TTS-Segment-Count": String(segments.length),
        "X-VNeGuide-TTS-Segment-Index": String(payload.segmentIndex),
      },
    });
  } catch (error) {
    if (error instanceof TtsProviderError) {
      if (error.kind === "invalid_input") {
        return errorResponse(
          "tts_input_rejected",
          "Chưa thể tạo giọng đọc cho nội dung này.",
          422,
        );
      }
      if (error.kind === "rate_limited") {
        return errorResponse(
          "tts_rate_limited",
          "Dịch vụ giọng đọc đang bận. Hãy đợi một chút rồi thử lại.",
          429,
          true,
        );
      }
      if (error.kind === "timeout") {
        return errorResponse(
          "tts_timeout",
          "Tạo giọng đọc quá thời gian chờ. Hãy thử lại sau.",
          504,
          true,
        );
      }
    }
    return errorResponse(
      "tts_unavailable",
      "Chưa thể tạo giọng đọc lúc này. Nội dung văn bản vẫn có thể sử dụng bình thường.",
      502,
      true,
    );
  }
}
