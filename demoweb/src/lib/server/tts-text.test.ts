import assert from "node:assert/strict";
import test from "node:test";

import {
  assistantSpeechSegments,
  normalizeAssistantText,
  segmentAssistantText,
  selectAssistantMessage,
  TtsTextError,
} from "./tts-text.ts";

test("selects an assistant message by its zero-based assistant ordinal", () => {
  const session = {
    turn: {
      messages: [
        { role: "user", content: "Không được đọc nội dung người dùng" },
        { role: "assistant", content: "Câu trả lời thứ nhất" },
        { role: "system", content: "Không được đọc system" },
        { role: "assistant", content: "Câu trả lời thứ hai" },
      ],
    },
  };

  assert.equal(selectAssistantMessage(session, 0), "Câu trả lời thứ nhất");
  assert.equal(selectAssistantMessage(session, 1), "Câu trả lời thứ hai");
  assert.throws(
    () => selectAssistantMessage(session, 2),
    (error: unknown) => error instanceof TtsTextError && error.kind === "not_found",
  );
});

test("normalizes Vietnamese Markdown for speech without accepting arbitrary markup", () => {
  const normalized = normalizeAssistantText(
    "## Hồ sơ\n- **Bản chính** và [Tờ khai](https://example.test/form).\n`1.004194`",
    4_000,
  );
  assert.equal(normalized, "Hồ sơ Bản chính và Tờ khai. 1.004194");
});

test("segments deterministically at sentence and word boundaries", () => {
  const text =
    "Đây là câu thứ nhất có đủ nội dung. Đây là câu thứ hai cũng khá dài. " +
    "Đây là câu thứ ba để kiểm tra việc chia đoạn.";
  const first = segmentAssistantText(text, 55);
  const second = segmentAssistantText(text, 55);

  assert.deepEqual(first, second);
  assert.ok(first.length > 1);
  assert.ok(first.every((segment) => segment.length <= 55));
  assert.equal(first.join(" "), text);
});

test("keeps surrogate pairs intact when a hard split is required", () => {
  const segments = segmentAssistantText("abcdefghij🙂klmnop", 11);
  assert.equal(segments.join(""), "abcdefghij🙂klmnop");
  assert.ok(segments.every((segment) => !segment.includes("�")));
});

test("builds bounded segments only from the requested assistant message", () => {
  const segments = assistantSpeechSegments(
    {
      turn: {
        messages: [
          { role: "user", content: "Dữ liệu riêng của người dùng" },
          {
            role: "assistant",
            content:
              "Bạn cần chuẩn bị tờ khai. Sau đó kiểm tra giấy tờ và nộp tại cơ quan có thẩm quyền.",
          },
        ],
      },
    },
    0,
    200,
    45,
  );

  assert.ok(segments.length > 1);
  assert.ok(!segments.join(" ").includes("Dữ liệu riêng"));
  assert.ok(segments.every((segment) => segment.length <= 45));
});

test("rejects empty, oversized, and malformed session content", () => {
  assert.throws(
    () => normalizeAssistantText("   ` `  ", 100),
    (error: unknown) => error instanceof TtsTextError && error.kind === "empty",
  );
  assert.throws(
    () => normalizeAssistantText("a".repeat(101), 100),
    (error: unknown) => error instanceof TtsTextError && error.kind === "too_long",
  );
  assert.throws(
    () => selectAssistantMessage({ turn: { messages: [{ role: 1 }] } }, 0),
    (error: unknown) => error instanceof TtsTextError && error.kind === "invalid_session",
  );
});
