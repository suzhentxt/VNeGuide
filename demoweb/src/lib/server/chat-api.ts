import "server-only";

export const CHAT_SESSION_COOKIE = "vneguide_chat_session";
export const CHAT_PROCEDURE_COOKIE = "vneguide_chat_procedure";

// The extractor can make two provider attempts of up to 20 seconds each.
// Keep the BFF alive long enough for the bounded retry path to finish.
const REQUEST_TIMEOUT_MS = 60_000;

function getApiBaseUrl() {
  const configured = process.env.VNEGUIDE_API_BASE_URL?.trim();
  const value = configured || "http://127.0.0.1:8000";
  const url = new URL(value);

  if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
    throw new Error("VNEGUIDE_API_BASE_URL must be an HTTP(S) URL without credentials");
  }

  return url;
}

export async function callChatApi(path: string, init: RequestInit = {}) {
  const target = new URL(path, getApiBaseUrl());
  return fetch(target, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
}

export async function safeResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return {
      error: {
        code: "invalid_backend_response",
        message: "Dịch vụ trợ lý trả về dữ liệu không hợp lệ.",
        retryable: true,
      },
    };
  }
}

export function unavailableResponse(error?: unknown) {
  const timeout = error instanceof DOMException && error.name === "TimeoutError";
  return Response.json(
    {
      error: {
        code: timeout ? "chat_api_timeout" : "chat_api_unavailable",
        message: timeout
          ? "Trợ lý phản hồi quá thời gian. Biểu mẫu vẫn dùng được; bạn có thể thử lại sau."
          : "Chưa thể kết nối tới trợ lý VNeGuide. Biểu mẫu vẫn dùng được.",
        retryable: true,
      },
    },
    { status: 503 },
  );
}
