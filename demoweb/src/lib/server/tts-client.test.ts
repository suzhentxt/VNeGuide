import assert from "node:assert/strict";
import test from "node:test";

import { synthesizeSpeech, TtsProviderError } from "./tts-client.ts";
import type { TtsConfig } from "./tts-config.ts";

function config(overrides: Partial<TtsConfig> = {}): TtsConfig {
  return {
    apiKey: "test-secret",
    endpoint: new URL("https://tts.example.test/v1/audio/speech"),
    format: "mp3",
    instructions: "Đọc bằng tiếng Việt rõ ràng.",
    maxMessageCharacters: 4_000,
    maxResponseBytes: 8 * 1024 * 1024,
    model: "gpt-4o-mini-tts",
    segmentCharacters: 600,
    speed: 1,
    timeoutMs: 60_000,
    voice: "marin",
    ...overrides,
  };
}

test("sends a bounded authenticated OpenAI-compatible Vietnamese speech request", async () => {
  const originalFetch = globalThis.fetch;
  let capturedAuthorization = "";
  let capturedAccept = "";
  let capturedRedirect: RequestRedirect | undefined;
  let capturedBody: Record<string, unknown> = {};

  globalThis.fetch = async (_input, init) => {
    const headers = new Headers(init?.headers);
    capturedAuthorization = headers.get("authorization") ?? "";
    capturedAccept = headers.get("accept") ?? "";
    capturedRedirect = init?.redirect;
    capturedBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
    return new Response(new Uint8Array([0x49, 0x44, 0x33, 1]), {
      headers: { "Content-Type": "audio/mpeg" },
    });
  };

  try {
    const audio = await synthesizeSpeech("Xin chào Việt Nam.", config());
    assert.deepEqual([...audio], [0x49, 0x44, 0x33, 1]);
    assert.equal(capturedAuthorization, "Bearer test-secret");
    assert.equal(capturedAccept, "audio/mpeg");
    assert.equal(capturedRedirect, "error");
    assert.deepEqual(capturedBody, {
      model: "gpt-4o-mini-tts",
      input: "Xin chào Việt Nam.",
      voice: "marin",
      instructions: "Đọc bằng tiếng Việt rõ ràng.",
      response_format: "mp3",
      speed: 1,
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects invalid input before contacting the provider", async () => {
  const originalFetch = globalThis.fetch;
  let called = false;
  globalThis.fetch = async () => {
    called = true;
    throw new Error("must not be called");
  };

  try {
    await assert.rejects(
      () => synthesizeSpeech("a".repeat(601), config()),
      (error: unknown) => error instanceof TtsProviderError && error.kind === "invalid_input",
    );
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("maps provider failures without reading or exposing error bodies", async (t) => {
  const originalFetch = globalThis.fetch;

  try {
    await t.test("rate limiting", async () => {
      globalThis.fetch = async () => new Response("private provider detail", { status: 429 });
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config()),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "rate_limited",
      );
    });

    await t.test("invalid input", async () => {
      globalThis.fetch = async () => new Response("private provider detail", { status: 422 });
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config()),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "invalid_input",
      );
    });

    await t.test("timeout", async () => {
      globalThis.fetch = async () => {
        throw new DOMException("timed out", "TimeoutError");
      };
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config()),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "timeout",
      );
    });

    await t.test("caller cancellation", async () => {
      globalThis.fetch = async (_input, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("cancelled", "AbortError")),
            { once: true },
          );
        });
      const controller = new AbortController();
      const request = synthesizeSpeech("Xin chào", config(), controller.signal);
      controller.abort();
      await assert.rejects(
        () => request,
        (error: unknown) => error instanceof TtsProviderError && error.kind === "timeout",
      );
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("requires MP3 and caps the provider audio response", async (t) => {
  const originalFetch = globalThis.fetch;

  try {
    await t.test("unexpected content type", async () => {
      globalThis.fetch = async () =>
        new Response(new Uint8Array([1]), { headers: { "Content-Type": "audio/wav" } });
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config()),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "unavailable",
      );
    });

    await t.test("oversized content length", async () => {
      globalThis.fetch = async () =>
        new Response(new Uint8Array([1]), {
          headers: { "Content-Length": "9", "Content-Type": "audio/mpeg" },
        });
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config({ maxResponseBytes: 8 })),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "unavailable",
      );
    });

    await t.test("oversized streamed body", async () => {
      globalThis.fetch = async () =>
        new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(new Uint8Array([1, 2, 3, 4, 5]));
              controller.enqueue(new Uint8Array([6, 7, 8, 9]));
              controller.close();
            },
          }),
          { headers: { "Content-Type": "audio/mpeg" } },
        );
      await assert.rejects(
        () => synthesizeSpeech("Xin chào", config({ maxResponseBytes: 8 })),
        (error: unknown) => error instanceof TtsProviderError && error.kind === "unavailable",
      );
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
