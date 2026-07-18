import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";

interface FieldPayload {
  field_id?: unknown;
  value?: unknown;
  expected_revision?: unknown;
  context?: unknown;
}

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
  };
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

    let sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
    let createdSession = false;
    if (!sessionId) {
      const created = await callChatApi("/v1/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ context: payload.context ?? null }),
      });
      if (!created.ok) {
        return NextResponse.json(await safeResponseBody(created), { status: created.status });
      }
      sessionId = created.headers.get("X-VNeGuide-Session") ?? undefined;
      createdSession = Boolean(sessionId);
    }

    if (!sessionId) {
      return NextResponse.json(
        {
          error: {
            code: "session_not_found",
            message: "Chưa thể khởi tạo phiên đồng bộ biểu mẫu.",
            retryable: true,
          },
        },
        { status: 503 },
      );
    }

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
    const response = NextResponse.json(await safeResponseBody(backend), {
      status: backend.status,
    });
    if (createdSession) response.cookies.set(CHAT_SESSION_COOKIE, sessionId, cookieOptions());
    return response;
  } catch (error) {
    return unavailableResponse(error);
  }
}
