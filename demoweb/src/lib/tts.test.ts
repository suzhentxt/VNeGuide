import assert from "node:assert/strict";
import test from "node:test";

import {
  getAssistantMessageOrdinals,
  getNextTtsSegmentIndex,
  isMpegAudioContentType,
  parseTtsContentLength,
  parseTtsSegmentMetadata,
} from "./tts.ts";

function responseHeaders(values: Record<string, string>) {
  return new Headers(values);
}

test("accepts an MPEG response and matching bounded segment metadata", () => {
  assert.equal(isMpegAudioContentType("audio/mpeg; charset=binary"), true);
  assert.deepEqual(
    parseTtsSegmentMetadata(
      responseHeaders({
        "X-VNeGuide-TTS-Segment-Count": "3",
        "X-VNeGuide-TTS-Segment-Index": "1",
      }),
      1,
    ),
    { segmentCount: 3, segmentIndex: 1 },
  );
});

test("numbers only authoritative assistant messages", () => {
  assert.deepEqual(
    getAssistantMessageOrdinals([
      { role: "system" },
      { role: "assistant" },
      { role: "user" },
      { role: "assistant" },
    ]),
    [null, 0, null, 1],
  );
});

test("rejects a response for a stale or impossible segment", () => {
  const headers = responseHeaders({
    "X-VNeGuide-TTS-Segment-Count": "2",
    "X-VNeGuide-TTS-Segment-Index": "1",
  });
  assert.equal(parseTtsSegmentMetadata(headers, 0), null);
  assert.equal(
    parseTtsSegmentMetadata(
      responseHeaders({
        "X-VNeGuide-TTS-Segment-Count": "1",
        "X-VNeGuide-TTS-Segment-Index": "1",
      }),
      1,
    ),
    null,
  );
});

test("finds the next segment and stops at the segment count", () => {
  assert.equal(getNextTtsSegmentIndex({ segmentCount: 3, segmentIndex: 1 }), 2);
  assert.equal(getNextTtsSegmentIndex({ segmentCount: 3, segmentIndex: 2 }), null);
});

test("validates audio type and declared response size", () => {
  assert.equal(isMpegAudioContentType("audio/wav"), false);
  assert.equal(isMpegAudioContentType(null), false);
  assert.equal(parseTtsContentLength("1024"), 1024);
  assert.equal(parseTtsContentLength("0"), null);
  assert.equal(parseTtsContentLength("9000000"), null);
  assert.equal(parseTtsContentLength(null), null);
});
