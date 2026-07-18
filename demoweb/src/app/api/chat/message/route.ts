import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";
import { withoutClientContext } from "@/lib/server/chat-session-context";

export async function POST(request: NextRequest) {
  const sessionId = request.cookies.get(CHAT_SESSION_COOKIE)?.value;
  if (!sessionId) {
    return NextResponse.json(
      {
        error: {
          code: "session_not_found",
          message: "Phiên trò chuyện chưa được khởi tạo.",
          retryable: false,
        },
      },
      { status: 404 },
    );
  }

  try {
    const payload: unknown = await request.json();
    const { forwardedPayload } = withoutClientContext(payload);

    const backend = await callChatApi(
      `/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
      { method: "POST", body: JSON.stringify(forwardedPayload) },
    );
    return NextResponse.json(await safeResponseBody(backend), {
      status: backend.status,
    });
  } catch (error) {
    return unavailableResponse(error);
  }
}
