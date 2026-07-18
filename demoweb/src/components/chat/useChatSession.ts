"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { guardSuggestionForLocalField } from "@/lib/procedure-workspace-reducer";
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

function stampMessages(messages: ChatMessage[]): ChatMessage[] {
  const now = new Date().toISOString();
  return messages.map((message) => (message.created_at ? message : { ...message, created_at: now }));
}

export function useChatSession(context: ChatSessionContext) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retryAction, setRetryAction] = useState<(() => Promise<void>) | null>(null);
  const [busy, setBusy] = useState(false);
  const initializing = useRef<Promise<void> | null>(null);
  const latestMessageRequest = useRef<string | null>(null);
  const hiddenMessages = useRef(new Set<string>());
  const [lastUserMessage, setLastUserMessage] = useState<string | null>(null);
  const workspace = useProcedureWorkspace();

  const fail = useCallback((message: string, retryFn: (() => Promise<void>) | null) => {
    setError(message);
    setRetryAction(() => retryFn);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setRetryAction(null);
  }, []);

  const applySession = useCallback(
    (nextSession: ChatSession) => {
      setSession(nextSession);
      if (nextSession.turn && workspace.applyTurn(nextSession.turn)) {
        setTurn(nextSession.turn);
        setMessages(
          stampMessages(
            nextSession.turn.messages.filter(
              (message) => message.role !== "user" || !hiddenMessages.current.has(message.content),
            ),
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

  const ensureSessionRef = useRef<() => Promise<void>>(async () => {});
  const ensureSession = useCallback(async () => {
    if (session || initializing.current) return initializing.current ?? Promise.resolve();

    const task = (async () => {
      setBusy(true);
      clearError();
      try {
        const response = await fetch("/api/chat/session", { cache: "no-store" });
        if (response.status === 404 || response.status === 410) await createSession();
        else applySession(await readJson<ChatSession>(response));
      } catch (requestError) {
        fail(errorMessage(requestError, "Chưa thể kết nối tới trợ lý."), () => ensureSessionRef.current());
      } finally {
        setBusy(false);
        initializing.current = null;
      }
    })();

    initializing.current = task;
    return task;
  }, [applySession, clearError, createSession, fail, session]);
  useEffect(() => {
    ensureSessionRef.current = ensureSession;
  }, [ensureSession]);

  const sendMessageRef = useRef<
    (message: string, options: { hidden?: boolean }) => Promise<void>
  >(async () => {});
  const sendMessage = useCallback(
    async (message: string, options: { hidden?: boolean } = {}) => {
      const normalized = message.trim();
      if (!normalized) return;

      const requestId = crypto.randomUUID();
      let expectedRevision = workspace.state.revision;
      latestMessageRequest.current = requestId;
      setLastUserMessage(normalized);
      if (options.hidden) hiddenMessages.current.add(normalized);
      setBusy(true);
      clearError();
      if (!options.hidden) {
        setMessages((current) => [
          ...current,
          { role: "user", content: normalized, created_at: new Date().toISOString() },
        ]);
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
          stampMessages(
            nextTurn.messages.filter(
              (item) => item.role !== "user" || !hiddenMessages.current.has(item.content),
            ),
          ),
        );
      } catch (requestError) {
        if (latestMessageRequest.current === requestId) {
          fail(errorMessage(requestError, "Không thể gửi tin nhắn."), () =>
            sendMessageRef.current(normalized, options),
          );
        }
      } finally {
        if (latestMessageRequest.current === requestId) setBusy(false);
      }
    },
    [clearError, createSession, fail, recoverSession, workspace],
  );
  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  const sendHiddenMessage = useCallback(
    (message: string) => sendMessage(message, { hidden: true }),
    [sendMessage],
  );

  const chooseFieldValueRef = useRef<
    (fieldId: string, value: JsonValue, visibleLabel: string) => Promise<void>
  >(async () => {});
  const chooseFieldValue = useCallback(
    async (fieldId: string, value: JsonValue, visibleLabel: string) => {
      setBusy(true);
      clearError();
      workspace.setField(fieldId, value);
      try {
        const nextTurn = await workspace.commitField(fieldId, value, {
          interaction: "chat_choice",
          displayLabel: visibleLabel,
        });
        if (!nextTurn) {
          fail(
            "Không thể đồng bộ giá trị này với trợ lý. Bạn vẫn có thể chỉnh tiếp trên form.",
            () => chooseFieldValueRef.current(fieldId, value, visibleLabel),
          );
          return;
        }
        setTurn(nextTurn);
        setMessages(
          stampMessages(
            nextTurn.messages.filter(
              (item) => item.role !== "user" || !hiddenMessages.current.has(item.content),
            ),
          ),
        );
      } finally {
        setBusy(false);
      }
    },
    [clearError, fail, workspace],
  );
  useEffect(() => {
    chooseFieldValueRef.current = chooseFieldValue;
  }, [chooseFieldValue]);

  const resolveSuggestionRef = useRef<
    (suggestion: ChatSuggestion, action: "accept" | "reject" | "edit", value?: JsonValue) => Promise<void>
  >(async () => {});
  const resolveSuggestion = useCallback(
    async (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      value?: JsonValue,
    ) => {
      if (action !== "reject" && workspace.isDirty(suggestion.field_id)) {
        fail("Field này đã được bạn sửa trực tiếp trên form. AI không được ghi đè giá trị đó.", null);
        return;
      }

      setBusy(true);
      clearError();
      const guardedSuggestion = guardSuggestionForLocalField(
        suggestion,
        workspace.state.fields[suggestion.field_id],
      );
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
        workspace.applySuggestion(guardedSuggestion, action, nextTurn, value);
        setTurn(nextTurn);
        setMessages(stampMessages(nextTurn.messages));
      } catch (requestError) {
        if (requestError instanceof ChatRequestError && requestError.status === 409) {
          workspace.markStale();
          await recoverSession();
        }
        fail(errorMessage(requestError, "Không thể cập nhật đề xuất."), () =>
          resolveSuggestionRef.current(suggestion, action, value),
        );
      } finally {
        setBusy(false);
      }
    },
    [clearError, fail, recoverSession, workspace],
  );
  useEffect(() => {
    resolveSuggestionRef.current = resolveSuggestion;
  }, [resolveSuggestion]);

  const resetSessionRef = useRef<() => Promise<void>>(async () => {});
  const resetSession = useCallback(async () => {
    setBusy(true);
    clearError();
    latestMessageRequest.current = null;
    hiddenMessages.current.clear();
    setLastUserMessage(null);
    try {
      await fetch("/api/chat/session", { method: "DELETE" });
      workspace.resetWorkspace();
      setSession(null);
      setTurn(null);
      setMessages([]);
      await createSession();
    } catch (requestError) {
      fail(errorMessage(requestError, "Không thể bắt đầu lại phiên trò chuyện."), () =>
        resetSessionRef.current(),
      );
    } finally {
      setBusy(false);
    }
  }, [clearError, createSession, fail, workspace]);
  useEffect(() => {
    resetSessionRef.current = resetSession;
  }, [resetSession]);

  const retry = useCallback(() => {
    if (busy || !retryAction) return;
    void retryAction();
  }, [busy, retryAction]);

  return {
    session,
    turn,
    messages,
    error,
    busy,
    lastUserMessage,
    retry,
    ensureSession,
    sendMessage,
    sendHiddenMessage,
    chooseFieldValue,
    resolveSuggestion,
    resetSession,
  };
}
