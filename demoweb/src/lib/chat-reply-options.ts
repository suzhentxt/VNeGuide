import type { ChatTurn } from "../types/chat.ts";

const BIRTH_SCOPE_OPTIONS = [
  "Tôi muốn xin bản sao Giấy khai sinh",
  "Tôi muốn đăng ký khai sinh mới",
] as const;

const CONFIRM_PROCEDURE_OPTIONS = [
  "Đúng, tiếp tục thủ tục này",
  "Không đúng, chọn thủ tục khác",
] as const;

const CONFIRM_SUGGESTION_OPTIONS = [
  "Đồng ý tất cả đề xuất",
  "Tôi sẽ xem từng mục",
] as const;

const REQUEST_CORRECTION_OPTIONS = [
  "Tôi sẽ sửa thông tin",
  "Bắt đầu lại từ đầu",
] as const;

const COMPLETE_OPTIONS = [
  "Kiểm tra lại hồ sơ",
  "Bắt đầu thủ tục khác",
] as const;

export function getChatReplyOptions(turn: ChatTurn | null): string[] {
  if (!turn) return [];

  switch (turn.next_action) {
    case "ask_clarification": {
      const normalizedReply = turn.reply.toLocaleLowerCase("vi");
      if (
        !turn.procedure &&
        normalizedReply.includes("xin bản sao") &&
        normalizedReply.includes("đăng ký khai sinh mới")
      ) {
        return [...BIRTH_SCOPE_OPTIONS];
      }
      return [];
    }
    case "confirm_procedure":
      return [...CONFIRM_PROCEDURE_OPTIONS];
    case "confirm_suggestion":
      return [...CONFIRM_SUGGESTION_OPTIONS];
    case "request_correction":
      return [...REQUEST_CORRECTION_OPTIONS];
    case "complete":
      return [...COMPLETE_OPTIONS];
    default:
      return [];
  }
}
