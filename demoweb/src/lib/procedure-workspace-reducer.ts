import type {
  ChatSuggestion,
  ChatTurn,
  JsonValue,
  ProcedureFieldState,
  ProcedureWorkspaceState,
} from "@/types/chat";

export const emptyWorkspace: ProcedureWorkspaceState = {
  procedure_code: null,
  revision: 0,
  fields: {},
  validation_issues: [],
  hydrated: false,
  recovery_notice: null,
  pending_suggestion_fields: [],
};

const localFieldGuardKey = "__vneguide_local_field_guard" as const;

interface LocalFieldGuard {
  value: JsonValue;
  dirty: boolean;
}

type LocallyGuardedSuggestion = ChatSuggestion & {
  [localFieldGuardKey]?: LocalFieldGuard;
};

export function guardSuggestionForLocalField(
  suggestion: ChatSuggestion,
  field: ProcedureFieldState | undefined,
): ChatSuggestion {
  const guardedSuggestion: LocallyGuardedSuggestion = {
    ...suggestion,
    [localFieldGuardKey]: {
      value: field?.value ?? null,
      dirty: field?.dirty ?? false,
    },
  };
  return guardedSuggestion;
}

export type WorkspaceAction =
  | { type: "hydrate"; state: ProcedureWorkspaceState }
  | { type: "activate"; procedureCode: string | null }
  | { type: "manual_change"; fieldId: string; value: JsonValue }
  | { type: "wallet_prefill"; values: Record<string, JsonValue> }
  | { type: "confirm_fields"; fieldIds: string[] }
  | { type: "sync_start"; fieldId: string }
  | { type: "sync_error"; fieldId: string; message: string }
  | { type: "apply_turn"; turn: ChatTurn; expectedRevision?: number }
  | {
      type: "suggestion_resolved";
      suggestion: ChatSuggestion;
      action: "accept" | "reject" | "edit";
      value?: JsonValue;
      turn: ChatTurn;
    }
  | { type: "stale" }
  | { type: "session_recreated" }
  | { type: "reset"; procedureCode: string | null };

function defaultField(value: JsonValue): ProcedureFieldState {
  return {
    value,
    confirmed: false,
    dirty: false,
    source: "assistant",
    sync_status: "idle",
    error: null,
  };
}

function jsonValuesEqual(left: JsonValue, right: JsonValue) {
  return Object.is(left, right) || JSON.stringify(left) === JSON.stringify(right);
}

function localFieldChangedSinceRequest(
  suggestion: ChatSuggestion,
  current: ProcedureFieldState,
) {
  const guard = (suggestion as LocallyGuardedSuggestion)[localFieldGuardKey];
  if (!guard) return current.dirty;
  return (
    current.dirty ||
    current.dirty !== guard.dirty ||
    !jsonValuesEqual(current.value, guard.value)
  );
}

function metadataFromTurn(
  state: ProcedureWorkspaceState,
  turn: ChatTurn,
): ProcedureWorkspaceState {
  const fields = { ...state.fields };
  const confirmed = new Set(turn.draft.confirmed_fields);
  const dirty = new Set(turn.draft.dirty_fields);

  for (const fieldId of new Set([...confirmed, ...dirty])) {
    const current = fields[fieldId] ?? defaultField(null);
    fields[fieldId] = {
      ...current,
      confirmed: current.confirmed || confirmed.has(fieldId),
      dirty: current.dirty || dirty.has(fieldId),
      source: dirty.has(fieldId) ? "manual" : current.source ?? "assistant",
      sync_status: current.sync_status === "saving" ? "saved" : current.sync_status,
      error: null,
    };
  }

  for (const [fieldId, value] of Object.entries(turn.draft.values ?? {})) {
    const current = fields[fieldId] ?? defaultField(value);
    if (!current.dirty) {
      fields[fieldId] = {
        ...current,
        value,
        confirmed: confirmed.has(fieldId),
        dirty: dirty.has(fieldId),
        source: dirty.has(fieldId) ? "manual" : current.source ?? "assistant",
      };
    }
  }

  return {
    ...state,
    revision: Math.max(state.revision, turn.draft.revision),
    fields,
    validation_issues: turn.validation?.issues ?? [],
    pending_suggestion_fields: turn.suggestions
      .filter((s) => s.status === "pending")
      .map((s) => s.field_id),
    recovery_notice: Object.values(fields).some(
      (field) => field.sync_status === "dirty" || field.sync_status === "error",
    )
      ? state.recovery_notice
      : null,
  };
}

export function procedureWorkspaceReducer(
  state: ProcedureWorkspaceState,
  action: WorkspaceAction,
): ProcedureWorkspaceState {
  switch (action.type) {
    case "hydrate":
      return {
        ...action.state,
        pending_suggestion_fields: action.state.pending_suggestion_fields ?? [],
        hydrated: true,
      };
    case "activate":
      if (state.procedure_code === action.procedureCode && state.hydrated) return state;
      return { ...emptyWorkspace, procedure_code: action.procedureCode, hydrated: true };
    case "manual_change": {
      const current = state.fields[action.fieldId] ?? defaultField(action.value);
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.fieldId]: {
            ...current,
            value: action.value,
            confirmed: true,
            dirty: true,
            source: "manual",
            sync_status: "dirty",
            error: null,
          },
        },
      };
    }
    case "wallet_prefill": {
      const fields = { ...state.fields };
      for (const [fieldId, value] of Object.entries(action.values)) {
        const current = fields[fieldId] ?? defaultField(value);
        fields[fieldId] = {
          ...current,
          value,
          confirmed: false,
          dirty: true,
          source: "wallet",
          sync_status: "dirty",
          error: null,
        };
      }
      return { ...state, fields };
    }
    case "confirm_fields": {
      const selected = new Set(action.fieldIds);
      return {
        ...state,
        fields: Object.fromEntries(
          Object.entries(state.fields).map(([fieldId, field]) => [
            fieldId,
            selected.has(fieldId) ? { ...field, confirmed: true } : field,
          ]),
        ),
      };
    }
    case "sync_start": {
      const current = state.fields[action.fieldId];
      if (!current) return state;
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.fieldId]: { ...current, sync_status: "saving", error: null },
        },
      };
    }
    case "sync_error": {
      const current = state.fields[action.fieldId];
      if (!current) return state;
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.fieldId]: {
            ...current,
            sync_status: "error",
            error: action.message,
          },
        },
      };
    }
    case "apply_turn":
      if (
        action.turn.draft.revision < state.revision ||
        (action.expectedRevision !== undefined && state.revision !== action.expectedRevision)
      ) {
        return { ...state, recovery_notice: "Đã bỏ một phản hồi cũ để giữ dữ liệu mới nhất trên biểu mẫu." };
      }
      return metadataFromTurn(state, action.turn);
    case "suggestion_resolved": {
      if (action.turn.draft.revision < state.revision) {
        return { ...state, recovery_notice: "Đề xuất đã hết hạn và không được áp dụng vào biểu mẫu." };
      }
      const currentBeforeResponse =
        state.fields[action.suggestion.field_id] ?? defaultField(null);
      const preserveLocalField = localFieldChangedSinceRequest(
        action.suggestion,
        currentBeforeResponse,
      );
      let next = metadataFromTurn(state, action.turn);
      if (action.action === "reject") return next;

      if (preserveLocalField) {
        return {
          ...next,
          recovery_notice: "Giữ nguyên giá trị bạn đã sửa trực tiếp; AI không được ghi đè field này.",
        };
      }
      const value = action.action === "edit" ? action.value ?? null : action.suggestion.suggested_value;
      next = {
        ...next,
        fields: {
          ...next.fields,
          [action.suggestion.field_id]: {
            value,
            confirmed: true,
            dirty: action.action === "edit",
            source: "assistant",
            sync_status: "saved",
            error: null,
          },
        },
      };
      return next;
    }
    case "stale":
      return {
        ...state,
        fields: Object.fromEntries(
          Object.entries(state.fields).map(([fieldId, field]) => [
            fieldId,
            field.sync_status === "saving"
              ? { ...field, sync_status: "dirty", error: null }
              : field,
          ]),
        ),
        recovery_notice:
          "Phiên đã thay đổi. Giá trị bạn vừa sửa vẫn được giữ và cần đồng bộ lại.",
      };
    case "session_recreated":
      return {
        ...state,
        revision: 0,
        fields: Object.fromEntries(
          Object.entries(state.fields).map(([fieldId, field]) => [
            fieldId,
            { ...field, dirty: true, sync_status: "dirty", error: null },
          ]),
        ),
        validation_issues: [],
        recovery_notice:
          "Phiên trợ lý đã được tạo lại. Dữ liệu trên form được giữ và cần đồng bộ lại.",
      };
    case "reset":
      return { ...emptyWorkspace, procedure_code: action.procedureCode, hydrated: true };
  }
}
