import assert from "node:assert/strict";
import test from "node:test";

import { getChatValidationPresentation } from "./chat-presentation.ts";
import type { ChatTurn } from "../types/chat.ts";

function turn(status: string, missingCount: number): ChatTurn {
  return {
    reply: "",
    next_action: "continue",
    procedure: { code: "1.004194", name: "Đăng ký tạm trú" },
    draft: {
      values: {},
      revision: 0,
      confirmed_fields: [],
      dirty_fields: [],
      pack_version: "2.0.0",
    },
    messages: [],
    suggestions: [],
    missing_fields: Array.from({ length: missingCount }, (_, index) => ({
      field_id: `field_${index}`,
      label: `Trường ${index}`,
      choices: [],
    })),
    validation: { status, readiness_score: 100, issues: [] },
    sources: [],
  };
}

test("ready rules do not present an incomplete draft as ready to submit", () => {
  assert.deepEqual(getChatValidationPresentation(turn("ready_to_submit", 11)), {
    label: "Hồ sơ chưa đủ thông tin",
    showReadinessScore: false,
    tone: "incomplete",
  });
});

test("a complete rule-valid draft is presented as ready for final review", () => {
  assert.deepEqual(getChatValidationPresentation(turn("ready_to_submit", 0)), {
    label: "Sẵn sàng kiểm tra lần cuối",
    showReadinessScore: true,
    tone: "success",
  });
});
