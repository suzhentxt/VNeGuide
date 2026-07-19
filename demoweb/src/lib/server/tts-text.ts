const CONTROL_CHARACTERS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;
const MARKDOWN_LINK = /!?\[([^\]]*)\]\((?:[^()\s]+|\([^)]*\))*\)/g;

type JsonObject = Record<string, unknown>;

export class TtsTextError extends Error {
  readonly kind: "empty" | "invalid_session" | "not_found" | "too_long";

  constructor(kind: "empty" | "invalid_session" | "not_found" | "too_long") {
    super(kind);
    this.name = "TtsTextError";
    this.kind = kind;
  }
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function selectAssistantMessage(session: unknown, assistantIndex: number) {
  if (!isJsonObject(session)) throw new TtsTextError("invalid_session");
  const turn = session.turn;
  if (!isJsonObject(turn) || !Array.isArray(turn.messages)) {
    throw new TtsTextError("not_found");
  }

  let ordinal = 0;
  for (const message of turn.messages) {
    if (!isJsonObject(message) || typeof message.role !== "string") {
      throw new TtsTextError("invalid_session");
    }
    if (message.role !== "assistant") continue;
    if (ordinal === assistantIndex) {
      if (typeof message.content !== "string") {
        throw new TtsTextError("invalid_session");
      }
      return message.content;
    }
    ordinal += 1;
  }
  throw new TtsTextError("not_found");
}

export function normalizeAssistantText(text: string, maxCharacters: number) {
  if (text.length > maxCharacters) throw new TtsTextError("too_long");

  const normalized = text
    .normalize("NFC")
    .replace(CONTROL_CHARACTERS, "")
    .replace(MARKDOWN_LINK, "$1")
    .replace(/^\s{0,3}(?:#{1,6}|>|[-+*]|\d+[.)])\s+/gm, "")
    .replace(/```(?:[^\n]*)\n?/g, "")
    .replace(/[*_~`]+/g, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!normalized) throw new TtsTextError("empty");
  if (normalized.length > maxCharacters) throw new TtsTextError("too_long");
  return normalized;
}

function safeHardEnd(text: string, offset: number, maximum: number) {
  let end = Math.min(offset + maximum, text.length);
  const previous = text.charCodeAt(end - 1);
  const current = text.charCodeAt(end);
  if (previous >= 0xd800 && previous <= 0xdbff && current >= 0xdc00 && current <= 0xdfff) {
    end -= 1;
  }
  return end;
}

function segmentEnd(text: string, offset: number, maximum: number) {
  const hardEnd = safeHardEnd(text, offset, maximum);
  if (hardEnd === text.length) return hardEnd;

  const softStart = offset + Math.floor(maximum * 0.45);
  for (let index = hardEnd; index > softStart; index -= 1) {
    if (/\s/.test(text[index]) && /[.!?;:]/.test(text[index - 1])) return index;
  }
  for (let index = hardEnd; index > offset; index -= 1) {
    if (/\s/.test(text[index])) return index;
  }
  return hardEnd;
}

export function segmentAssistantText(text: string, maximum: number) {
  if (!Number.isSafeInteger(maximum) || maximum < 1) {
    throw new RangeError("maximum must be a positive integer");
  }

  const segments: string[] = [];
  let offset = 0;
  while (offset < text.length) {
    const end = segmentEnd(text, offset, maximum);
    const segment = text.slice(offset, end).trim();
    if (segment) segments.push(segment);
    offset = end;
    while (offset < text.length && /\s/.test(text[offset])) offset += 1;
  }
  if (segments.length === 0) throw new TtsTextError("empty");
  return segments;
}

export function assistantSpeechSegments(
  session: unknown,
  assistantIndex: number,
  maxMessageCharacters: number,
  segmentCharacters: number,
) {
  const text = selectAssistantMessage(session, assistantIndex);
  return segmentAssistantText(
    normalizeAssistantText(text, maxMessageCharacters),
    segmentCharacters,
  );
}
