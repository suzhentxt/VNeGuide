import assert from "node:assert/strict";
import test from "node:test";

import {
  convertToWav,
  durationFromFfprobeJson,
  SttAudioConversionError,
  SttAudioValidationError,
  validateAudioDuration,
} from "./stt-audio.ts";

test("uses packet timestamps when a MediaRecorder container omits duration", () => {
  const duration = durationFromFfprobeJson(
    JSON.stringify({
      format: {},
      packets: [
        { pts_time: "0.000", duration_time: "0.020" },
        { pts_time: "1.240", duration_time: "0.020" },
      ],
    }),
  );
  assert.ok(Math.abs(duration - 1.26) < 0.001);
});

test("uses the longest authoritative duration reported by ffprobe", () => {
  const duration = durationFromFfprobeJson(
    JSON.stringify({
      format: { duration: "1.000" },
      packets: [{ pts_time: "1.240", duration_time: "0.020" }],
    }),
  );
  assert.equal(duration, 1.26);
});

test("rejects media whose measured duration exceeds the server limit", async () => {
  await assert.rejects(
    () =>
      validateAudioDuration(new Uint8Array([1]), 60, async () =>
        JSON.stringify({
          packets: [{ pts_time: "61.000", duration_time: "0.020" }],
        }),
      ),
    (error: unknown) =>
      error instanceof SttAudioValidationError && error.kind === "too_long",
  );
});

test("rejects probe output without a measurable audio duration", async () => {
  await assert.rejects(
    () => validateAudioDuration(new Uint8Array([1]), 60, async () => "{}"),
    (error: unknown) =>
      error instanceof SttAudioValidationError && error.kind === "unreadable",
  );
});

test("rejects a container duration when no audio packets were selected", () => {
  assert.throws(
    () => durationFromFfprobeJson(JSON.stringify({ format: { duration: "10.0" } })),
    (error: unknown) =>
      error instanceof SttAudioValidationError && error.kind === "unreadable",
  );
});

test("convertToWav returns the converter output on success", async () => {
  const fakeWav = new Uint8Array([82, 73, 70, 70]);
  const result = await convertToWav(new Uint8Array([1, 2, 3]), async () => fakeWav);
  assert.equal(result, fakeWav);
});

test("convertToWav surfaces converter failures as SttAudioConversionError", async () => {
  await assert.rejects(
    () =>
      convertToWav(new Uint8Array([1]), async () => {
        throw new SttAudioConversionError("ffmpeg exited with code 1");
      }),
    (error: unknown) =>
      error instanceof SttAudioConversionError &&
      /ffmpeg exited/.test(error.message),
  );
});
