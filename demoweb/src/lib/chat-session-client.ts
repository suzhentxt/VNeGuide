"use client";

import { getChatContextKey } from "../data/chat-scope.ts";
import type {
  ChatApiError,
  ChatSession,
  ChatSessionContext,
  ChatTurn,
} from "../types/chat.ts";

interface PendingCreation {
  controller: AbortController;
  consumers: Set<symbol>;
  promise: Promise<ChatSession>;
  settled: boolean;
}

const pendingCreations = new Map<string, PendingCreation>();
const sessionSubscribers = new Set<(session: ChatSession) => void>();
const turnSubscribers = new Set<(turn: ChatTurn) => void>();

export function subscribeToChatSession(
  subscriber: (session: ChatSession) => void,
): () => void {
  sessionSubscribers.add(subscriber);
  return () => sessionSubscribers.delete(subscriber);
}

export function publishChatSession(session: ChatSession) {
  for (const subscriber of sessionSubscribers) {
    try {
      subscriber(session);
    } catch {
      // One UI consumer must not prevent the other consumers from receiving
      // the newly established browser session.
    }
  }
}

export function subscribeToChatTurn(
  subscriber: (turn: ChatTurn) => void,
): () => void {
  turnSubscribers.add(subscriber);
  return () => turnSubscribers.delete(subscriber);
}

export function publishChatTurn(turn: ChatTurn) {
  for (const subscriber of turnSubscribers) {
    try {
      subscriber(turn);
    } catch {
      // A stale UI subscriber must not prevent the form owner from completing.
    }
  }
}

function abortError() {
  return new DOMException("Aborted", "AbortError");
}

function startCreation(
  key: string,
  context: ChatSessionContext,
): PendingCreation {
  const controller = new AbortController();
  const entry: PendingCreation = {
    controller,
    consumers: new Set(),
    promise: Promise.resolve(null as unknown as ChatSession),
    settled: false,
  };

  entry.promise = (async () => {
    const response = await fetch("/api/chat/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context }),
      signal: controller.signal,
    });
    const body = (await response.json()) as ChatSession | ChatApiError;
    if (!response.ok) {
      const apiError = body as ChatApiError;
      throw new Error(apiError.error?.message || "Không thể khởi tạo phiên trợ lý.");
    }
    const session = body as ChatSession;
    publishChatSession(session);
    return session;
  })();

  pendingCreations.set(key, entry);
  void entry.promise
    .finally(() => {
      entry.settled = true;
      if (pendingCreations.get(key) === entry) pendingCreations.delete(key);
    })
    .catch(() => undefined);
  return entry;
}

function joinCreation(
  entry: PendingCreation,
  signal?: AbortSignal,
): Promise<ChatSession> {
  if (signal?.aborted) return Promise.reject(abortError());

  const consumer = Symbol("chat-session-consumer");
  entry.consumers.add(consumer);
  return new Promise<ChatSession>((resolve, reject) => {
    let completed = false;
    const release = () => {
      signal?.removeEventListener("abort", onAbort);
      entry.consumers.delete(consumer);
      if (!entry.settled && entry.consumers.size === 0) entry.controller.abort();
    };
    const onAbort = () => {
      if (completed) return;
      completed = true;
      release();
      reject(abortError());
    };

    signal?.addEventListener("abort", onAbort, { once: true });
    void entry.promise.then(
      (session) => {
        if (completed) return;
        completed = true;
        release();
        resolve(session);
      },
      (error: unknown) => {
        if (completed) return;
        completed = true;
        release();
        reject(error);
      },
    );
  });
}

export function createChatSession(
  context: ChatSessionContext,
  signal?: AbortSignal,
): Promise<ChatSession> {
  if (signal?.aborted) return Promise.reject(abortError());

  const key = getChatContextKey(context);
  let entry = pendingCreations.get(key);
  if (!entry || entry.controller.signal.aborted) {
    entry = startCreation(key, context);
  }
  return joinCreation(entry, signal);
}
