import type { SttConfig } from "./stt-config";

const MAX_TRANSCRIPT_CHARACTERS = 4_000;
const MAX_PROVIDER_RESPONSE_BYTES = 64 * 1024;

export interface SttResult {
  language?: string;
  text: string;
  truncated: boolean;
}

export class SttProviderError extends Error {
  readonly kind:
    | "bad_audio"
    | "format_rejected"
    | "rate_limited"
    | "timeout"
    | "unavailable";

  constructor(
    kind:
      | "bad_audio"
      | "format_rejected"
      | "rate_limited"
      | "timeout"
      | "unavailable",
  ) {
    super(kind);
    this.name = "SttProviderError";
    this.kind = kind;
  }
}

function isTimeout(error: unknown) {
  return (
    error instanceof DOMException &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

function normalizeTranscript(value: unknown) {
  if (typeof value !== "string") return "";
  return value.replace(/[\0\u0001-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "").trim();
}

async function readProviderJson(response: Response) {
  const contentLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_PROVIDER_RESPONSE_BYTES) {
    throw new SttProviderError("unavailable");
  }
  if (!response.body) throw new SttProviderError("unavailable");

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_PROVIDER_RESPONSE_BYTES) {
        await reader.cancel();
        throw new SttProviderError("unavailable");
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof SttProviderError) throw error;
    throw new SttProviderError(isTimeout(error) ? "timeout" : "unavailable");
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  } catch {
    throw new SttProviderError("unavailable");
  }
}

export async function transcribeAudio(
  audio: Uint8Array,
  mimeType: string,
  filename: string,
  config: SttConfig,
): Promise<SttResult> {
  const form = new FormData();
  const ownedAudio = new Uint8Array(audio);
  form.append("file", new Blob([ownedAudio.buffer], { type: mimeType }), filename);
  form.append("model", config.model);
  if (config.sendLanguage && config.language) form.append("language", config.language);
  if (config.prompt) form.append("prompt", config.prompt);

  let response: Response;
  try {
    response = await fetch(config.endpoint, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
      body: form,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(config.timeoutMs),
    });
  } catch (error) {
    throw new SttProviderError(isTimeout(error) ? "timeout" : "unavailable");
  }

  if (!response.ok) {
    if (response.status === 429) throw new SttProviderError("rate_limited");
    if ([400, 413, 415, 422].includes(response.status)) {
      throw new SttProviderError("format_rejected");
    }
    throw new SttProviderError("unavailable");
  }

  const body = await readProviderJson(response);

  if (typeof body !== "object" || body === null || !("text" in body)) {
    throw new SttProviderError("unavailable");
  }

  const text = normalizeTranscript(body.text);
  if (!text) throw new SttProviderError("bad_audio");
  const language =
    "language" in body && typeof body.language === "string"
      ? body.language.replace(/[\r\n\0]/g, "").trim().slice(0, 80)
      : undefined;

  return {
    ...(language ? { language } : {}),
    text: text.slice(0, MAX_TRANSCRIPT_CHARACTERS),
    truncated: text.length > MAX_TRANSCRIPT_CHARACTERS,
  };
}
