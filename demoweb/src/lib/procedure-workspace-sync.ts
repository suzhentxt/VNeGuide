import type { ProcedureWorkspaceState } from "@/types/chat";

export interface WorkspaceRouteSnapshot {
  serializedState: string;
  pendingFieldIds: string[];
}

export function getPendingFieldCommitIds(
  state: ProcedureWorkspaceState,
): string[] {
  return Object.entries(state.fields)
    .filter(([, field]) =>
      field.sync_status === "dirty" ||
      field.sync_status === "saving" ||
      field.sync_status === "error"
    )
    .map(([fieldId]) => fieldId);
}

export function createWorkspaceRouteSnapshot(
  state: ProcedureWorkspaceState,
  procedureCode: string | null,
): WorkspaceRouteSnapshot | null {
  if (
    !procedureCode ||
    !state.hydrated ||
    state.procedure_code !== procedureCode
  ) {
    return null;
  }

  return {
    serializedState: JSON.stringify(state),
    pendingFieldIds: getPendingFieldCommitIds(state),
  };
}
