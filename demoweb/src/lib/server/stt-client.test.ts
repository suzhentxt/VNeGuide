import assert from "node:assert/strict";
import test from "node:test";

import { SttProviderError, transcribeAudio } from "./stt-client.ts";
import type { SttConfig } from "./stt-config.ts";

function config(overrides: Partial<SttConfig> = {}): SttConfig {
  return {
    endpoint: new URL("https://stt.example.test/v1/audio/transcriptions"),
    maxBytes: 10 * 1024 * 1024,
    maxDurationSeconds: 60,
    model: "Qwen/Qwen3-ASR-1.7B",
    timeoutMs: 180_000,
    ...overrides,
  };
}

test("forwards audio as an authenticated OpenAI-compatible transcription request", async () => {
  const originalFetch = globalThis.fetch;
  let capturedAuthorization = "";
  let capturedModel = "";
  let capturedFilename = "";
  let capturedLanguage = "";

  globalThis.fetch = async (_input, init) => {
    capturedAuthorization = new Headers(init?.headers).get("authorization") ?? "";
    const form = init?.body as FormData;
    capturedModel = String(form.get("model"));
    capturedLanguage = String(form.get("language") ?? "");
    const file = form.get("file") as File;
    capturedFilename = file.name;
    return Response.json({ text: "  Xin chào\u0000  ", language: "Vietnamese" });
  };

  try {
    const result = await transcribeAudio(
      new Uint8Array([1, 2, 3]),
      "audio/webm",
      "recording.webm",
      config({ apiKey: "test-secret", language: "vi" }),
    );

    assert.deepEqual(result, {
      language: "Vietnamese",
      text: "Xin chào",
      truncated: false,
    });
    assert.equal(capturedAuthorization, "Bearer test-secret");
    assert.equal(capturedModel, "Qwen/Qwen3-ASR-1.7B");
    assert.equal(capturedFilename, "recording.webm");
    assert.equal(capturedLanguage, "vi");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("bounds transcripts to the chat input contract", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ text: "a".repeat(4_001) });

  try {
    const result = await transcribeAudio(
      new Uint8Array([1]),
      "audio/wav",
      "recording.wav",
      config(),
    );
    assert.equal(result.text.length, 4_000);
    assert.equal(result.truncated, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("maps invalid audio, rate limiting, and timeouts without exposing provider bodies", async (t) => {
  const originalFetch = globalThis.fetch;

  await t.test("invalid audio", async () => {
    globalThis.fetch = async () => new Response("provider detail", { status: 415 });
    await assert.rejects(
      () => transcribeAudio(new Uint8Array([1]), "audio/wav", "recording.wav", config()),
      (error: unknown) => error instanceof SttProviderError && error.kind === "bad_audio",
    );
  });

  await t.test("rate limited", async () => {
    globalThis.fetch = async () => new Response(null, { status: 429 });
    await assert.rejects(
      () => transcribeAudio(new Uint8Array([1]), "audio/wav", "recording.wav", config()),
      (error: unknown) => error instanceof SttProviderError && error.kind === "rate_limited",
    );
  });

  await t.test("timeout", async () => {
    globalThis.fetch = async () => {
      throw new DOMException("timed out", "TimeoutError");
    };
    await assert.rejects(
      () => transcribeAudio(new Uint8Array([1]), "audio/wav", "recording.wav", config()),
      (error: unknown) => error instanceof SttProviderError && error.kind === "timeout",
    );
  });

  globalThis.fetch = originalFetch;
});

test("caps provider responses and preserves body-read timeouts", async (t) => {
  const originalFetch = globalThis.fetch;

  await t.test("oversized response", async () => {
    globalThis.fetch = async () =>
      Response.json({ text: "a".repeat(70 * 1024) });
    await assert.rejects(
      () => transcribeAudio(new Uint8Array([1]), "audio/wav", "recording.wav", config()),
      (error: unknown) => error instanceof SttProviderError && error.kind === "unavailable",
    );
  });

  await t.test("timeout while reading body", async () => {
    globalThis.fetch = async () =>
      new Response(
        new ReadableStream({
          start(controller) {
            controller.error(new DOMException("timed out", "TimeoutError"));
          },
        }),
      );
    await assert.rejects(
      () => transcribeAudio(new Uint8Array([1]), "audio/wav", "recording.wav", config()),
      (error: unknown) => error instanceof SttProviderError && error.kind === "timeout",
    );
  });

  globalThis.fetch = originalFetch;
});
