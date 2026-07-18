"use client";

import { useCallback, useRef, useState } from "react";

import type {
  ChatApiError,
  ChatMessage,
  ChatSession,
  ChatSessionContext,
  ChatSuggestion,
  ChatTurn,
  JsonValue,
} from "@/types/chat";

class ChatRequestError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
  }
}

async function readJson<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T | ChatApiError;
  if (!response.ok) {
    const error = body as ChatApiError;
    throw new ChatRequestError(
      error.error?.message || "Không thể xử lý yêu cầu trò chuyện.",
      error.error?.code || "chat_request_failed",
    );
  }
  return body as T;
}

export function useChatSession(context: ChatSessionContext) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const initializing = useRef<Promise<void> | null>(null);

  const applySession = useCallback((nextSession: ChatSession) => {
    setSession(nextSession);
    setTurn(nextSession.turn);
    setMessages(nextSession.turn?.messages ?? []);
  }, []);

  const createSession = useCallback(async () => {
    const response = await fetch("/api/chat/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context }),
    });
    applySession(await readJson<ChatSession>(response));
  }, [applySession, context]);

  const ensureSession = useCallback(async () => {
    if (session || initializing.current) {
      return initializing.current ?? Promise.resolve();
    }

    const task = (async () => {
      setBusy(true);
      setError(null);
      try {
        const response = await fetch("/api/chat/session", { cache: "no-store" });
        if (response.status === 404 || response.status === 410) {
          await createSession();
        } else {
          applySession(await readJson<ChatSession>(response));
        }
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Chưa thể kết nối tới trợ lý.",
        );
      } finally {
        setBusy(false);
        initializing.current = null;
      }
    })();

    initializing.current = task;
    return task;
  }, [applySession, createSession, session]);

  const sendMessage = useCallback(async (message: string) => {
    const normalized = message.trim();
    if (!normalized) return;

    setBusy(true);
    setError(null);
    setMessages((current) => [...current, { role: "user", content: normalized }]);
    try {
      const payload = JSON.stringify({
        message: normalized,
        client_turn_id: crypto.randomUUID(),
      });
      const postMessage = () =>
        fetch("/api/chat/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
        });

      let response = await postMessage();
      if (response.status === 404 || response.status === 410) {
        await createSession();
        response = await postMessage();
      }
      const nextTurn = await readJson<ChatTurn>(response);
      setTurn(nextTurn);
      setMessages(nextTurn.messages);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Không thể gửi tin nhắn.",
      );
    } finally {
      setBusy(false);
    }
  }, [createSession]);

  const resolveSuggestion = useCallback(
    async (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      value?: JsonValue,
    ) => {
      setBusy(true);
      setError(null);
      try {
        const response = await fetch("/api/chat/suggestion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            suggestion_id: suggestion.id,
            action,
            ...(action === "edit" ? { value } : {}),
            expected_revision: suggestion.revision,
          }),
        });
        const nextTurn = await readJson<ChatTurn>(response);
        setTurn(nextTurn);
        setMessages((current) => [
          ...current,
          { role: "assistant", content: nextTurn.reply },
        ]);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không thể cập nhật đề xuất.",
        );
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const resetSession = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await fetch("/api/chat/session", { method: "DELETE" });
      setSession(null);
      setTurn(null);
      setMessages([]);
      await createSession();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Không thể bắt đầu lại phiên trò chuyện.",
      );
    } finally {
      setBusy(false);
    }
  }, [createSession]);

  return {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    resolveSuggestion,
    resetSession,
  };
}
