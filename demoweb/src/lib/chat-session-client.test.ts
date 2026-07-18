import assert from "node:assert/strict";
import test from "node:test";

import {
  createChatSession,
  subscribeToChatSession,
} from "./chat-session-client.ts";
import type { ChatSession } from "../types/chat.ts";

const session: ChatSession = {
  expires_in_seconds: 1_800,
  context: {
    procedure_code: "1.004194",
    procedure_title: "Đăng ký tạm trú",
    route: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru",
  },
  context_supported: true,
  scope_warning: null,
  draft: {
    values: {},
    revision: 0,
    confirmed_fields: [],
    dirty_fields: [],
    pack_version: "2.0.0",
  },
  turn: null,
};

test("concurrent creators for one procedure share a single request", async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalls = 0;
  let resolveFetch: ((response: Response) => void) | undefined;
  globalThis.fetch = (() => {
    fetchCalls += 1;
    return new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
  }) as typeof fetch;

  const published: ChatSession[] = [];
  const unsubscribe = subscribeToChatSession((nextSession) => published.push(nextSession));
  try {
    const first = createChatSession(session.context!);
    const second = createChatSession(session.context!);

    assert.equal(fetchCalls, 1);
    resolveFetch?.(
      new Response(JSON.stringify(session), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const [firstResult, secondResult] = await Promise.all([first, second]);
    assert.deepEqual(firstResult, session);
    assert.deepEqual(secondResult, session);
    assert.equal(published.length, 1);
  } finally {
    unsubscribe();
    globalThis.fetch = originalFetch;
  }
});

test("aborting one joined caller keeps the shared creation alive", async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalls = 0;
  let underlyingAborted = false;
  let resolveFetch: ((response: Response) => void) | undefined;
  globalThis.fetch = ((_input, init) => {
    fetchCalls += 1;
    init?.signal?.addEventListener("abort", () => {
      underlyingAborted = true;
    });
    return new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
  }) as typeof fetch;

  try {
    const controller = new AbortController();
    const cancelledCaller = createChatSession(session.context!, controller.signal);
    const activeCaller = createChatSession(session.context!);
    controller.abort();

    await assert.rejects(cancelledCaller, { name: "AbortError" });
    assert.equal(underlyingAborted, false);
    resolveFetch?.(
      new Response(JSON.stringify(session), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    assert.deepEqual(await activeCaller, session);
    assert.equal(fetchCalls, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("an aborted creator does not poison the next creation", async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalls = 0;
  globalThis.fetch = ((_input, init) => {
    fetchCalls += 1;
    if (fetchCalls === 1) {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }
    return Promise.resolve(
      new Response(JSON.stringify(session), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }) as typeof fetch;

  try {
    const controller = new AbortController();
    const aborted = createChatSession(session.context!, controller.signal);
    controller.abort();
    const replacement = createChatSession(session.context!);

    await assert.rejects(aborted, { name: "AbortError" });
    assert.deepEqual(await replacement, session);
    assert.equal(fetchCalls, 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
