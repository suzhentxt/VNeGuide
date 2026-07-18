import "server-only";

import { readFile, stat } from "node:fs/promises";
import { isAbsolute } from "node:path";

const DEFAULT_MODEL = "Qwen/Qwen3-ASR-1.7B";
const DEFAULT_TIMEOUT_MS = 180_000;
const DEFAULT_MAX_BYTES = 10 * 1024 * 1024;
const DEFAULT_MAX_DURATION_SECONDS = 60;
const MAX_SECRET_BYTES = 8 * 1024;

export interface SttConfig {
  apiKey?: string;
  endpoint: URL;
  language?: string;
  maxBytes: number;
  maxDurationSeconds: number;
  model: string;
  timeoutMs: number;
}

export class SttConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SttConfigurationError";
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
    throw new SttConfigurationError(`${name} is outside the supported range`);
  }
  return parsed;
}

function transcriptionEndpoint(rawBaseUrl: string, allowInsecureHttp: boolean) {
  let baseUrl: URL;
  try {
    baseUrl = new URL(rawBaseUrl);
  } catch {
    throw new SttConfigurationError("VNEGUIDE_STT_BASE_URL must be a valid URL");
  }

  if (baseUrl.username || baseUrl.password || baseUrl.search || baseUrl.hash) {
    throw new SttConfigurationError(
      "VNEGUIDE_STT_BASE_URL must not contain credentials, a query, or a fragment",
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
    throw new SttConfigurationError(
      "VNEGUIDE_STT_BASE_URL must use HTTPS outside a trusted development environment",
    );
  }

  if (!baseUrl.pathname.endsWith("/")) {
    baseUrl.pathname += "/";
  }
  return new URL("audio/transcriptions", baseUrl);
}

async function readApiKey(path: string | undefined) {
  const normalizedPath = path?.trim();
  if (!normalizedPath) return undefined;
  if (!isAbsolute(normalizedPath)) {
    throw new SttConfigurationError("VNEGUIDE_STT_API_KEY_FILE must be an absolute path");
  }

  try {
    const metadata = await stat(normalizedPath);
    if (!metadata.isFile() || metadata.size === 0 || metadata.size > MAX_SECRET_BYTES) {
      throw new SttConfigurationError("The STT API key file is empty or too large");
    }
    const apiKey = (await readFile(normalizedPath, "utf8")).trim();
    if (!apiKey || /[\r\n]/.test(apiKey)) {
      throw new SttConfigurationError("The STT API key file is invalid");
    }
    return apiKey;
  } catch (error) {
    if (error instanceof SttConfigurationError) throw error;
    throw new SttConfigurationError("The STT API key file cannot be read");
  }
}

export function isSttRequested() {
  return enabled(process.env.VNEGUIDE_STT_ENABLED);
}

export async function getSttConfig(): Promise<SttConfig> {
  if (!isSttRequested()) {
    throw new SttConfigurationError("STT is disabled");
  }

  const rawBaseUrl = process.env.VNEGUIDE_STT_BASE_URL?.trim();
  if (!rawBaseUrl) {
    throw new SttConfigurationError("VNEGUIDE_STT_BASE_URL is required when STT is enabled");
  }

  const model = process.env.VNEGUIDE_STT_MODEL?.trim() || DEFAULT_MODEL;
  if (model.length > 200 || /[\r\n\0]/.test(model)) {
    throw new SttConfigurationError("VNEGUIDE_STT_MODEL is invalid");
  }

  const rawLanguage = process.env.VNEGUIDE_STT_LANGUAGE?.trim().toLowerCase();
  if (rawLanguage && !/^[a-z]{2}$/.test(rawLanguage)) {
    throw new SttConfigurationError("VNEGUIDE_STT_LANGUAGE must be an ISO-639-1 code");
  }

  const timeoutSeconds = boundedInteger(
    "VNEGUIDE_STT_TIMEOUT_SECONDS",
    process.env.VNEGUIDE_STT_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_MS / 1000,
    5,
    180,
  );
  const maxBytes = boundedInteger(
    "VNEGUIDE_STT_MAX_BYTES",
    process.env.VNEGUIDE_STT_MAX_BYTES,
    DEFAULT_MAX_BYTES,
    64 * 1024,
    DEFAULT_MAX_BYTES,
  );
  const maxDurationSeconds = boundedInteger(
    "VNEGUIDE_STT_MAX_DURATION_SECONDS",
    process.env.VNEGUIDE_STT_MAX_DURATION_SECONDS,
    DEFAULT_MAX_DURATION_SECONDS,
    1,
    DEFAULT_MAX_DURATION_SECONDS,
  );

  return {
    apiKey: await readApiKey(process.env.VNEGUIDE_STT_API_KEY_FILE),
    endpoint: transcriptionEndpoint(
      rawBaseUrl,
      enabled(process.env.VNEGUIDE_STT_ALLOW_INSECURE_HTTP),
    ),
    ...(rawLanguage ? { language: rawLanguage } : {}),
    maxBytes,
    maxDurationSeconds,
    model,
    timeoutMs: timeoutSeconds * 1000,
  };
}

export const sttPublicDefaults = {
  maxBytes: DEFAULT_MAX_BYTES,
  maxDurationSeconds: DEFAULT_MAX_DURATION_SECONDS,
} as const;
