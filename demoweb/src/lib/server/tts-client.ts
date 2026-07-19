import type { TtsConfig } from "./tts-config";

export class TtsProviderError extends Error {
  readonly kind: "invalid_input" | "rate_limited" | "timeout" | "unavailable";

  constructor(kind: "invalid_input" | "rate_limited" | "timeout" | "unavailable") {
    super(kind);
    this.name = "TtsProviderError";
    this.kind = kind;
  }
}

function isTimeout(error: unknown) {
  return (
    error instanceof DOMException &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

async function discardBody(response: Response) {
  try {
    await response.body?.cancel();
  } catch {
    // Provider error bodies are intentionally discarded and never logged.
  }
}

async function readLimitedAudio(response: Response, maximum: number) {
  const contentLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > maximum) {
    await discardBody(response);
    throw new TtsProviderError("unavailable");
  }
  if (!response.body) throw new TtsProviderError("unavailable");

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maximum) {
        await reader.cancel();
        throw new TtsProviderError("unavailable");
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof TtsProviderError) throw error;
    throw new TtsProviderError(isTimeout(error) ? "timeout" : "unavailable");
  } finally {
    reader.releaseLock();
  }

  if (total === 0) throw new TtsProviderError("unavailable");
  const audio = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    audio.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return audio;
}

export async function synthesizeSpeech(
  text: string,
  config: TtsConfig,
  externalSignal?: AbortSignal,
) {
  if (
    !text.trim() ||
    text.length > config.segmentCharacters ||
    /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text)
  ) {
    throw new TtsProviderError("invalid_input");
  }

  let response: Response;
  try {
    const timeoutSignal = AbortSignal.timeout(config.timeoutMs);
    response = await fetch(config.endpoint, {
      method: "POST",
      headers: {
        Accept: "audio/mpeg",
        Authorization: `Bearer ${config.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: config.model,
        input: text,
        voice: config.voice,
        instructions: config.instructions,
        response_format: config.format,
        speed: config.speed,
      }),
      cache: "no-store",
      redirect: "error",
      signal: externalSignal
        ? AbortSignal.any([externalSignal, timeoutSignal])
        : timeoutSignal,
    });
  } catch (error) {
    throw new TtsProviderError(isTimeout(error) ? "timeout" : "unavailable");
  }

  if (!response.ok) {
    await discardBody(response);
    if (response.status === 429) throw new TtsProviderError("rate_limited");
    if ([400, 413, 415, 422].includes(response.status)) {
      throw new TtsProviderError("invalid_input");
    }
    throw new TtsProviderError("unavailable");
  }

  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (contentType !== "audio/mpeg") {
    await discardBody(response);
    throw new TtsProviderError("unavailable");
  }
  return readLimitedAudio(response, config.maxResponseBytes);
}
