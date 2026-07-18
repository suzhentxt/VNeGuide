"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import {
  getChatContextKey,
  shouldRebindChatWorkspace,
  shouldRebindChatSession,
} from "@/data/chat-scope";
import {
  createChatSession,
  subscribeToChatSession,
  subscribeToChatTurn,
} from "@/lib/chat-session-client";
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

interface ChatOperation {
  controller: AbortController;
  generation: number;
  procedureKey: string;
}

interface Initialization {
  procedureKey: string;
  promise: Promise<void>;
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

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useChatSession(context: ChatSessionContext) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const initializing = useRef<Initialization | null>(null);
  const latestMessageRequest = useRef<string | null>(null);
  const activeControllers = useRef(new Set<AbortController>());
  const pendingOperations = useRef(0);
  const generation = useRef(0);
  const workspace = useProcedureWorkspace();
  const procedureKey = getChatContextKey(context);
  const currentProcedureKey = useRef(procedureKey);

  useLayoutEffect(() => {
    const controllers = activeControllers.current;
    currentProcedureKey.current = procedureKey;
    generation.current += 1;
    latestMessageRequest.current = null;
    initializing.current = null;

    return () => {
      for (const controller of controllers) controller.abort();
      controllers.clear();
    };
  }, [procedureKey]);

  const beginOperation = useCallback((): ChatOperation => {
    const controller = new AbortController();
    const operation = {
      controller,
      generation: generation.current,
      procedureKey: currentProcedureKey.current,
    };
    activeControllers.current.add(controller);
    pendingOperations.current += 1;
    setBusy(true);
    return operation;
  }, []);

  const finishOperation = useCallback((operation: ChatOperation) => {
    activeControllers.current.delete(operation.controller);
    pendingOperations.current = Math.max(0, pendingOperations.current - 1);
    if (pendingOperations.current === 0) setBusy(false);
  }, []);

  const operationIsCurrent = useCallback(
    (operation: ChatOperation, requestProcedureKey: string) =>
      !operation.controller.signal.aborted &&
      operation.generation === generation.current &&
      operation.procedureKey === requestProcedureKey &&
      currentProcedureKey.current === requestProcedureKey,
    [],
  );

  const applySession = useCallback(
    (nextSession: ChatSession, requestProcedureKey: string) => {
      if (currentProcedureKey.current !== requestProcedureKey) return false;

      setSession(nextSession);
      if (
        shouldRebindChatSession(
          nextSession.context,
          context,
        )
      ) {
        setTurn(null);
        setMessages([]);
        return false;
      }

      if (!nextSession.turn) {
        setTurn(null);
        setMessages([]);
        return true;
      }

      if (!workspace.applyTurn(nextSession.turn)) return false;
      setTurn(nextSession.turn);
      setMessages(nextSession.turn.messages);
      return true;
    },
    [context, workspace],
  );

  useEffect(() => {
    const unsubscribeSession = subscribeToChatSession((nextSession) => {
        applySession(nextSession, currentProcedureKey.current);
      });
    const unsubscribeTurn = subscribeToChatTurn((nextTurn) => {
      const currentKey = currentProcedureKey.current;
      if (
        currentKey !== "__general__" &&
        nextTurn.procedure?.code !== currentKey
      ) return;
      setTurn(nextTurn);
      setMessages(nextTurn.messages);
      setSession((current) =>
        current ? { ...current, draft: nextTurn.draft, turn: nextTurn } : current,
      );
    });
    return () => {
      unsubscribeSession();
      unsubscribeTurn();
    };
  }, [applySession]);

  const createSession = useCallback(async () => {
    const requestProcedureKey = procedureKey;
    const operation = beginOperation();
    if (!operationIsCurrent(operation, requestProcedureKey)) {
      finishOperation(operation);
      return false;
    }

    try {
      const nextSession = await createChatSession(context, operation.controller.signal);
      if (!operationIsCurrent(operation, requestProcedureKey)) return false;
      return !shouldRebindChatSession(nextSession.context, context);
    } catch (requestError) {
      if (operationIsCurrent(operation, requestProcedureKey) && !isAbortError(requestError)) {
        setError(errorMessage(requestError, "Chưa thể khởi tạo phiên trợ lý."));
      }
      return false;
    } finally {
      finishOperation(operation);
    }
  }, [beginOperation, context, finishOperation, operationIsCurrent, procedureKey]);

  const recoverSession = useCallback(async () => {
    const requestProcedureKey = procedureKey;
    const operation = beginOperation();
    if (!operationIsCurrent(operation, requestProcedureKey)) {
      finishOperation(operation);
      return false;
    }

    try {
      const response = await fetch("/api/chat/session", {
        cache: "no-store",
        signal: operation.controller.signal,
      });
      if (!response.ok) return false;
      const nextSession = await readJson<ChatSession>(response);
      if (!operationIsCurrent(operation, requestProcedureKey)) return false;
      return applySession(nextSession, requestProcedureKey);
    } catch (requestError) {
      if (!isAbortError(requestError) && operationIsCurrent(operation, requestProcedureKey)) {
        setError(errorMessage(requestError, "Chưa thể khôi phục phiên trợ lý."));
      }
      return false;
    } finally {
      finishOperation(operation);
    }
  }, [applySession, beginOperation, finishOperation, operationIsCurrent, procedureKey]);

  const ensureSession = useCallback(async () => {
    if (session) return;

    const currentInitialization = initializing.current;
    if (currentInitialization?.procedureKey === procedureKey) {
      return currentInitialization.promise;
    }

    const initialization: Initialization = {
      procedureKey,
      promise: Promise.resolve(),
    };
    const task = (async () => {
      const operation = beginOperation();
      if (!operationIsCurrent(operation, procedureKey)) {
        finishOperation(operation);
        return;
      }

      setError(null);
      try {
        const response = await fetch("/api/chat/session", {
          cache: "no-store",
          signal: operation.controller.signal,
        });
        if (!operationIsCurrent(operation, procedureKey)) return;
        if (response.status === 404 || response.status === 410) {
          workspace.rebaseSession();
          if (await createSession()) await workspace.syncFields();
        } else {
          applySession(await readJson<ChatSession>(response), procedureKey);
        }
      } catch (requestError) {
        if (!isAbortError(requestError) && operationIsCurrent(operation, procedureKey)) {
          setError(errorMessage(requestError, "Chưa thể kết nối tới trợ lý."));
        }
      } finally {
        finishOperation(operation);
        if (initializing.current === initialization) initializing.current = null;
      }
    })();

    initialization.promise = task;
    initializing.current = initialization;
    return task;
  }, [applySession, beginOperation, createSession, finishOperation, operationIsCurrent, procedureKey, session, workspace]);

  const sendMessage = useCallback(
    async (message: string) => {
      const normalized = message.trim();
      if (!normalized) return;
      if (
        !session ||
        shouldRebindChatSession(session.context, context) ||
        shouldRebindChatWorkspace(
          turn?.draft ?? session.draft,
          context,
          workspace.state,
        )
      ) {
        setError("Hãy kết nối trợ lý với trang hiện tại trước khi gửi tin nhắn.");
        return;
      }

      const requestId = crypto.randomUUID();
      const requestProcedureKey = procedureKey;
      const operation = beginOperation();
      if (!operationIsCurrent(operation, requestProcedureKey)) {
        finishOperation(operation);
        return;
      }

      let expectedRevision = workspace.state.revision;
      latestMessageRequest.current = requestId;
      setError(null);
      setMessages((current) => [...current, { role: "user", content: normalized }]);
      try {
        const payload = JSON.stringify({
          message: normalized,
          client_turn_id: requestId,
          context,
        });
        const postMessage = () =>
          fetch("/api/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: payload,
            signal: operation.controller.signal,
          });

        let response = await postMessage();
        if (!operationIsCurrent(operation, requestProcedureKey)) return;
        if (response.status === 404 || response.status === 410) {
          workspace.rebaseSession();
          if (!(await createSession()) || !operationIsCurrent(operation, requestProcedureKey)) {
            return;
          }
          expectedRevision = await workspace.syncFields();
          if (!operationIsCurrent(operation, requestProcedureKey)) return;
          response = await postMessage();
        }
        const nextTurn = await readJson<ChatTurn>(response);
        if (
          !operationIsCurrent(operation, requestProcedureKey) ||
          latestMessageRequest.current !== requestId
        ) return;
        if (!workspace.applyTurn(nextTurn, expectedRevision)) {
          await recoverSession();
          return;
        }
        setTurn(nextTurn);
        setMessages(nextTurn.messages);
      } catch (requestError) {
        if (
          !isAbortError(requestError) &&
          operationIsCurrent(operation, requestProcedureKey) &&
          latestMessageRequest.current === requestId
        ) {
          if (
            requestError instanceof ChatRequestError &&
            requestError.code === "session_context_mismatch"
          ) {
            await recoverSession();
          }
          if (!operationIsCurrent(operation, requestProcedureKey)) return;
          setError(errorMessage(requestError, "Không thể gửi tin nhắn."));
        }
      } finally {
        finishOperation(operation);
      }
    },
    [
      beginOperation,
      context,
      createSession,
      finishOperation,
      operationIsCurrent,
      procedureKey,
      recoverSession,
      session,
      turn?.draft,
      workspace,
    ],
  );

  const resolveSuggestion = useCallback(
    async (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      value?: JsonValue,
    ) => {
      if (
        !session ||
        shouldRebindChatSession(session.context, context) ||
        shouldRebindChatWorkspace(
          turn?.draft ?? session.draft,
          context,
          workspace.state,
        )
      ) {
        setError("Đề xuất thuộc phiên khác. Hãy kết nối trợ lý với trang hiện tại.");
        return;
      }
      if (action !== "reject" && workspace.isDirty(suggestion.field_id)) {
        setError("Field này đã được bạn sửa trực tiếp trên form. AI không được ghi đè giá trị đó.");
        return;
      }

      // Carry the form value observed at request start through the Provider.
      // The reducer compares it with its latest state before applying the response,
      // so an in-flight accept/edit cannot overwrite a newer manual change.
      const guardedSuggestion = guardSuggestionForLocalField(
        suggestion,
        workspace.state.fields[suggestion.field_id],
      );

      const requestProcedureKey = procedureKey;
      const operation = beginOperation();
      if (!operationIsCurrent(operation, requestProcedureKey)) {
        finishOperation(operation);
        return;
      }

      setError(null);
      try {
        await workspace.runDraftMutation(async (currentRevision) => {
          if (!operationIsCurrent(operation, requestProcedureKey)) return;
          if (currentRevision !== suggestion.revision) {
            throw new ChatRequestError(
              "Đề xuất đã cũ; vui lòng dùng đề xuất mới nhất.",
              "stale_suggestion",
              409,
            );
          }
          const response = await fetch("/api/chat/suggestion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              suggestion_id: suggestion.id,
              action,
              ...(action === "edit" ? { value } : {}),
              expected_revision: currentRevision,
              context,
            }),
            signal: operation.controller.signal,
          });
          const nextTurn = await readJson<ChatTurn>(response);
          if (!operationIsCurrent(operation, requestProcedureKey)) return;
          workspace.applySuggestion(guardedSuggestion, action, nextTurn, value);
          setTurn(nextTurn);
          setMessages(nextTurn.messages);
        });
      } catch (requestError) {
        if (!operationIsCurrent(operation, requestProcedureKey) || isAbortError(requestError)) {
          return;
        }
        if (requestError instanceof ChatRequestError && requestError.status === 409) {
          if (requestError.code !== "session_context_mismatch") workspace.markStale();
          await recoverSession();
        }
        if (!operationIsCurrent(operation, requestProcedureKey)) return;
        setError(errorMessage(requestError, "Không thể cập nhật đề xuất."));
      } finally {
        finishOperation(operation);
      }
    },
    [
      beginOperation,
      context,
      finishOperation,
      operationIsCurrent,
      procedureKey,
      recoverSession,
      session,
      turn?.draft,
      workspace,
    ],
  );

  const resetSession = useCallback(async () => {
    const requestProcedureKey = procedureKey;
    const operation = beginOperation();
    if (!operationIsCurrent(operation, requestProcedureKey)) {
      finishOperation(operation);
      return;
    }

    setError(null);
    latestMessageRequest.current = null;
    try {
      await fetch("/api/chat/session", {
        method: "DELETE",
        signal: operation.controller.signal,
      });
      if (!operationIsCurrent(operation, requestProcedureKey)) return;
      workspace.resetWorkspace();
      setSession(null);
      setTurn(null);
      setMessages([]);
      await createSession();
    } catch (requestError) {
      if (!isAbortError(requestError) && operationIsCurrent(operation, requestProcedureKey)) {
        setError(errorMessage(requestError, "Không thể bắt đầu lại phiên trò chuyện."));
      }
    } finally {
      finishOperation(operation);
    }
  }, [beginOperation, createSession, finishOperation, operationIsCurrent, procedureKey, workspace]);

  const rebindSession = useCallback(async () => {
    const requestProcedureKey = procedureKey;
    const operation = beginOperation();
    if (!operationIsCurrent(operation, requestProcedureKey)) {
      finishOperation(operation);
      return;
    }

    setError(null);
    latestMessageRequest.current = null;
    try {
      await fetch("/api/chat/session", {
        method: "DELETE",
        signal: operation.controller.signal,
      });
      if (!operationIsCurrent(operation, requestProcedureKey)) return;
      workspace.rebaseSession();
      setSession(null);
      setTurn(null);
      setMessages([]);
      if (await createSession()) await workspace.syncFields();
    } catch (requestError) {
      if (!isAbortError(requestError) && operationIsCurrent(operation, requestProcedureKey)) {
        setError(errorMessage(requestError, "Không thể chuyển trợ lý sang trang hiện tại."));
      }
    } finally {
      finishOperation(operation);
    }
  }, [beginOperation, createSession, finishOperation, operationIsCurrent, procedureKey, workspace]);

  return {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    resolveSuggestion,
    rebindSession,
    resetSession,
  };
}
