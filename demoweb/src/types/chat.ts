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
    revision: number;
    confirmed_fields: string[];
    dirty_fields: string[];
  };
  messages: ChatMessage[];
  suggestions: ChatSuggestion[];
  missing_fields: Array<{ field_id: string; label: string }>;
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
  turn: ChatTurn | null;
}

export interface ChatApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}
