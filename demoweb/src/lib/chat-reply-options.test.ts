import assert from "node:assert/strict";
import test from "node:test";

import { getChatReplyOptions } from "./chat-reply-options.ts";
import type { ChatTurn } from "../types/chat.ts";

function turn(overrides: Partial<ChatTurn>): ChatTurn {
  return {
    reply: "",
    next_action: "ask_clarification",
    procedure: null,
    draft: {
      values: {},
      revision: 0,
      confirmed_fields: [],
      dirty_fields: [],
      pack_version: null,
    },
    messages: [],
    suggestions: [],
    missing_fields: [],
    validation: null,
    sources: [],
    ...overrides,
  };
}

test("offers two plain-language choices for the remembered birth scope question", () => {
  const options = getChatReplyOptions(
    turn({
      reply:
        "Bạn muốn xin bản sao Giấy khai sinh hay đăng ký khai sinh mới?",
    }),
  );

  assert.deepEqual(options, [
    "Tôi muốn xin bản sao Giấy khai sinh",
    "Tôi muốn đăng ký khai sinh mới",
  ]);
});

test("leaves requester enum choices to the catalog-driven field card", () => {
  const options = getChatReplyOptions(
    turn({
      procedure: { code: "2.000635", name: "Cấp bản sao Giấy khai sinh" },
      missing_fields: [{
        field_id: "requester_type",
        label: "Loại người yêu cầu",
        field_type: "enum",
        input_hint: "Chọn một phương án.",
        choices: ["self", "authorized_person", "organization"],
      }],
    }),
  );

  assert.deepEqual(options, []);
});
