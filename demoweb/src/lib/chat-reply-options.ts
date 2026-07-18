import type { ChatTurn } from "../types/chat.ts";

const BIRTH_SCOPE_OPTIONS = [
  "Tôi muốn xin bản sao Giấy khai sinh",
  "Tôi muốn đăng ký khai sinh mới",
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

  return [];
}
