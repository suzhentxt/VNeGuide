import { NextRequest, NextResponse } from "next/server";

import {
  callChatApi,
  CHAT_SESSION_COOKIE,
  safeResponseBody,
  unavailableResponse,
} from "@/lib/server/chat-api";

interface SuggestionPayload {
  suggestion_id?: unknown;
  action?: unknown;
  value?: unknown;
  expected_revision?: unknown;
}

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
    const payload = (await request.json()) as SuggestionPayload;
    if (typeof payload.suggestion_id !== "string" || payload.suggestion_id.length > 200) {
      return NextResponse.json(
        {
          error: {
            code: "invalid_suggestion",
            message: "Đề xuất không hợp lệ.",
            retryable: false,
          },
        },
        { status: 400 },
      );
    }

    const { suggestion_id: suggestionId, ...action } = payload;
    const backend = await callChatApi(
      `/v1/chat/sessions/${encodeURIComponent(sessionId)}/suggestions/${encodeURIComponent(suggestionId)}`,
      { method: "POST", body: JSON.stringify(action) },
    );
    return NextResponse.json(await safeResponseBody(backend), {
      status: backend.status,
    });
  } catch (error) {
    return unavailableResponse(error);
  }
}
