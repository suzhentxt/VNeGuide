export const DEFAULT_TTS_MAX_AUDIO_BYTES = 8 * 1024 * 1024;
export const MAX_TTS_SEGMENTS = 100;

export interface TtsSegmentMetadata {
  segmentCount: number;
  segmentIndex: number;
}

export function getAssistantMessageOrdinals(
  messages: readonly { role: string }[],
): Array<number | null> {
  let assistantIndex = 0;
  return messages.map((message) =>
    message.role === "assistant" ? assistantIndex++ : null,
  );
}

function parseBoundedInteger(
  rawValue: string | null,
  minimum: number,
  maximum: number,
): number | null {
  if (!rawValue || !/^\d+$/u.test(rawValue)) return null;
  const value = Number(rawValue);
  return Number.isSafeInteger(value) && value >= minimum && value <= maximum
    ? value
    : null;
}

export function isMpegAudioContentType(contentType: string | null): boolean {
  return contentType?.split(";", 1)[0].trim().toLowerCase() === "audio/mpeg";
}

export function parseTtsSegmentMetadata(
  headers: Pick<Headers, "get">,
  requestedSegmentIndex: number,
): TtsSegmentMetadata | null {
  const segmentCount = parseBoundedInteger(
    headers.get("X-VNeGuide-TTS-Segment-Count"),
    1,
    MAX_TTS_SEGMENTS,
  );
  const segmentIndex = parseBoundedInteger(
    headers.get("X-VNeGuide-TTS-Segment-Index"),
    0,
    MAX_TTS_SEGMENTS - 1,
  );

  if (
    segmentCount === null ||
    segmentIndex === null ||
    segmentIndex !== requestedSegmentIndex ||
    segmentIndex >= segmentCount
  ) {
    return null;
  }

  return { segmentCount, segmentIndex };
}

export function getNextTtsSegmentIndex(
  metadata: TtsSegmentMetadata,
): number | null {
  const nextIndex = metadata.segmentIndex + 1;
  return nextIndex < metadata.segmentCount ? nextIndex : null;
}

export function parseTtsContentLength(
  rawValue: string | null,
  maximum = DEFAULT_TTS_MAX_AUDIO_BYTES,
): number | null {
  return parseBoundedInteger(rawValue, 1, maximum);
}
