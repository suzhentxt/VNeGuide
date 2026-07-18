import assert from "node:assert/strict";
import test from "node:test";

import {
  emptyWorkspace,
  guardSuggestionForLocalField,
  procedureWorkspaceReducer,
} from "./procedure-workspace-reducer.ts";
import {
  createWorkspaceRouteSnapshot,
  getPendingFieldCommitIds,
} from "./procedure-workspace-sync.ts";
import {
  getChatContextKey,
  getChatSessionContext,
  shouldRebindChatWorkspace,
  shouldRebindChatSession,
} from "../data/chat-scope.ts";
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
      pack_version: "2.0.0",
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
    source: "manual",
    sync_status: "dirty",
    error: null,
  });
});

test("wallet prefill stays blocked until the user confirms it", () => {
  const prefilled = procedureWorkspaceReducer(workspace(), {
    type: "wallet_prefill",
    values: { applicant_full_name: "NGUYEN VAN A" },
  });

  assert.equal(prefilled.fields.applicant_full_name.value, "NGUYEN VAN A");
  assert.equal(prefilled.fields.applicant_full_name.source, "wallet");
  assert.equal(prefilled.fields.applicant_full_name.confirmed, false);

  const confirmed = procedureWorkspaceReducer(prefilled, {
    type: "confirm_fields",
    fieldIds: ["applicant_full_name"],
  });
  assert.equal(confirmed.fields.applicant_full_name.confirmed, true);
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

test("stale rebase preserves the unsynced value and status", () => {
  const edited = procedureWorkspaceReducer(workspace({ revision: 1 }), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "Giá trị local cần retry",
  });
  const saving = procedureWorkspaceReducer(edited, {
    type: "sync_start",
    fieldId: "temporary_address",
  });
  const stale = procedureWorkspaceReducer(saving, { type: "stale" });
  const rebased = procedureWorkspaceReducer(stale, {
    type: "apply_turn",
    turn: turn(2, { temporary_address: "Giá trị server cũ" }),
  });

  assert.equal(rebased.revision, 2);
  assert.equal(rebased.fields.temporary_address.value, "Giá trị local cần retry");
  assert.equal(rebased.fields.temporary_address.sync_status, "dirty");
  assert.match(rebased.recovery_notice ?? "", /vẫn được giữ/);
});

test("session recreation preserves form values and rebases the revision", () => {
  const current = workspace({
    revision: 3,
    fields: {
      temporary_address: {
        value: "Giá trị người dùng",
        confirmed: true,
        dirty: false,
        sync_status: "saved",
        error: null,
      },
    },
  });
  const next = procedureWorkspaceReducer(current, { type: "session_recreated" });
  assert.equal(next.revision, 0);
  assert.equal(next.fields.temporary_address.value, "Giá trị người dùng");
  assert.equal(next.fields.temporary_address.dirty, true);
  assert.equal(next.fields.temporary_address.sync_status, "dirty");
  assert.match(next.recovery_notice ?? "", /tạo lại/);
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

test("edit applies when its request-start field guard is still current", () => {
  const current = workspace({
    fields: {
      temporary_address: {
        value: "value before request",
        confirmed: false,
        dirty: false,
        sync_status: "idle",
        error: null,
      },
    },
  });
  const guardedSuggestion = guardSuggestionForLocalField(
    suggestion,
    current.fields.temporary_address,
  );
  const responseTurn = turn(1, { temporary_address: "edited suggestion" });
  responseTurn.draft.dirty_fields = ["temporary_address"];

  const next = procedureWorkspaceReducer(current, {
    type: "suggestion_resolved",
    suggestion: guardedSuggestion,
    action: "edit",
    value: "edited suggestion",
    turn: responseTurn,
  });

  assert.equal(next.fields.temporary_address.value, "edited suggestion");
  assert.equal(next.fields.temporary_address.dirty, true);
  assert.equal(next.recovery_notice, null);
});

test("pending accept and edit never overwrite a later manual change", () => {
  for (const action of ["accept", "edit"] as const) {
    const requestStart = workspace({
      fields: {
        temporary_address: {
          value: "value before request",
          confirmed: false,
          dirty: false,
          sync_status: "idle",
          error: null,
        },
      },
    });
    const guardedSuggestion = guardSuggestionForLocalField(
      suggestion,
      requestStart.fields.temporary_address,
    );
    const manuallyChanged = procedureWorkspaceReducer(requestStart, {
      type: "manual_change",
      fieldId: "temporary_address",
      value: "newer manual value",
    });
    const responseTurn = turn(1, {
      temporary_address:
        action === "edit" ? "late edited suggestion" : "late accepted suggestion",
    });
    if (action === "edit") {
      responseTurn.draft.dirty_fields = ["temporary_address"];
    }

    const next = procedureWorkspaceReducer(manuallyChanged, {
      type: "suggestion_resolved",
      suggestion: guardedSuggestion,
      action,
      ...(action === "edit" ? { value: "late edited suggestion" } : {}),
      turn: responseTurn,
    });

    assert.equal(next.fields.temporary_address.value, "newer manual value");
    assert.equal(next.fields.temporary_address.dirty, true);
    assert.equal(next.revision, 1);
    assert.match(next.recovery_notice ?? "", /AI/);
  }
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

test("route snapshot requeues unsynced fields with their latest values", () => {
  const current = workspace({
    fields: {
      dirty_field: {
        value: "latest dirty value",
        confirmed: true,
        dirty: true,
        sync_status: "dirty",
        error: null,
      },
      saving_field: {
        value: "latest saving value",
        confirmed: true,
        dirty: true,
        sync_status: "saving",
        error: null,
      },
      error_field: {
        value: "latest error value",
        confirmed: true,
        dirty: true,
        sync_status: "error",
        error: "temporary failure",
      },
      saved_field: {
        value: "already synced",
        confirmed: true,
        dirty: true,
        sync_status: "saved",
        error: null,
      },
    },
  });

  assert.deepEqual(getPendingFieldCommitIds(current), [
    "dirty_field",
    "saving_field",
    "error_field",
  ]);

  const snapshot = createWorkspaceRouteSnapshot(current, "1.004194");
  assert.ok(snapshot);
  assert.deepEqual(snapshot.pendingFieldIds, [
    "dirty_field",
    "saving_field",
    "error_field",
  ]);
  const persisted = JSON.parse(
    snapshot.serializedState,
  ) as ProcedureWorkspaceState;
  assert.equal(persisted.fields.dirty_field.value, "latest dirty value");
  assert.equal(persisted.fields.saving_field.value, "latest saving value");
  assert.equal(persisted.fields.error_field.value, "latest error value");
});

test("reset snapshot has no pending fields to resurrect", () => {
  const dirty = procedureWorkspaceReducer(workspace(), {
    type: "manual_change",
    fieldId: "temporary_address",
    value: "must be cleared",
  });
  const reset = procedureWorkspaceReducer(dirty, {
    type: "reset",
    procedureCode: "1.004194",
  });

  const snapshot = createWorkspaceRouteSnapshot(reset, "1.004194");
  assert.ok(snapshot);
  assert.deepEqual(snapshot.pendingFieldIds, []);
  const persisted = JSON.parse(
    snapshot.serializedState,
  ) as ProcedureWorkspaceState;
  assert.deepEqual(persisted.fields, {});
});

test("chat scope resolves all supported procedures on nested routes", () => {
  const cases = [
    ["/hon-nhan-va-gia-dinh/dang-ky-tam-tru/to-khai", "1.004194"],
    ["/hon-nhan-va-gia-dinh/cap-ban-sao-giay-khai-sinh/nop-ho-so", "2.000635"],
    ["/hon-nhan-va-gia-dinh/xac-nhan-dieu-kien-nha-o/truc-tuyen", "1.013314"],
  ] as const;

  for (const [pathname, expectedCode] of cases) {
    assert.equal(getChatSessionContext(pathname).procedure_code, expectedCode);
  }
});

test("removed marriage and general pages use an unscoped chat context", () => {
  assert.equal(getChatSessionContext("/").procedure_code, undefined);
  assert.equal(
    getChatSessionContext("/hon-nhan-va-gia-dinh/dang-ky-ket-hon").procedure_code,
    undefined,
  );
});

test("chat rebinds from general context or another procedure", () => {
  const general = getChatSessionContext("/");
  const temporaryResidence = getChatSessionContext(
    "/hon-nhan-va-gia-dinh/dang-ky-tam-tru",
  );
  const birthCopy = getChatSessionContext(
    "/hon-nhan-va-gia-dinh/cap-ban-sao-giay-khai-sinh",
  );

  assert.equal(shouldRebindChatSession(general, temporaryResidence), true);
  assert.equal(shouldRebindChatSession(temporaryResidence, birthCopy), true);
});

test("chat keeps its session across subpages of the same procedure", () => {
  const detail = getChatSessionContext("/hon-nhan-va-gia-dinh/dang-ky-tam-tru");
  const form = getChatSessionContext(
    "/hon-nhan-va-gia-dinh/dang-ky-tam-tru/to-khai",
  );

  assert.equal(shouldRebindChatSession(detail, form), false);
});

test("chat rebinds when leaving a procedure for general pages", () => {
  const detail = getChatSessionContext("/hon-nhan-va-gia-dinh/dang-ky-tam-tru");
  const general = getChatSessionContext("/");

  assert.equal(shouldRebindChatSession(detail, general), true);
  assert.equal(shouldRebindChatSession(null, detail), true);
  assert.equal(shouldRebindChatSession(undefined, detail), false);
  assert.equal(getChatContextKey(null), getChatContextKey(general));
});

test("chat rebinds when a hydrated procedure form differs from the backend draft", () => {
  const temporaryResidence = getChatSessionContext(
    "/hon-nhan-va-gia-dinh/dang-ky-tam-tru",
  );

  assert.equal(
    shouldRebindChatWorkspace(
      turn(1).draft,
      temporaryResidence,
      workspace({ revision: 5 }),
    ),
    true,
  );
  assert.equal(
    shouldRebindChatWorkspace(
      turn(5).draft,
      temporaryResidence,
      workspace({ revision: 5 }),
    ),
    false,
  );
  assert.equal(
    shouldRebindChatWorkspace(
      turn(1).draft,
      temporaryResidence,
      workspace({ revision: 5, hydrated: false }),
    ),
    false,
  );
  assert.equal(
    shouldRebindChatWorkspace(
      turn(1, { temporary_address: "Backend" }).draft,
      temporaryResidence,
      workspace({
        revision: 1,
        fields: {
          temporary_address: {
            value: "Form",
            confirmed: true,
            dirty: true,
            sync_status: "saved",
            error: null,
          },
        },
      }),
    ),
    true,
  );
});
