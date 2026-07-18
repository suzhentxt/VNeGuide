import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_PROCEDURE_COOKIE,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
  };
}

const SUPPORTED_PROCEDURE_CODES = new Set(["2.000635", "1.013314", "1.004194"]);

export async function POST(request: NextRequest) {
  try {
    const payload: unknown = await request.json();
    const backend = await callChatApi("/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const body = await safeResponseBody(backend);
    const response = NextResponse.json(body, { status: backend.status });
    const sessionId = backend.headers.get("X-VNeGuide-Session");

    if (backend.ok && sessionId) {
      response.cookies.set(CHAT_SESSION_COOKIE, sessionId, cookieOptions());
      const context =
        payload && typeof payload === "object" && "context" in payload
          ? payload.context
          : null;
      const procedureCode =
        context && typeof context === "object" && "procedure_code" in context
          ? context.procedure_code
          : null;
      if (typeof procedureCode === "string") {
        response.cookies.set(CHAT_PROCEDURE_COOKIE, procedureCode, cookieOptions());
      } else {
        response.cookies.delete(CHAT_PROCEDURE_COOKIE);
      }
    }
    return response;
  } catch (error) {
    return unavailableResponse(error);
  }
}

export async function GET(request: NextRequest) {
  const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
  if (!sessionId) {
    return NextResponse.json(
      {
        error: {
          code: "session_not_found",
          message: "Chưa có phiên trò chuyện.",
          retryable: false,
        },
      },
      { status: 404 },
    );
  }

  try {
    const backend = await callChatApi(`/v1/chat/sessions/${encodeURIComponent(sessionId)}`);
    const body = await safeResponseBody(backend);
    const response = NextResponse.json(body, { status: backend.status });
    if (backend.status === 404 || backend.status === 410) {
      response.cookies.delete(CHAT_SESSION_COOKIE);
      response.cookies.delete(CHAT_PROCEDURE_COOKIE);
    }
    return response;
  } catch (error) {
    return unavailableResponse(error);
  }
}

export async function PATCH(request: NextRequest) {
  const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
  if (!sessionId) {
    return NextResponse.json(
      {
        error: {
          code: "session_not_found",
          message: "Chưa có phiên trò chuyện để tiếp tục.",
          retryable: false,
        },
      },
      { status: 404 },
    );
  }

  try {
    const payload = (await request.json()) as { procedure_code?: unknown };
    if (
      typeof payload.procedure_code !== "string" ||
      !SUPPORTED_PROCEDURE_CODES.has(payload.procedure_code)
    ) {
      return NextResponse.json(
        {
          error: {
            code: "invalid_procedure",
            message: "Dịch vụ được xác nhận không hợp lệ.",
            retryable: false,
          },
        },
        { status: 400 },
      );
    }

    const backend = await callChatApi(`/v1/chat/sessions/${encodeURIComponent(sessionId)}`);
    const body = await safeResponseBody(backend);
    if (!backend.ok) {
      return NextResponse.json(body, { status: backend.status });
    }
    const session = body && typeof body === "object" ? body as Record<string, unknown> : null;
    const turn = session?.turn && typeof session.turn === "object"
      ? session.turn as Record<string, unknown>
      : null;
    const procedure = turn?.procedure && typeof turn.procedure === "object"
      ? turn.procedure as Record<string, unknown>
      : null;
    const context = session?.context && typeof session.context === "object"
      ? session.context as Record<string, unknown>
      : null;
    const activeProcedure =
      typeof procedure?.code === "string"
        ? procedure.code
        : typeof context?.procedure_code === "string"
          ? context.procedure_code
          : null;
    if (activeProcedure !== payload.procedure_code) {
      return NextResponse.json(
        {
          error: {
            code: "procedure_conflict",
            message: "Dịch vụ xác nhận không khớp với phiên trò chuyện.",
            retryable: false,
          },
        },
        { status: 409 },
      );
    }

    const response = new NextResponse(null, { status: 204 });
    response.cookies.set(CHAT_PROCEDURE_COOKIE, payload.procedure_code, cookieOptions());
    return response;
  } catch (error) {
    return unavailableResponse(error);
  }
}

export async function DELETE(request: NextRequest) {
  const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
  try {
    if (sessionId) {
      await callChatApi(`/v1/chat/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      });
    }
  } catch {
    // Reset the browser session even when the local API is already unavailable.
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(CHAT_SESSION_COOKIE);
  response.cookies.delete(CHAT_PROCEDURE_COOKIE);
  return response;
}
