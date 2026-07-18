import type { ChatSessionContext } from "@/types/chat";

const procedureContexts = [
  {
    slug: "dang-ky-ket-hon-co-yeu-to-nuoc-ngoai",
    code: "2.000806",
    title: "Đăng ký kết hôn có yếu tố nước ngoài",
  },
  {
    slug: "thay-doi-cai-chinh-ho-tich-co-yeu-to-nuoc-ngoai",
    code: "2.000748",
    title: "Thay đổi, cải chính hộ tịch có yếu tố nước ngoài",
  },
  {
    slug: "thay-doi-cai-chinh-ho-tich",
    code: "1.004859",
    title: "Thay đổi, cải chính thông tin hộ tịch",
  },
  {
    slug: "dang-ky-ket-hon",
    code: "1.000894",
    title: "Đăng ký kết hôn",
  },
] as const;

export function getChatSessionContext(pathname: string): ChatSessionContext {
  const matched = procedureContexts.find(({ slug }) =>
    pathname.split("/").includes(slug),
  );

  return {
    route: pathname,
    ...(matched
      ? {
          procedure_code: matched.code,
          procedure_title: matched.title,
        }
      : { procedure_title: "Hôn nhân và gia đình" }),
  };
}
