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
};

export type WorkspaceAction =
  | { type: "hydrate"; state: ProcedureWorkspaceState }
  | { type: "activate"; procedureCode: string | null }
  | { type: "manual_change"; fieldId: string; value: JsonValue }
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
  | { type: "reset"; procedureCode: string | null };

function defaultField(value: JsonValue): ProcedureFieldState {
  return {
    value,
    confirmed: false,
    dirty: false,
    sync_status: "idle",
    error: null,
  };
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
      };
    }
  }

  return {
    ...state,
    revision: Math.max(state.revision, turn.draft.revision),
    fields,
    validation_issues: turn.validation?.issues ?? [],
    recovery_notice: null,
  };
}

export function procedureWorkspaceReducer(
  state: ProcedureWorkspaceState,
  action: WorkspaceAction,
): ProcedureWorkspaceState {
  switch (action.type) {
    case "hydrate":
      return { ...action.state, hydrated: true };
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
            sync_status: "dirty",
            error: null,
          },
        },
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
      let next = metadataFromTurn(state, action.turn);
      if (action.action === "reject") return next;

      const current = next.fields[action.suggestion.field_id] ?? defaultField(null);
      if (current.dirty && action.action === "accept") {
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
            sync_status: "saved",
            error: null,
          },
        },
      };
      return next;
    }
    case "stale":
      return { ...state, recovery_notice: "Phiên đã thay đổi. Dữ liệu trên form được giữ lại và chat đang đồng bộ lại." };
    case "reset":
      return { ...emptyWorkspace, procedure_code: action.procedureCode, hydrated: true };
  }
}
