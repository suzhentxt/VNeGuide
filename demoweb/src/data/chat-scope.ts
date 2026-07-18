import type { ChatSessionContext } from "@/types/chat";

const procedureContexts = [
  {
    slug: "cap-ban-sao-giay-khai-sinh",
    code: "2.000635",
    title: "Cấp bản sao Giấy khai sinh",
  },
  {
    slug: "xac-nhan-dieu-kien-nha-o",
    code: "1.013314",
    title: "Xác nhận điều kiện diện tích bình quân nhà ở",
  },
  {
    slug: "dang-ky-tam-tru",
    code: "1.004194",
    title: "Đăng ký tạm trú",
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
      : { procedure_title: "Ba thủ tục VNeGuide hỗ trợ" }),
  };
}
