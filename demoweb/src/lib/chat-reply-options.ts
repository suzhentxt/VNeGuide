import type { ChatTurn } from "../types/chat.ts";

const BIRTH_SCOPE_OPTIONS = [
  "Tôi muốn xin bản sao Giấy khai sinh",
  "Tôi muốn đăng ký khai sinh mới",
] as const;

const SERVICE_OPTIONS = [
  "Tôi muốn đăng ký tạm trú",
  "Tôi muốn xác nhận điều kiện nhà ở để đăng ký thường trú",
  "Tôi muốn xin bản sao Giấy khai sinh",
] as const;

const SERVICE_SWITCH_OPTIONS = [
  "Đúng, chuyển sang dịch vụ mới",
  "Không, giữ dịch vụ hiện tại",
] as const;

export function getChatReplyOptions(turn: ChatTurn | null): string[] {
  if (!turn || turn.next_action !== "ask_clarification") return [];
  const normalizedReply = turn.reply.toLocaleLowerCase("vi");

  if (
    normalizedReply.includes("bạn có muốn chuyển") &&
    normalizedReply.includes("dịch vụ mới")
  ) {
    return [...SERVICE_SWITCH_OPTIONS];
  }

  if (
    !turn.procedure &&
    normalizedReply.includes("xin bản sao") &&
    normalizedReply.includes("đăng ký khai sinh mới")
  ) {
    return [...BIRTH_SCOPE_OPTIONS];
  }

  if (!turn.procedure) return [...SERVICE_OPTIONS];

  return [];
}
