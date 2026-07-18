import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_PROCEDURE_COOKIE,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";

interface FieldPayload {
  field_id?: unknown;
  value?: unknown;
  expected_revision?: unknown;
  context?: unknown;
  interaction?: unknown;
  display_label?: unknown;
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
      || (payload.interaction !== undefined && payload.interaction !== "chat_choice")
      || (payload.interaction === "chat_choice" && (
        typeof payload.display_label !== "string" ||
        payload.display_label.length === 0 ||
        payload.display_label.length > 200
      ))
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
    const fieldId = payload.field_id;

    const context =
      payload.context && typeof payload.context === "object"
        ? payload.context as Record<string, unknown>
        : null;
    const requestedProcedure =
      context && typeof context.procedure_code === "string"
        ? context.procedure_code
        : null;
    let sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
    const cookieProcedure = request.cookies.get(CHAT_PROCEDURE_COOKIE)?.value;
    let createdSession = false;
    if (!sessionId || (requestedProcedure && cookieProcedure !== requestedProcedure)) {
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
            message: "Chưa có phiên đồng bộ biểu mẫu.",
            retryable: true,
          },
        },
        { status: 404 },
      );
    }

    const patchField = (activeSessionId: string, expectedRevision: number) => callChatApi(
      `/v1/chat/sessions/${encodeURIComponent(activeSessionId)}/draft/fields/${encodeURIComponent(fieldId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          value: payload.value ?? null,
          expected_revision: expectedRevision,
          interaction: payload.interaction ?? "form",
          ...(payload.interaction === "chat_choice"
            ? { display_label: payload.display_label }
            : {}),
        }),
      },
    );
    let backend = await patchField(sessionId, createdSession ? 0 : payload.expected_revision);
    if (!createdSession && (backend.status === 404 || backend.status === 410)) {
      const recreated = await callChatApi("/v1/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ context: payload.context ?? null }),
      });
      if (!recreated.ok) {
        return NextResponse.json(await safeResponseBody(recreated), { status: recreated.status });
      }
      const recreatedId = recreated.headers.get("X-VNeGuide-Session");
      if (!recreatedId) {
        return NextResponse.json(
          {
            error: {
              code: "session_not_found",
              message: "Chưa thể tạo lại phiên đồng bộ biểu mẫu.",
              retryable: true,
            },
          },
          { status: 503 },
        );
      }
      sessionId = recreatedId;
      createdSession = true;
      backend = await patchField(sessionId, 0);
    }
    const response = NextResponse.json(await safeResponseBody(backend), {
      status: backend.status,
    });
    if (createdSession) {
      response.cookies.set(CHAT_SESSION_COOKIE, sessionId, cookieOptions());
      if (requestedProcedure) {
        response.cookies.set(CHAT_PROCEDURE_COOKIE, requestedProcedure, cookieOptions());
      } else {
        response.cookies.delete(CHAT_PROCEDURE_COOKIE);
      }
      response.headers.set("X-VNeGuide-Session-Recreated", "1");
    }
    return response;
  } catch (error) {
    return unavailableResponse(error);
  }
}
