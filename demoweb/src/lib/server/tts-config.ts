import "server-only";

import { readFile, stat } from "node:fs/promises";
import { isAbsolute } from "node:path";

const DEFAULT_MODEL = "gpt-4o-mini-tts";
const DEFAULT_VOICE = "marin";
const DEFAULT_FORMAT = "mp3";
const DEFAULT_SPEED = 1;
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_SEGMENT_CHARACTERS = 600;
const DEFAULT_MAX_MESSAGE_CHARACTERS = 4_000;
const DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024;
const DEFAULT_INSTRUCTIONS =
  "Hãy đọc bằng tiếng Việt tự nhiên, rõ ràng, với tốc độ vừa phải. Giữ nguyên tên riêng, mã thủ tục, ngày tháng và các con số; không dịch sang ngôn ngữ khác.";
const MAX_SECRET_BYTES = 8 * 1024;
const MAX_INSTRUCTION_CHARACTERS = 1_000;

export interface TtsConfig {
  apiKey: string;
  endpoint: URL;
  format: "mp3";
  instructions: string;
  maxMessageCharacters: number;
  maxResponseBytes: number;
  model: string;
  segmentCharacters: number;
  speed: number;
  timeoutMs: number;
  voice: string;
}

export class TtsConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TtsConfigurationError";
  }
}

function enabled(value: string | undefined) {
  return value?.trim() === "1" || value?.trim().toLowerCase() === "true";
}

function boundedInteger(
  name: string,
  value: string | undefined,
  fallback: number,
  minimum: number,
  maximum: number,
) {
  if (!value?.trim()) return fallback;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new TtsConfigurationError(`${name} is outside the supported range`);
  }
  return parsed;
}

function boundedNumber(
  name: string,
  value: string | undefined,
  fallback: number,
  minimum: number,
  maximum: number,
) {
  if (!value?.trim()) return fallback;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < minimum || parsed > maximum) {
    throw new TtsConfigurationError(`${name} is outside the supported range`);
  }
  return parsed;
}

function boundedText(name: string, value: string, maximum: number) {
  const normalized = value.trim();
  if (
    !normalized ||
    normalized.length > maximum ||
    /[\u0000-\u001f\u007f]/.test(normalized)
  ) {
    throw new TtsConfigurationError(`${name} is invalid`);
  }
  return normalized;
}

function speechEndpoint(rawBaseUrl: string, allowInsecureHttp: boolean) {
  let baseUrl: URL;
  try {
    baseUrl = new URL(rawBaseUrl);
  } catch {
    throw new TtsConfigurationError("VNEGUIDE_TTS_BASE_URL must be a valid URL");
  }

  if (baseUrl.username || baseUrl.password || baseUrl.search || baseUrl.hash) {
    throw new TtsConfigurationError(
      "VNEGUIDE_TTS_BASE_URL must not contain credentials, a query, or a fragment",
    );
  }

  const loopbackHosts = new Set(["127.0.0.1", "localhost", "[::1]"]);
  if (
    baseUrl.protocol !== "https:" &&
    !(
      baseUrl.protocol === "http:" &&
      (allowInsecureHttp || loopbackHosts.has(baseUrl.hostname.toLowerCase()))
    )
  ) {
    throw new TtsConfigurationError(
      "VNEGUIDE_TTS_BASE_URL must use HTTPS outside a trusted development environment",
    );
  }

  if (!baseUrl.pathname.endsWith("/")) baseUrl.pathname += "/";
  return new URL("audio/speech", baseUrl);
}

async function readApiKeyFile(path: string) {
  const normalizedPath = path.trim();
  if (!isAbsolute(normalizedPath)) {
    throw new TtsConfigurationError("VNEGUIDE_TTS_API_KEY_FILE must be an absolute path");
  }

  try {
    const metadata = await stat(normalizedPath);
    if (!metadata.isFile() || metadata.size === 0 || metadata.size > MAX_SECRET_BYTES) {
      throw new TtsConfigurationError("The TTS API key file is empty or too large");
    }
    const apiKey = (await readFile(normalizedPath, "utf8")).trim();
    if (!apiKey || /[\r\n]/.test(apiKey)) {
      throw new TtsConfigurationError("The TTS API key file is invalid");
    }
    return apiKey;
  } catch (error) {
    if (error instanceof TtsConfigurationError) throw error;
    throw new TtsConfigurationError("The TTS API key file cannot be read");
  }
}

async function resolveApiKey() {
  const filePath = process.env.VNEGUIDE_TTS_API_KEY_FILE?.trim();
  if (filePath) return readApiKeyFile(filePath);
  const directKey = process.env.VNEGUIDE_TTS_API_KEY || process.env.VNEGUIDE_API_KEY;
  if (directKey) {
    const normalizedKey = directKey.trim();
    if (
      !normalizedKey ||
      Buffer.byteLength(normalizedKey, "utf8") > MAX_SECRET_BYTES ||
      /[\r\n\0]/.test(normalizedKey)
    ) {
      throw new TtsConfigurationError("The TTS API key environment value is invalid");
    }
    return normalizedKey;
  }
  throw new TtsConfigurationError(
    "VNEGUIDE_TTS_API_KEY_FILE (absolute path), VNEGUIDE_TTS_API_KEY, or VNEGUIDE_API_KEY must be configured when TTS is enabled",
  );
}

export function isTtsRequested() {
  return enabled(process.env.VNEGUIDE_TTS_ENABLED);
}

export async function getTtsConfig(): Promise<TtsConfig> {
  if (!isTtsRequested()) throw new TtsConfigurationError("TTS is disabled");

  const rawBaseUrl = process.env.VNEGUIDE_TTS_BASE_URL?.trim();
  if (!rawBaseUrl) {
    throw new TtsConfigurationError("VNEGUIDE_TTS_BASE_URL is required when TTS is enabled");
  }

  const model = boundedText(
    "VNEGUIDE_TTS_MODEL",
    process.env.VNEGUIDE_TTS_MODEL || DEFAULT_MODEL,
    200,
  );
  const voice = boundedText(
    "VNEGUIDE_TTS_VOICE",
    process.env.VNEGUIDE_TTS_VOICE || DEFAULT_VOICE,
    100,
  );
  const instructions = boundedText(
    "VNEGUIDE_TTS_INSTRUCTIONS",
    process.env.VNEGUIDE_TTS_INSTRUCTIONS || DEFAULT_INSTRUCTIONS,
    MAX_INSTRUCTION_CHARACTERS,
  );
  const format = (process.env.VNEGUIDE_TTS_FORMAT?.trim().toLowerCase() ||
    DEFAULT_FORMAT) as string;
  if (format !== "mp3") {
    throw new TtsConfigurationError("VNEGUIDE_TTS_FORMAT must be mp3");
  }

  const timeoutSeconds = boundedInteger(
    "VNEGUIDE_TTS_TIMEOUT_SECONDS",
    process.env.VNEGUIDE_TTS_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_MS / 1000,
    5,
    120,
  );
  const segmentCharacters = boundedInteger(
    "VNEGUIDE_TTS_SEGMENT_CHARACTERS",
    process.env.VNEGUIDE_TTS_SEGMENT_CHARACTERS,
    DEFAULT_SEGMENT_CHARACTERS,
    200,
    1_000,
  );
  const maxMessageCharacters = boundedInteger(
    "VNEGUIDE_TTS_MAX_MESSAGE_CHARACTERS",
    process.env.VNEGUIDE_TTS_MAX_MESSAGE_CHARACTERS,
    DEFAULT_MAX_MESSAGE_CHARACTERS,
    600,
    DEFAULT_MAX_MESSAGE_CHARACTERS,
  );
  if (segmentCharacters > maxMessageCharacters) {
    throw new TtsConfigurationError(
      "VNEGUIDE_TTS_SEGMENT_CHARACTERS must not exceed VNEGUIDE_TTS_MAX_MESSAGE_CHARACTERS",
    );
  }

  return {
    apiKey: await resolveApiKey(),
    endpoint: speechEndpoint(
      rawBaseUrl,
      enabled(process.env.VNEGUIDE_TTS_ALLOW_INSECURE_HTTP),
    ),
    format,
    instructions,
    maxMessageCharacters,
    maxResponseBytes: boundedInteger(
      "VNEGUIDE_TTS_MAX_RESPONSE_BYTES",
      process.env.VNEGUIDE_TTS_MAX_RESPONSE_BYTES,
      DEFAULT_MAX_RESPONSE_BYTES,
      64 * 1024,
      DEFAULT_MAX_RESPONSE_BYTES,
    ),
    model,
    segmentCharacters,
    speed: boundedNumber(
      "VNEGUIDE_TTS_SPEED",
      process.env.VNEGUIDE_TTS_SPEED,
      DEFAULT_SPEED,
      0.25,
      4,
    ),
    timeoutMs: timeoutSeconds * 1000,
    voice,
  };
}
