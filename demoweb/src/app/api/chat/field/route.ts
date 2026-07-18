import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";
import { guardSessionContext } from "@/lib/server/chat-session-context";

interface FieldPayload {
  field_id?: unknown;
  value?: unknown;
  expected_revision?: unknown;
  context?: unknown;
}

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as FieldPayload;
    if (
      typeof payload.field_id !== "string" ||
      !/^[a-z][a-z0-9_]{0,99}$/.test(payload.field_id) ||
      typeof payload.expected_revision !== "number" ||
      !Number.isInteger(payload.expected_revision) ||
      payload.expected_revision < 0
    ) {
      return NextResponse.json(
        {
          error: {
            code: "invalid_field_update",
            message: "Dữ liệu cập nhật biểu mẫu không hợp lệ.",
            retryable: false,
          },
        },
        { status: 400 },
      );
    }

    const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
    if (!sessionId) {
      return NextResponse.json(
        {
          error: {
            code: "session_not_found",
            message: "Chưa có phiên đồng bộ biểu mẫu.",
            retryable: true,
          },
        },
        { status: 404 },
      );
    }

    const contextMismatch = await guardSessionContext(sessionId, payload.context);
    if (contextMismatch) return contextMismatch;

    const backend = await callChatApi(
      `/v1/chat/sessions/${encodeURIComponent(sessionId)}/draft/fields/${encodeURIComponent(payload.field_id)}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          value: payload.value ?? null,
          expected_revision: payload.expected_revision,
        }),
      },
    );
    return NextResponse.json(await safeResponseBody(backend), {
      status: backend.status,
    });
  } catch (error) {
    return unavailableResponse(error);
  }
}
