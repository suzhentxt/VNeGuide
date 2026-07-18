export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface ChatSessionContext {
  procedure_code?: string;
  procedure_title?: string;
  route: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatSuggestion {
  id: string;
  field_id: string;
  label: string;
  current_value: JsonValue;
  suggested_value: JsonValue;
  evidence: string;
  status: "pending" | "accepted" | "rejected" | "edited";
  revision: number;
}

export interface ChatTurn {
  reply: string;
  next_action: string;
  procedure: { code: string; name: string } | null;
  draft: {
    values: Record<string, JsonValue>;
    revision: number;
    confirmed_fields: string[];
    dirty_fields: string[];
    pack_version: string | null;
  };
  messages: ChatMessage[];
  suggestions: ChatSuggestion[];
  missing_fields: Array<{ field_id: string; label: string; choices: JsonValue[] }>;
  validation: {
    status: string;
    readiness_score: number | null;
    issues: Array<{
      rule_id: string;
      severity: string;
      message: string;
      field_id: string | null;
      suggestion: string;
      source_ids: string[];
    }>;
  } | null;
  sources: Array<{
    id: string;
    title: string;
    publisher: string;
    url: string;
    verified_at: string;
  }>;
}

export interface ChatSession {
  expires_in_seconds: number;
  context: ChatSessionContext | null;
  context_supported: boolean;
  scope_warning: string | null;
  draft: ChatTurn["draft"];
  turn: ChatTurn | null;
}

export interface ChatApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}

export type FieldSyncStatus = "idle" | "dirty" | "saving" | "saved" | "error";

export interface ProcedureFieldState {
  value: JsonValue;
  confirmed: boolean;
  dirty: boolean;
  source?: "manual" | "assistant" | "wallet";
  sync_status: FieldSyncStatus;
  error: string | null;
}

export interface ProcedureWorkspaceState {
  procedure_code: string | null;
  revision: number;
  fields: Record<string, ProcedureFieldState>;
  validation_issues: NonNullable<ChatTurn["validation"]>["issues"];
  hydrated: boolean;
  recovery_notice: string | null;
}
