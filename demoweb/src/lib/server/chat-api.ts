import "server-only";

export const CHAT_SESSION_COOKIE = "vneguide_chat_session";

const REQUEST_TIMEOUT_MS = 25_000;

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

export function unavailableResponse() {
  return Response.json(
    {
      error: {
        code: "chat_api_unavailable",
        message: "Chưa thể kết nối tới trợ lý VNeGuide. Vui lòng thử lại sau.",
        retryable: true,
      },
    },
    { status: 503 },
  );
}
