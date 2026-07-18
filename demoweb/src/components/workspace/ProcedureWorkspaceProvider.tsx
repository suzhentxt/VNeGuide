"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from "react";

import { getChatSessionContext } from "@/data/chat-scope";
import {
  emptyWorkspace,
  procedureWorkspaceReducer,
  type WorkspaceAction,
} from "@/lib/procedure-workspace-reducer";
import type { ChatSession, ChatSuggestion, ChatTurn, JsonValue, ProcedureWorkspaceState } from "@/types/chat";

const STORAGE_PREFIX = "vneguide:workspace:v1:";

interface WorkspaceContextValue {
  state: ProcedureWorkspaceState;
  setField: (fieldId: string, value: JsonValue) => void;
  commitField: (fieldId: string, value?: JsonValue) => Promise<void>;
  applyTurn: (turn: ChatTurn, expectedRevision?: number) => boolean;
  applySuggestion: (
    suggestion: ChatSuggestion,
    action: "accept" | "reject" | "edit",
    turn: ChatTurn,
    value?: JsonValue,
  ) => void;
  markStale: () => void;
  rebaseSession: () => void;
  resetWorkspace: () => void;
  isDirty: (fieldId: string) => boolean;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function storageKey(procedureCode: string) {
  return `${STORAGE_PREFIX}${procedureCode}`;
}

function readPersisted(procedureCode: string): ProcedureWorkspaceState | null {
  try {
    const raw = window.sessionStorage.getItem(storageKey(procedureCode));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ProcedureWorkspaceState;
    if (
      parsed.procedure_code !== procedureCode ||
      typeof parsed.revision !== "number" ||
      !parsed.fields ||
      typeof parsed.fields !== "object" ||
      !Array.isArray(parsed.validation_issues)
    ) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function ProcedureWorkspaceProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const context = useMemo(() => getChatSessionContext(pathname), [pathname]);
  const procedureCode = context.procedure_code ?? null;
  const [state, dispatch] = useReducer(procedureWorkspaceReducer, {
    ...emptyWorkspace,
    procedure_code: procedureCode,
  });
  const stateRef = useRef(state);
  const requestTokens = useRef(new Map<string, string>());
  const dispatchTracked = useCallback((action: WorkspaceAction) => {
    stateRef.current = procedureWorkspaceReducer(stateRef.current, action);
    dispatch(action);
  }, []);

  useEffect(() => {
    stateRef.current = state;
    if (state.hydrated && state.procedure_code) {
      window.sessionStorage.setItem(storageKey(state.procedure_code), JSON.stringify(state));
    }
  }, [state]);

  useEffect(() => {
    if (!procedureCode) {
      dispatchTracked({ type: "activate", procedureCode: null });
      return;
    }
    const persisted = readPersisted(procedureCode);
    dispatchTracked({
      type: "hydrate",
      state: persisted ?? { ...emptyWorkspace, procedure_code: procedureCode },
    });
  }, [dispatchTracked, procedureCode]);

  const setField = useCallback((fieldId: string, value: JsonValue) => {
    dispatchTracked({ type: "manual_change", fieldId, value });
  }, [dispatchTracked]);

  const applyTurn = useCallback((turn: ChatTurn, expectedRevision?: number) => {
    const before = stateRef.current;
    if (
      turn.draft.revision < before.revision ||
      (expectedRevision !== undefined && before.revision !== expectedRevision)
    ) {
      dispatchTracked({ type: "stale" });
      return false;
    }
    dispatchTracked({ type: "apply_turn", turn, expectedRevision });
    return true;
  }, [dispatchTracked]);

  const commitField = useCallback(async (fieldId: string, value?: JsonValue) => {
    const snapshot = stateRef.current;
    const field = snapshot.fields[fieldId];
    if (!field || !snapshot.procedure_code) return;

    const token = crypto.randomUUID();
    requestTokens.current.set(fieldId, token);
    dispatchTracked({ type: "sync_start", fieldId });
    try {
      const response = await fetch("/api/chat/field", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          field_id: fieldId,
          value: value === undefined ? field.value : value,
          expected_revision: snapshot.revision,
          context,
        }),
      });
      const body = (await response.json()) as ChatTurn | { error?: { message?: string } };
      if (requestTokens.current.get(fieldId) !== token) return;
      if (response.status === 409) {
        dispatchTracked({ type: "stale" });
        const recovered = await fetch("/api/chat/session", { cache: "no-store" });
        if (recovered.ok) {
          const recoveredSession = (await recovered.json()) as ChatSession;
          if (recoveredSession.turn) applyTurn(recoveredSession.turn);
        }
        return;
      }
      if (!response.ok || !("draft" in body)) {
        const message = "error" in body ? body.error?.message : undefined;
        dispatchTracked({
          type: "sync_error",
          fieldId,
          message: message || "AI chưa đồng bộ được; giá trị vẫn được giữ trên biểu mẫu.",
        });
        return;
      }
      applyTurn(body, snapshot.revision);
    } catch {
      if (requestTokens.current.get(fieldId) === token) {
        dispatchTracked({
          type: "sync_error",
          fieldId,
          message: "AI đang quá hạn hoặc mất kết nối; giá trị vẫn được giữ trên biểu mẫu.",
        });
      }
    }
  }, [applyTurn, context, dispatchTracked]);

  const applySuggestion = useCallback(
    (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      turn: ChatTurn,
      value?: JsonValue,
    ) => {
      dispatchTracked({ type: "suggestion_resolved", suggestion, action, turn, value });
    },
    [dispatchTracked],
  );

  const resetWorkspace = useCallback(() => {
    if (stateRef.current.procedure_code) {
      window.sessionStorage.removeItem(storageKey(stateRef.current.procedure_code));
    }
    requestTokens.current.clear();
    dispatchTracked({ type: "reset", procedureCode: stateRef.current.procedure_code });
  }, [dispatchTracked]);

  const isDirty = useCallback(
    (fieldId: string) => Boolean(state.fields[fieldId]?.dirty),
    [state.fields],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      state,
      setField,
      commitField,
      applyTurn,
      applySuggestion,
      markStale: () => dispatchTracked({ type: "stale" }),
      rebaseSession: () => dispatchTracked({ type: "session_recreated" }),
      resetWorkspace,
      isDirty,
    }),
    [applySuggestion, applyTurn, commitField, dispatchTracked, isDirty, resetWorkspace, setField, state],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useProcedureWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useProcedureWorkspace must be used inside ProcedureWorkspaceProvider");
  return value;
}
