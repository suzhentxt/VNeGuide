import assert from "node:assert/strict";
import test from "node:test";

import {
  chooseRecordingMimeType,
  mergeTranscriptIntoDraft,
  parsePositiveLimit,
  resolveAudioMimeType,
} from "./stt.ts";

test("chooses the first safe recording MIME type supported by the browser", () => {
  assert.equal(
    chooseRecordingMimeType((mimeType) => mimeType === "audio/ogg;codecs=opus"),
    "audio/ogg;codecs=opus",
  );
  assert.equal(chooseRecordingMimeType(() => false), null);
  assert.equal(
    chooseRecordingMimeType((mimeType) => {
      if (mimeType.startsWith("audio/webm")) throw new TypeError("unsupported");
      return mimeType === "audio/mp4";
    }),
    "audio/mp4",
  );
});

test("normalizes safe audio types and can infer them from file extensions", () => {
  assert.equal(resolveAudioMimeType("audio/webm; codecs=opus"), "audio/webm");
  assert.equal(resolveAudioMimeType("audio/mp3", "voice.mp3"), "audio/mpeg");
  assert.equal(resolveAudioMimeType("", "ghi-am.M4A"), "audio/mp4");
  assert.equal(resolveAudioMimeType("application/octet-stream", "voice.wav"), "audio/wav");
  assert.equal(resolveAudioMimeType("text/plain", "notes.txt"), null);
});

test("merges a transcript into the editable draft without submitting it", () => {
  assert.equal(mergeTranscriptIntoDraft("Xin", " chào bạn "), "Xin chào bạn");
  assert.equal(mergeTranscriptIntoDraft("Xin\n", "chào"), "Xin\nchào");
  assert.equal(mergeTranscriptIntoDraft("Nội dung", "   "), "Nội dung");
  assert.equal(mergeTranscriptIntoDraft("1234", "567", 6), "1234 5");
  assert.equal(mergeTranscriptIntoDraft("123456", "789", 6), "123456");
});

test("accepts only finite positive limits and clamps unusually large values", () => {
  assert.equal(parsePositiveLimit(60, 30, 120), 60);
  assert.equal(parsePositiveLimit(200, 30, 120), 120);
  assert.equal(parsePositiveLimit(0, 30, 120), 30);
  assert.equal(parsePositiveLimit("60", 30, 120), 30);
});
