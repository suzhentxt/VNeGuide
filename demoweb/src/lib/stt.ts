export const MAX_CHAT_DRAFT_LENGTH = 4_000;
export const DEFAULT_STT_MAX_DURATION_SECONDS = 60;
export const DEFAULT_STT_MAX_BYTES = 10 * 1024 * 1024;

export const RECORDING_MIME_TYPE_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/ogg",
  "audio/mp4",
] as const;

const AUDIO_MIME_TYPES = new Set([
  "audio/aac",
  "audio/flac",
  "audio/mp4",
  "audio/mp3",
  "audio/mpeg",
  "audio/ogg",
  "audio/wav",
  "audio/webm",
  "audio/x-m4a",
  "audio/x-wav",
]);

const AUDIO_MIME_TYPE_BY_EXTENSION: Record<string, string> = {
  ".aac": "audio/aac",
  ".flac": "audio/flac",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
  ".mp4": "audio/mp4",
  ".oga": "audio/ogg",
  ".ogg": "audio/ogg",
  ".wav": "audio/wav",
  ".webm": "audio/webm",
};

export const AUDIO_FILE_ACCEPT = [
  ...AUDIO_MIME_TYPES,
  ...Object.keys(AUDIO_MIME_TYPE_BY_EXTENSION),
].join(",");

export function chooseRecordingMimeType(
  isTypeSupported: (mimeType: string) => boolean,
): string | null {
  for (const mimeType of RECORDING_MIME_TYPE_CANDIDATES) {
    try {
      if (isTypeSupported(mimeType)) return mimeType;
    } catch {
      // Some partial MediaRecorder implementations throw for unknown codecs.
    }
  }
  return null;
}

export function resolveAudioMimeType(
  declaredMimeType: string | undefined,
  fileName = "",
): string | null {
  const normalizedMimeType = declaredMimeType
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (normalizedMimeType && AUDIO_MIME_TYPES.has(normalizedMimeType)) {
    if (normalizedMimeType === "audio/x-m4a") return "audio/mp4";
    if (normalizedMimeType === "audio/mp3") return "audio/mpeg";
    return normalizedMimeType;
  }

  const lowerName = fileName.trim().toLowerCase();
  const extension = Object.keys(AUDIO_MIME_TYPE_BY_EXTENSION).find((candidate) =>
    lowerName.endsWith(candidate),
  );
  return extension ? AUDIO_MIME_TYPE_BY_EXTENSION[extension] : null;
}

export function mergeTranscriptIntoDraft(
  draft: string,
  transcript: string,
  maxLength = MAX_CHAT_DRAFT_LENGTH,
): string {
  if (maxLength <= 0) return "";

  const cleanTranscript = transcript.trim();
  if (!cleanTranscript || draft.length >= maxLength) {
    return draft.slice(0, maxLength);
  }

  const separator = draft.length > 0 && !/\s$/u.test(draft) ? " " : "";
  return `${draft}${separator}${cleanTranscript}`.slice(0, maxLength);
}

export function parsePositiveLimit(
  value: unknown,
  fallback: number,
  maximum: number,
): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.min(Math.floor(value), maximum)
    : fallback;
}
