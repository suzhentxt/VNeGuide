import type { ChatTurn } from "../types/chat.ts";

export type ChatStatusTone = "danger" | "warning" | "info" | "success";

export interface ChatStatusPresentation {
  label: string;
  readinessScore: number | null;
  tone: ChatStatusTone;
}

export function getReviewedSourceHref(url: string): string | null {
  const href = url.trim();
  return href.length > 0 ? href : null;
}

const SUPPLEMENT_ACTIONS = new Set(["ask_clarification", "manual_input"]);

/**
 * Convert backend workflow state into language suitable for end users.
 *
 * The order is intentional: a terminal validation result must not be hidden by
 * a lower-priority conversational action, and a readiness score is meaningful
 * only after the workflow has actually completed with no missing fields.
 */
export function getChatStatusPresentation(turn: ChatTurn): ChatStatusPresentation {
  const validationStatus = turn.validation?.status;

  if (validationStatus === "out_of_scope" || turn.next_action === "out_of_scope") {
    return presentation("Ngoài phạm vi hỗ trợ", "warning");
  }

  if (
    validationStatus === "needs_correction" ||
    turn.next_action === "request_correction"
  ) {
    return presentation("Cần sửa thông tin", "danger");
  }

  if (
    validationStatus === "needs_official_review" ||
    turn.next_action === "request_official_review"
  ) {
    return presentation("Cần cơ quan có thẩm quyền kiểm tra", "warning");
  }

  if (
    turn.next_action === "confirm_suggestion" ||
    turn.suggestions.some((suggestion) => suggestion.status === "pending")
  ) {
    return presentation("Đang chờ xác nhận đề xuất", "info");
  }

  if (turn.next_action === "confirm_procedure") {
    return presentation("Đang xác nhận thủ tục", "info");
  }

  if (
    turn.missing_fields.length > 0 ||
    SUPPLEMENT_ACTIONS.has(turn.next_action)
  ) {
    return presentation("Đang bổ sung thông tin", "info");
  }

  if (
    turn.next_action === "complete" &&
    turn.missing_fields.length === 0 &&
    validationStatus === "ready_to_submit"
  ) {
    return {
      label: "Sẵn sàng kiểm tra trước khi nộp",
      readinessScore: turn.validation?.readiness_score ?? null,
      tone: "success",
    };
  }

  if (turn.next_action === "retry") {
    return presentation("Kết nối AI đang gián đoạn", "warning");
  }

  return presentation("Đang xử lý", "info");
}

function presentation(
  label: string,
  tone: ChatStatusTone,
): ChatStatusPresentation {
  return { label, readinessScore: null, tone };
}
