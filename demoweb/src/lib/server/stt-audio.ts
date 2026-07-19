import { spawn } from "node:child_process";

const DURATION_PROBE_TIMEOUT_MS = 10_000;
const MAX_PROBE_RESPONSE_BYTES = 1024 * 1024;
const CONVERT_TIMEOUT_MS = 30_000;
const MAX_CONVERT_OUTPUT_BYTES = 32 * 1024 * 1024;

export class SttAudioValidationError extends Error {
  readonly kind: "unreadable" | "too_long";

  constructor(kind: "unreadable" | "too_long") {
    super(kind);
    this.name = "SttAudioValidationError";
    this.kind = kind;
  }
}

export class SttAudioConversionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SttAudioConversionError";
  }
}

function runFfprobe(audio: Uint8Array) {
  return new Promise<string>((resolve, reject) => {
    const child = spawn(
      "ffprobe",
      [
        "-v",
        "error",
        "-protocol_whitelist",
        "pipe",
        "-select_streams",
        "a:0",
        "-show_entries",
        "format=duration:packet=pts_time,duration_time",
        "-of",
        "json",
        "-i",
        "pipe:0",
      ],
      { stdio: ["pipe", "pipe", "ignore"], windowsHide: true },
    );
    const chunks: Buffer[] = [];
    let total = 0;
    let settled = false;

    const finish = (error?: Error, output?: string) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (error) reject(error);
      else resolve(output ?? "");
    };
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      finish(new SttAudioValidationError("unreadable"));
    }, DURATION_PROBE_TIMEOUT_MS);
    timeout.unref?.();

    child.once("error", () => finish(new SttAudioValidationError("unreadable")));
    child.stdout.on("data", (chunk: Buffer) => {
      total += chunk.byteLength;
      if (total > MAX_PROBE_RESPONSE_BYTES) {
        child.kill("SIGKILL");
        finish(new SttAudioValidationError("unreadable"));
        return;
      }
      chunks.push(chunk);
    });
    child.once("close", (code) => {
      if (code !== 0) {
        finish(new SttAudioValidationError("unreadable"));
        return;
      }
      finish(undefined, Buffer.concat(chunks, total).toString("utf8"));
    });
    child.stdin.on("error", () => undefined);
    child.stdin.end(Buffer.from(audio.buffer, audio.byteOffset, audio.byteLength));
  });
}

function finiteNonNegative(value: unknown) {
  if (typeof value !== "string" && typeof value !== "number") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

export function durationFromFfprobeJson(output: string) {
  let body: unknown;
  try {
    body = JSON.parse(output);
  } catch {
    throw new SttAudioValidationError("unreadable");
  }
  if (typeof body !== "object" || body === null) {
    throw new SttAudioValidationError("unreadable");
  }

  const document = body as {
    format?: { duration?: unknown };
    packets?: Array<{ duration_time?: unknown; pts_time?: unknown }>;
  };
  let packetDuration = 0;
  let hasAudioPacket = false;
  if (Array.isArray(document.packets)) {
    for (const packet of document.packets) {
      const pts = finiteNonNegative(packet?.pts_time);
      if (pts === undefined) continue;
      hasAudioPacket = true;
      const packetLength = finiteNonNegative(packet.duration_time) ?? 0;
      packetDuration = Math.max(packetDuration, pts + packetLength);
    }
  }
  if (!hasAudioPacket) {
    throw new SttAudioValidationError("unreadable");
  }
  const duration = Math.max(
    finiteNonNegative(document.format?.duration) ?? 0,
    packetDuration,
  );
  if (!Number.isFinite(duration) || duration <= 0) {
    throw new SttAudioValidationError("unreadable");
  }
  return duration;
}

/** Measure duration from decoded packet timestamps, never from a browser header alone. */
export async function validateAudioDuration(
  audio: Uint8Array,
  maxDurationSeconds: number,
  probe: (bytes: Uint8Array) => Promise<string> = runFfprobe,
) {
  let output: string;
  try {
    output = await probe(audio);
  } catch (error) {
    if (error instanceof SttAudioValidationError) throw error;
    throw new SttAudioValidationError("unreadable");
  }

  const durationSeconds = durationFromFfprobeJson(output);
  if (durationSeconds > maxDurationSeconds) {
    throw new SttAudioValidationError("too_long");
  }
  return durationSeconds;
}

/**
 * Convert any audio container ffmpeg can decode into 16 kHz mono PCM WAV.
 *
 * Local ASR providers (e.g. Qwen3-ASR served by vLLM) typically accept only WAV
 * PCM input, while browsers record in WebM/Opus. OpenAI-compatible endpoints
 * accept many containers, so conversion is opt-in via ``VNEGUIDE_STT_CONVERT_TO_WAV``.
 */
export function convertToWav(
  audio: Uint8Array,
  runFfmpeg: (input: Uint8Array) => Promise<Uint8Array> = runFfmpegConvert,
): Promise<Uint8Array> {
  return runFfmpeg(audio);
}

function runFfmpegConvert(input: Uint8Array): Promise<Uint8Array> {
  return new Promise<Uint8Array>((resolve, reject) => {
    const child = spawn(
      "ffmpeg",
      [
        "-hide_banner",
        "-loglevel",
        "error",
        "-protocol_whitelist",
        "pipe",
        "-i",
        "pipe:0",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        "pipe:1",
      ],
      { stdio: ["pipe", "pipe", "pipe"], windowsHide: true },
    );
    const chunks: Buffer[] = [];
    let total = 0;
    let settled = false;
    let stderrText = "";

    const finish = (error?: Error, output?: Uint8Array) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (error) reject(error);
      else resolve(output ?? new Uint8Array(0));
    };
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      finish(new SttAudioConversionError("ffmpeg conversion timed out"));
    }, CONVERT_TIMEOUT_MS);
    timeout.unref?.();

    child.once("error", () =>
      finish(new SttAudioConversionError("ffmpeg is not available")),
    );
    child.stdout.on("data", (chunk: Buffer) => {
      total += chunk.byteLength;
      if (total > MAX_CONVERT_OUTPUT_BYTES) {
        child.kill("SIGKILL");
        finish(new SttAudioConversionError("converted audio exceeds size limit"));
        return;
      }
      chunks.push(chunk);
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      stderrText += chunk.toString("utf8");
    });
    child.once("close", (code) => {
      if (code !== 0) {
        finish(
          new SttAudioConversionError(
            stderrText.trim() || `ffmpeg exited with code ${code}`,
          ),
        );
        return;
      }
      finish(undefined, Buffer.concat(chunks, total));
    });
    child.stdin.on("error", () => undefined);
    child.stdin.end(Buffer.from(input.buffer, input.byteOffset, input.byteLength));
  });
}
