import type { ChatTurn } from "../types/chat.ts";

const BIRTH_SCOPE_OPTIONS = [
  "Tôi muốn xin bản sao Giấy khai sinh",
  "Tôi muốn đăng ký khai sinh mới",
] as const;

const REQUESTER_TYPE_OPTIONS = [
  "Xin cho bản thân tôi",
  "Tôi là người được ủy quyền",
  "Tôi đại diện cơ quan/tổ chức",
  "Tôi chưa rõ",
] as const;

export function getChatReplyOptions(turn: ChatTurn | null): string[] {
  if (!turn || turn.next_action !== "ask_clarification") return [];
  const normalizedReply = turn.reply.toLocaleLowerCase("vi");

  if (
    !turn.procedure &&
    normalizedReply.includes("xin bản sao") &&
    normalizedReply.includes("đăng ký khai sinh mới")
  ) {
    return [...BIRTH_SCOPE_OPTIONS];
  }

  if (
    turn.procedure?.code === "2.000635" &&
    turn.missing_fields[0]?.field_id === "requester_type"
  ) {
    return [...REQUESTER_TYPE_OPTIONS];
  }

  return [];
}
