import assert from "node:assert/strict";
import test from "node:test";

import {
  getChatStatusPresentation,
  getReviewedSourceHref,
} from "./chat-status-presentation.ts";
import type { ChatSuggestion, ChatTurn } from "../types/chat.ts";

function turn(overrides: Partial<ChatTurn> = {}): ChatTurn {
  return {
    reply: "Phản hồi thử nghiệm",
    next_action: "ask_clarification",
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
    missing_fields: [],
    validation: null,
    sources: [],
    ...overrides,
  };
}

function validation(
  status: string,
  readinessScore: number | null = null,
): NonNullable<ChatTurn["validation"]> {
  return {
    status,
    readiness_score: readinessScore,
    issues: [],
  };
}

const pendingSuggestion: ChatSuggestion = {
  id: "suggestion-1",
  field_id: "registration_mode",
  label: "Hình thức đăng ký",
  current_value: null,
  suggested_value: "individual_household",
  evidence: "cá nhân",
  status: "pending",
  revision: 0,
};

test("terminal validation states take precedence over workflow actions", () => {
  const cases = [
    ["out_of_scope", "Ngoài phạm vi hỗ trợ"],
    ["needs_correction", "Cần sửa thông tin"],
    ["needs_official_review", "Cần cơ quan có thẩm quyền kiểm tra"],
  ] as const;

  for (const [status, expectedLabel] of cases) {
    const result = getChatStatusPresentation(
      turn({
        next_action: "confirm_suggestion",
        suggestions: [pendingSuggestion],
        validation: validation(status, 100),
      }),
    );
    assert.equal(result.label, expectedLabel);
    assert.equal(result.readinessScore, null);
  }
});

test("terminal workflow actions are mapped without exposing backend enums", () => {
  const cases = [
    ["out_of_scope", "Ngoài phạm vi hỗ trợ"],
    ["request_correction", "Cần sửa thông tin"],
    ["request_official_review", "Cần cơ quan có thẩm quyền kiểm tra"],
  ] as const;

  for (const [nextAction, expectedLabel] of cases) {
    const result = getChatStatusPresentation(turn({ next_action: nextAction }));
    assert.equal(result.label, expectedLabel);
    assert.doesNotMatch(result.label, /out_of_scope|needs_|request_/);
    assert.equal(result.readinessScore, null);
  }
});

test("pending suggestion is shown before missing-field progress", () => {
  const result = getChatStatusPresentation(
    turn({
      next_action: "ask_clarification",
      suggestions: [pendingSuggestion],
      missing_fields: [
        {
          field_id: "full_name",
          label: "Họ tên",
          field_type: "string",
          input_hint: "Nhập đầy đủ họ và tên.",
          choices: [],
        },
      ],
    }),
  );
  assert.equal(result.label, "Đang chờ xác nhận đề xuất");
  assert.equal(result.readinessScore, null);
});

test("missing fields prevent ready status and hide readiness score", () => {
  const result = getChatStatusPresentation(
    turn({
      next_action: "complete",
      missing_fields: [
        {
          field_id: "registration_mode",
          label: "Hình thức đăng ký",
          field_type: "enum",
          input_hint: "Chọn một phương án.",
          choices: ["individual_household", "by_list"],
        },
      ],
      validation: validation("ready_to_submit", 100),
    }),
  );
  assert.equal(result.label, "Đang bổ sung thông tin");
  assert.equal(result.readinessScore, null);
});

test("manual and clarification actions are presented as supplementing information", () => {
  for (const nextAction of ["manual_input", "ask_clarification"]) {
    const result = getChatStatusPresentation(turn({ next_action: nextAction }));
    assert.equal(result.label, "Đang bổ sung thông tin");
    assert.equal(result.readinessScore, null);
  }
});

test("procedure confirmation has a dedicated user-facing status", () => {
  const result = getChatStatusPresentation(turn({ next_action: "confirm_procedure" }));
  assert.equal(result.label, "Đang xác nhận thủ tục");
  assert.equal(result.readinessScore, null);
});

test("readiness score appears only for a truly completed draft", () => {
  const result = getChatStatusPresentation(
    turn({
      next_action: "complete",
      missing_fields: [],
      validation: validation("ready_to_submit", 100),
    }),
  );
  assert.deepEqual(result, {
    label: "Sẵn sàng kiểm tra trước khi nộp",
    readinessScore: 100,
    tone: "success",
  });
});

test("retry and unknown actions use safe Vietnamese labels", () => {
  assert.equal(
    getChatStatusPresentation(turn({ next_action: "retry" })).label,
    "Kết nối AI đang gián đoạn",
  );
  assert.equal(
    getChatStatusPresentation(turn({ next_action: "future_action" })).label,
    "Đang xử lý",
  );
});

test("source without URL is rendered as text instead of an empty link", () => {
  assert.equal(getReviewedSourceHref(""), null);
  assert.equal(getReviewedSourceHref("   "), null);
  assert.equal(
    getReviewedSourceHref("https://example.test/official"),
    "https://example.test/official",
  );
});
