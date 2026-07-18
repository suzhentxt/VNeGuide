import assert from "node:assert/strict";
import test from "node:test";

import {
  emptyWorkspace,
  procedureWorkspaceReducer,
} from "./procedure-workspace-reducer.ts";
import type { ChatSuggestion, ChatTurn, ProcedureWorkspaceState } from "../types/chat.ts";

function workspace(overrides: Partial<ProcedureWorkspaceState> = {}): ProcedureWorkspaceState {
  return {
    ...emptyWorkspace,
    procedure_code: "1.004194",
    hydrated: true,
    ...overrides,
  };
}

function turn(revision: number, values: Record<string, string> = {}): ChatTurn {
  return {
    reply: "Đã cập nhật",
    next_action: "continue",
    procedure: { code: "1.004194", name: "Đăng ký tạm trú" },
    draft: {
      revision,
      confirmed_fields: Object.keys(values),
      dirty_fields: [],
      values,
    },
    messages: [],
    suggestions: [],
    missing_fields: [],
    validation: null,
    sources: [],
  };
}

const suggestion: ChatSuggestion = {
  id: "suggestion-1",
  field_id: "temporary_address",
  label: "Địa chỉ tạm trú",
  current_value: null,
  suggested_value: "Địa chỉ do AI đề xuất",
  evidence: "Tôi ở địa chỉ giả lập",
  status: "pending",
  revision: 0,
};

test("manual edit becomes confirmed and dirty immediately", () => {
  const next = procedureWorkspaceReducer(workspace(), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "Địa chỉ do người dùng nhập",
  });
  assert.deepEqual(next.fields.temporary_address, {
    value: "Địa chỉ do người dùng nhập",
    confirmed: true,
    dirty: true,
    sync_status: "dirty",
    error: null,
  });
});

test("stale response is ignored", () => {
  const current = workspace({ revision: 3 });
  const next = procedureWorkspaceReducer(current, {
    type: "apply_turn",
    turn: turn(2, { temporary_address: "Dữ liệu cũ" }),
  });
  assert.equal(next.revision, 3);
  assert.equal(next.fields.temporary_address, undefined);
  assert.match(next.recovery_notice ?? "", /phản hồi cũ/);
});

test("AI draft values never overwrite a manually dirty field", () => {
  const edited = procedureWorkspaceReducer(workspace(), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "Giá trị người dùng",
  });
  const next = procedureWorkspaceReducer(edited, {
    type: "apply_turn",
    turn: turn(1, { temporary_address: "Giá trị AI" }),
    expectedRevision: 0,
  });
  assert.equal(next.fields.temporary_address.value, "Giá trị người dùng");
  assert.equal(next.fields.temporary_address.dirty, true);
});

test("accept writes the suggested value to a clean form field", () => {
  const next = procedureWorkspaceReducer(workspace(), {
    type: "suggestion_resolved",
    suggestion,
    action: "accept",
    turn: turn(1),
  });
  assert.equal(next.fields.temporary_address.value, suggestion.suggested_value);
  assert.equal(next.fields.temporary_address.confirmed, true);
  assert.equal(next.fields.temporary_address.dirty, false);
});

test("edit writes the chosen value and marks the field dirty", () => {
  const next = procedureWorkspaceReducer(workspace(), {
    type: "suggestion_resolved",
    suggestion,
    action: "edit",
    value: "Giá trị đã sửa",
    turn: turn(1),
  });
  assert.equal(next.fields.temporary_address.value, "Giá trị đã sửa");
  assert.equal(next.fields.temporary_address.confirmed, true);
  assert.equal(next.fields.temporary_address.dirty, true);
});

test("reject leaves the form value untouched", () => {
  const current = workspace({
    fields: {
      temporary_address: {
        value: "Giá trị hiện tại",
        confirmed: true,
        dirty: false,
        sync_status: "saved",
        error: null,
      },
    },
  });
  const next = procedureWorkspaceReducer(current, {
    type: "suggestion_resolved",
    suggestion,
    action: "reject",
    turn: turn(1),
  });
  assert.equal(next.fields.temporary_address.value, "Giá trị hiện tại");
});

test("accept cannot overwrite an already dirty field", () => {
  const current = procedureWorkspaceReducer(workspace(), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "Giá trị người dùng",
  });
  const next = procedureWorkspaceReducer(current, {
    type: "suggestion_resolved",
    suggestion,
    action: "accept",
    turn: turn(1),
  });
  assert.equal(next.fields.temporary_address.value, "Giá trị người dùng");
  assert.match(next.recovery_notice ?? "", /không được ghi đè/);
});

test("reset clears fields while keeping the active procedure", () => {
  const current = procedureWorkspaceReducer(workspace(), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "Giá trị người dùng",
  });
  const next = procedureWorkspaceReducer(current, {
    type: "reset",
    procedureCode: "1.004194",
  });
  assert.equal(next.procedure_code, "1.004194");
  assert.deepEqual(next.fields, {});
  assert.equal(next.revision, 0);
});
