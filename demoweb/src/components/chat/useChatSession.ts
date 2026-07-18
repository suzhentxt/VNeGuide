"use client";

import { useCallback, useRef, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
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
    readonly status: number,
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
      response.status,
    );
  }
  return body as T;
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ChatRequestError && error.code === "chat_api_timeout") {
    return "Trợ lý phản hồi quá thời gian. Biểu mẫu vẫn dùng được và dữ liệu không bị mất.";
  }
  return error instanceof Error ? error.message : fallback;
}

export function useChatSession(context: ChatSessionContext) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const initializing = useRef<Promise<void> | null>(null);
  const latestMessageRequest = useRef<string | null>(null);
  const hiddenMessages = useRef(new Set<string>());
  const workspace = useProcedureWorkspace();

  const applySession = useCallback(
    (nextSession: ChatSession) => {
      setSession(nextSession);
      if (nextSession.turn && workspace.applyTurn(nextSession.turn)) {
        setTurn(nextSession.turn);
        setMessages(
          nextSession.turn.messages.filter(
            (message) => message.role !== "user" || !hiddenMessages.current.has(message.content),
          ),
        );
      } else if (!nextSession.turn) {
        setTurn(null);
        setMessages([]);
      }
    },
    [workspace],
  );

  const createSession = useCallback(async () => {
    const response = await fetch("/api/chat/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context }),
    });
    applySession(await readJson<ChatSession>(response));
  }, [applySession, context]);

  const recoverSession = useCallback(async () => {
    const response = await fetch("/api/chat/session", { cache: "no-store" });
    if (!response.ok) return false;
    applySession(await readJson<ChatSession>(response));
    return true;
  }, [applySession]);

  const ensureSession = useCallback(async () => {
    if (session || initializing.current) return initializing.current ?? Promise.resolve();

    const task = (async () => {
      setBusy(true);
      setError(null);
      try {
        const response = await fetch("/api/chat/session", { cache: "no-store" });
        if (response.status === 404 || response.status === 410) await createSession();
        else applySession(await readJson<ChatSession>(response));
      } catch (requestError) {
        setError(errorMessage(requestError, "Chưa thể kết nối tới trợ lý."));
      } finally {
        setBusy(false);
        initializing.current = null;
      }
    })();

    initializing.current = task;
    return task;
  }, [applySession, createSession, session]);

  const sendMessage = useCallback(
    async (message: string, options: { hidden?: boolean } = {}) => {
      const normalized = message.trim();
      if (!normalized) return;

      const requestId = crypto.randomUUID();
      let expectedRevision = workspace.state.revision;
      latestMessageRequest.current = requestId;
      if (options.hidden) hiddenMessages.current.add(normalized);
      setBusy(true);
      setError(null);
      if (!options.hidden) {
        setMessages((current) => [...current, { role: "user", content: normalized }]);
      }
      try {
        const payload = JSON.stringify({ message: normalized, client_turn_id: requestId });
        const postMessage = () =>
          fetch("/api/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: payload,
          });

        let response = await postMessage();
        if (response.status === 404 || response.status === 410) {
          await createSession();
          workspace.rebaseSession();
          expectedRevision = 0;
          response = await postMessage();
        }
        const nextTurn = await readJson<ChatTurn>(response);
        if (latestMessageRequest.current !== requestId) return;
        if (!workspace.applyTurn(nextTurn, expectedRevision)) {
          await recoverSession();
          return;
        }
        setTurn(nextTurn);
        setMessages(
          nextTurn.messages.filter(
            (item) => item.role !== "user" || !hiddenMessages.current.has(item.content),
          ),
        );
      } catch (requestError) {
        if (latestMessageRequest.current === requestId) {
          setError(errorMessage(requestError, "Không thể gửi tin nhắn."));
        }
      } finally {
        if (latestMessageRequest.current === requestId) setBusy(false);
      }
    },
    [createSession, recoverSession, workspace],
  );

  const sendHiddenMessage = useCallback(
    (message: string) => sendMessage(message, { hidden: true }),
    [sendMessage],
  );

  const chooseFieldValue = useCallback(
    async (fieldId: string, value: JsonValue, visibleLabel: string) => {
      setBusy(true);
      setError(null);
      workspace.setField(fieldId, value);
      try {
        const nextTurn = await workspace.commitField(fieldId, value, {
          interaction: "chat_choice",
          displayLabel: visibleLabel,
        });
        if (!nextTurn) return;
        setTurn(nextTurn);
        setMessages(
          nextTurn.messages.filter(
            (item) => item.role !== "user" || !hiddenMessages.current.has(item.content),
          ),
        );
      } finally {
        setBusy(false);
      }
    },
    [workspace],
  );

  const resolveSuggestion = useCallback(
    async (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      value?: JsonValue,
    ) => {
      if (action !== "reject" && workspace.isDirty(suggestion.field_id)) {
        setError("Field này đã được bạn sửa trực tiếp trên form. AI không được ghi đè giá trị đó.");
        return;
      }

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
        workspace.applySuggestion(suggestion, action, nextTurn, value);
        setTurn(nextTurn);
        setMessages(nextTurn.messages);
      } catch (requestError) {
        if (requestError instanceof ChatRequestError && requestError.status === 409) {
          workspace.markStale();
          await recoverSession();
        }
        setError(errorMessage(requestError, "Không thể cập nhật đề xuất."));
      } finally {
        setBusy(false);
      }
    },
    [recoverSession, workspace],
  );

  const resetSession = useCallback(async () => {
    setBusy(true);
    setError(null);
    latestMessageRequest.current = null;
    hiddenMessages.current.clear();
    try {
      await fetch("/api/chat/session", { method: "DELETE" });
      workspace.resetWorkspace();
      setSession(null);
      setTurn(null);
      setMessages([]);
      await createSession();
    } catch (requestError) {
      setError(errorMessage(requestError, "Không thể bắt đầu lại phiên trò chuyện."));
    } finally {
      setBusy(false);
    }
  }, [createSession, workspace]);

  const closeSession = useCallback(async () => {
    setBusy(true);
    setError(null);
    latestMessageRequest.current = null;
    hiddenMessages.current.clear();
    try {
      await fetch("/api/chat/session", { method: "DELETE" });
      workspace.resetWorkspace();
      setSession(null);
      setTurn(null);
      setMessages([]);
    } catch (requestError) {
      setError(errorMessage(requestError, "Không thể chuyển sang hồ sơ đã chọn."));
      throw requestError;
    } finally {
      setBusy(false);
    }
  }, [workspace]);

  return {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    sendHiddenMessage,
    chooseFieldValue,
    resolveSuggestion,
    resetSession,
    closeSession,
  };
}
