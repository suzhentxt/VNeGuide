import type { ChatTurn } from "../types/chat.ts";

export type ChatValidationTone = "danger" | "incomplete" | "success" | "warning";

export interface ChatValidationPresentation {
  label: string;
  showReadinessScore: boolean;
  tone: ChatValidationTone;
}

const STATUS_PRESENTATIONS: Record<string, ChatValidationPresentation> = {
  needs_correction: {
    label: "Cần sửa thông tin",
    showReadinessScore: true,
    tone: "danger",
  },
  needs_official_review: {
    label: "Cần cơ quan có thẩm quyền kiểm tra",
    showReadinessScore: true,
    tone: "warning",
  },
  out_of_scope: {
    label: "Ngoài phạm vi hỗ trợ",
    showReadinessScore: false,
    tone: "warning",
  },
  ready_to_submit: {
    label: "Sẵn sàng kiểm tra lần cuối",
    showReadinessScore: true,
    tone: "success",
  },
};

export function getChatValidationPresentation(
  turn: ChatTurn | null,
): ChatValidationPresentation | null {
  if (!turn?.validation) return null;

  if (turn.missing_fields.length > 0 && turn.validation.status === "ready_to_submit") {
    return {
      label: "Hồ sơ chưa đủ thông tin",
      showReadinessScore: false,
      tone: "incomplete",
    };
  }

  return (
    STATUS_PRESENTATIONS[turn.validation.status] ?? {
      label: `Trạng thái kiểm tra: ${turn.validation.status}`,
      showReadinessScore: turn.validation.readiness_score !== null,
      tone: "warning",
    }
  );
}
