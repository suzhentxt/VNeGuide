import "server-only";

import { callChatApi, safeResponseBody } from "./chat-api";

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function procedureCode(context: unknown): string | null {
  if (!isJsonObject(context)) return null;
  const value = context.procedure_code;
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function withoutClientContext(payload: unknown): {
  context: unknown;
  forwardedPayload: unknown;
} {
  if (!isJsonObject(payload)) {
    return { context: null, forwardedPayload: payload };
  }

  const { context, ...forwardedPayload } = payload;
  return { context: context ?? null, forwardedPayload };
}

export async function guardSessionContext(
  sessionId: string,
  clientContext: unknown,
): Promise<Response | null> {
  const backend = await callChatApi(
    `/v1/chat/sessions/${encodeURIComponent(sessionId)}`,
  );
  const body = await safeResponseBody(backend);

  if (!backend.ok) {
    return Response.json(body, { status: backend.status });
  }
  if (!isJsonObject(body) || !("context" in body)) {
    return Response.json(
      {
        error: {
          code: "invalid_backend_response",
          message: "Dịch vụ trợ lý trả về thông tin phiên không hợp lệ.",
          retryable: true,
        },
      },
      { status: 502 },
    );
  }

  const storedCode = procedureCode(body.context);
  const expectedCode = procedureCode(clientContext);
  if (storedCode !== expectedCode) {
    return Response.json(
      {
        error: {
          code: "session_context_mismatch",
          message:
            "Phiên trợ lý đang thuộc một phạm vi thủ tục khác. Hãy bắt đầu phiên cho trang hiện tại trước khi tiếp tục.",
          retryable: false,
        },
      },
      { status: 409 },
    );
  }

  return null;
}
