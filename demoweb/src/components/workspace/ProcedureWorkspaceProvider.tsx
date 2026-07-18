"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
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
import {
  createWorkspaceRouteSnapshot,
  getPendingFieldCommitIds,
} from "@/lib/procedure-workspace-sync";
import {
  createChatSession,
  publishChatSession,
  publishChatTurn,
} from "@/lib/chat-session-client";
import type { ChatSession, ChatSuggestion, ChatTurn, JsonValue, ProcedureWorkspaceState } from "@/types/chat";

const STORAGE_PREFIX = "vneguide:workspace:v1:";

interface WorkspaceContextValue {
  state: ProcedureWorkspaceState;
  setField: (fieldId: string, value: JsonValue) => void;
  commitField: (fieldId: string) => Promise<boolean>;
  syncFields: () => Promise<number>;
  runDraftMutation: <T>(
    mutation: (currentRevision: number) => Promise<T>,
  ) => Promise<T | undefined>;
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

function queueFieldCommits(
  queues: Map<string, Set<string>>,
  procedureCode: string,
  fieldIds: Iterable<string>,
) {
  const queued = queues.get(procedureCode) ?? new Set<string>();
  for (const fieldId of fieldIds) queued.add(fieldId);
  if (queued.size > 0) queues.set(procedureCode, queued);
}

function turnMatchesProcedure(turn: ChatTurn, procedureCode: string | null) {
  // General pages have no form workspace to protect, so their chat may identify
  // any supported procedure. Once a procedure form is active, only that exact
  // procedure may update its shared state.
  return procedureCode === null || turn.procedure?.code === procedureCode;
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
  const requestControllers = useRef(new Map<string, AbortController>());
  const routeProcedureRef = useRef(procedureCode);
  const queuedFieldChanges = useRef(
    new Map<string, Map<string, JsonValue>>(),
  );
  const queuedFieldCommits = useRef(new Map<string, Set<string>>());
  const inMemoryWorkspaces = useRef(
    new Map<string, ProcedureWorkspaceState>(),
  );
  const fieldMutationQueue = useRef<Promise<unknown>>(Promise.resolve());
  const fieldQueueGeneration = useRef(0);
  const dispatchTracked = useCallback((action: WorkspaceAction) => {
    stateRef.current = procedureWorkspaceReducer(stateRef.current, action);
    dispatch(action);
  }, []);

  const abortFieldRequests = useCallback(() => {
    fieldQueueGeneration.current += 1;
    for (const controller of requestControllers.current.values()) controller.abort();
    requestControllers.current.clear();
    requestTokens.current.clear();
  }, []);

  useLayoutEffect(() => {
    const previousProcedureCode = routeProcedureRef.current;
    if (previousProcedureCode && previousProcedureCode !== procedureCode) {
      const snapshot = createWorkspaceRouteSnapshot(
        stateRef.current,
        previousProcedureCode,
      );
      if (snapshot) {
        inMemoryWorkspaces.current.set(
          previousProcedureCode,
          JSON.parse(snapshot.serializedState) as ProcedureWorkspaceState,
        );
        try {
          window.sessionStorage.setItem(
            storageKey(previousProcedureCode),
            snapshot.serializedState,
          );
        } catch {
          // The in-memory retry queue still protects this navigation even when
          // browser storage is unavailable.
        }
        queueFieldCommits(
          queuedFieldCommits.current,
          previousProcedureCode,
          snapshot.pendingFieldIds,
        );
      }
    }
    routeProcedureRef.current = procedureCode;
    abortFieldRequests();
    return abortFieldRequests;
  }, [abortFieldRequests, procedureCode]);

  useEffect(() => {
    stateRef.current = state;
    if (state.hydrated && state.procedure_code) {
      inMemoryWorkspaces.current.set(state.procedure_code, state);
      try {
        window.sessionStorage.setItem(
          storageKey(state.procedure_code),
          JSON.stringify(state),
        );
      } catch {
        // The in-memory snapshot keeps this tab usable when storage is blocked
        // or full. A page refresh may still lose that local-only draft.
      }
    }
  }, [state]);

  const setField = useCallback((fieldId: string, value: JsonValue) => {
    const targetProcedureCode = routeProcedureRef.current;
    if (!targetProcedureCode) return;
    if (
      stateRef.current.procedure_code !== targetProcedureCode ||
      !stateRef.current.hydrated
    ) {
      const queued =
        queuedFieldChanges.current.get(targetProcedureCode) ?? new Map<string, JsonValue>();
      queued.set(fieldId, value);
      queuedFieldChanges.current.set(targetProcedureCode, queued);
      return;
    }
    dispatchTracked({ type: "manual_change", fieldId, value });
  }, [dispatchTracked]);

  const applyTurn = useCallback((turn: ChatTurn, expectedRevision?: number) => {
    const before = stateRef.current;
    if (
      before.procedure_code !== routeProcedureRef.current ||
      !turnMatchesProcedure(turn, before.procedure_code)
    ) {
      return false;
    }
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

  const performFieldCommit = useCallback(async (
    fieldId: string,
  ): Promise<boolean> => {
    const snapshot = stateRef.current;
    const field = snapshot.fields[fieldId];
    const requestProcedureCode = snapshot.procedure_code;
    if (
      !field ||
      !requestProcedureCode ||
      routeProcedureRef.current !== requestProcedureCode
    ) return false;

    const token = crypto.randomUUID();
    requestControllers.current.get(fieldId)?.abort();
    const controller = new AbortController();
    requestControllers.current.set(fieldId, controller);
    requestTokens.current.set(fieldId, token);
    const requestIsActive = () =>
      !controller.signal.aborted &&
      requestControllers.current.get(fieldId) === controller &&
      requestTokens.current.get(fieldId) === token &&
      routeProcedureRef.current === requestProcedureCode &&
      stateRef.current.procedure_code === requestProcedureCode;
    dispatchTracked({ type: "sync_start", fieldId });
    try {
      let expectedRevision = snapshot.revision;
      const postField = () =>
        fetch("/api/chat/field", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            field_id: fieldId,
            value: field.value,
            expected_revision: expectedRevision,
            context,
          }),
          signal: controller.signal,
        });
      let response = await postField();
      if ((response.status === 404 || response.status === 410) && requestIsActive()) {
        dispatchTracked({ type: "session_recreated" });
        expectedRevision = 0;
        await createChatSession(context, controller.signal);
        if (!requestIsActive()) return false;
        response = await postField();
      }
      const body = (await response.json()) as
        | ChatTurn
        | { error?: { code?: string; message?: string } };
      if (!requestIsActive()) return false;
      if (response.status === 409) {
        const responseError = "error" in body ? body.error : undefined;
        if (responseError?.code !== "session_context_mismatch") {
          dispatchTracked({ type: "stale" });
        }
        const recovered = await fetch("/api/chat/session", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (requestIsActive() && recovered.ok) {
          const recoveredSession = (await recovered.json()) as ChatSession;
          publishChatSession(recoveredSession);
        }
        if (requestIsActive()) {
          dispatchTracked({
            type: "sync_error",
            fieldId,
            message:
              responseError?.message ||
              "Giá trị mới vẫn được giữ trên biểu mẫu nhưng chưa đồng bộ vào phiên trợ lý.",
          });
        }
        return false;
      }
      if (!response.ok || !("draft" in body)) {
        const message = "error" in body ? body.error?.message : undefined;
        dispatchTracked({
          type: "sync_error",
          fieldId,
          message: message || "AI chưa đồng bộ được; giá trị vẫn được giữ trên biểu mẫu.",
        });
        return false;
      }
      if (applyTurn(body, expectedRevision)) {
        publishChatTurn(body);
        return true;
      } else if (requestIsActive()) {
        dispatchTracked({
          type: "sync_error",
          fieldId,
          message: "Giá trị mới vẫn được giữ trên biểu mẫu nhưng chưa đồng bộ vào phiên trợ lý.",
        });
      }
      return false;
    } catch {
      if (requestIsActive()) {
        dispatchTracked({
          type: "sync_error",
          fieldId,
          message: "AI đang quá hạn hoặc mất kết nối; giá trị vẫn được giữ trên biểu mẫu.",
        });
      }
      return false;
    } finally {
      if (requestControllers.current.get(fieldId) === controller) {
        requestControllers.current.delete(fieldId);
      }
      if (requestTokens.current.get(fieldId) === token) requestTokens.current.delete(fieldId);
    }
  }, [applyTurn, context, dispatchTracked]);

  const runDraftMutation = useCallback(
    <T,>(mutation: (currentRevision: number) => Promise<T>) => {
      const requestGeneration = fieldQueueGeneration.current;
      const run = async () => {
        if (fieldQueueGeneration.current !== requestGeneration) return;
        return mutation(stateRef.current.revision);
      };
      const queued = fieldMutationQueue.current.then(run, run);
      fieldMutationQueue.current = queued.catch(() => undefined);
      return queued;
    },
    [],
  );

  const commitField = useCallback(
    async (fieldId: string): Promise<boolean> => {
      const targetProcedureCode = routeProcedureRef.current;
      if (
        targetProcedureCode &&
        (stateRef.current.procedure_code !== targetProcedureCode ||
          !stateRef.current.hydrated)
      ) {
        const queued =
          queuedFieldCommits.current.get(targetProcedureCode) ?? new Set<string>();
        queued.add(fieldId);
        queuedFieldCommits.current.set(targetProcedureCode, queued);
        return false;
      }
      return (await runDraftMutation(() => performFieldCommit(fieldId))) ?? false;
    },
    [performFieldCommit, runDraftMutation],
  );

  const syncFields = useCallback(async () => {
    const targetProcedureCode = routeProcedureRef.current;
    const maxPasses = 4;
    if (!targetProcedureCode) return stateRef.current.revision;

    for (let pass = 0; pass < maxPasses; pass += 1) {
      if (
        routeProcedureRef.current !== targetProcedureCode ||
        stateRef.current.procedure_code !== targetProcedureCode
      ) {
        throw new Error("Trang đã thay đổi trước khi biểu mẫu đồng bộ xong.");
      }

      const fieldIds = getPendingFieldCommitIds(stateRef.current);
      if (fieldIds.length === 0) return stateRef.current.revision;

      for (const fieldId of fieldIds) {
        const field = stateRef.current.fields[fieldId];
        if (!field) continue;
        const synced = await commitField(fieldId);
        if (!synced) {
          throw new Error(
            "Chưa thể đồng bộ đầy đủ biểu mẫu. Dữ liệu bạn nhập vẫn được giữ lại; hãy thử lại.",
          );
        }
      }
    }

    if (getPendingFieldCommitIds(stateRef.current).length === 0) {
      return stateRef.current.revision;
    }

    throw new Error(
      "Biểu mẫu tiếp tục thay đổi trong lúc đồng bộ. Dữ liệu vẫn được giữ lại; hãy thử lại.",
    );
  }, [commitField]);

  useEffect(() => {
    if (!procedureCode) {
      dispatchTracked({ type: "activate", procedureCode: null });
      return;
    }
    const persisted =
      inMemoryWorkspaces.current.get(procedureCode) ?? readPersisted(procedureCode);
    dispatchTracked({
      type: "hydrate",
      state: persisted ?? { ...emptyWorkspace, procedure_code: procedureCode },
    });
    const queuedChanges = queuedFieldChanges.current.get(procedureCode);
    if (queuedChanges) {
      for (const [fieldId, value] of queuedChanges) {
        dispatchTracked({ type: "manual_change", fieldId, value });
      }
      queuedFieldChanges.current.delete(procedureCode);
    }
    const commits = queuedFieldCommits.current.get(procedureCode);
    const pendingFieldIds = new Set(commits);
    for (const fieldId of getPendingFieldCommitIds(stateRef.current)) {
      pendingFieldIds.add(fieldId);
    }
    queuedFieldCommits.current.delete(procedureCode);
    for (const fieldId of pendingFieldIds) {
      void commitField(fieldId);
    }
  }, [commitField, dispatchTracked, procedureCode]);

  const applySuggestion = useCallback(
    (
      suggestion: ChatSuggestion,
      action: "accept" | "reject" | "edit",
      turn: ChatTurn,
      value?: JsonValue,
    ) => {
      const activeProcedureCode = stateRef.current.procedure_code;
      if (
        activeProcedureCode !== routeProcedureRef.current ||
        !turnMatchesProcedure(turn, activeProcedureCode)
      ) return;
      dispatchTracked({ type: "suggestion_resolved", suggestion, action, turn, value });
    },
    [dispatchTracked],
  );

  const resetWorkspace = useCallback(() => {
    abortFieldRequests();
    queuedFieldChanges.current.clear();
    queuedFieldCommits.current.clear();
    const currentProcedureCode = stateRef.current.procedure_code;
    if (currentProcedureCode) {
      inMemoryWorkspaces.current.delete(currentProcedureCode);
      try {
        window.sessionStorage.removeItem(storageKey(currentProcedureCode));
      } catch {
        // Reset still succeeds in memory when browser storage is unavailable.
      }
    }
    dispatchTracked({ type: "reset", procedureCode: stateRef.current.procedure_code });
  }, [abortFieldRequests, dispatchTracked]);

  const exposedState = useMemo(
    () =>
      state.procedure_code === procedureCode
        ? state
        : { ...emptyWorkspace, procedure_code: procedureCode },
    [procedureCode, state],
  );

  const isDirty = useCallback(
    (fieldId: string) => Boolean(exposedState.fields[fieldId]?.dirty),
    [exposedState.fields],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      state: exposedState,
      setField,
      commitField,
      syncFields,
      runDraftMutation,
      applyTurn,
      applySuggestion,
      markStale: () => dispatchTracked({ type: "stale" }),
      rebaseSession: () => dispatchTracked({ type: "session_recreated" }),
      resetWorkspace,
      isDirty,
    }),
    [applySuggestion, applyTurn, commitField, dispatchTracked, exposedState, isDirty, resetWorkspace, runDraftMutation, setField, syncFields],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useProcedureWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useProcedureWorkspace must be used inside ProcedureWorkspaceProvider");
  return value;
}
