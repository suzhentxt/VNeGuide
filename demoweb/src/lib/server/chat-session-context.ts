import "server-only";

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function withoutClientContext(payload: unknown): {
  context: unknown;
  forwardedPayload: unknown;
} {
  if (!isJsonObject(payload)) {
    return { context: null, forwardedPayload: payload };
  }

  const { context, ...forwardedPayload } = payload;
  return { context: context ?? null, forwardedPayload };
}
