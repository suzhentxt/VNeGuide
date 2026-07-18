import type { ChatSessionContext } from "@/types/chat";

export const procedureContexts = [
  {
    slug: "cap-ban-sao-giay-khai-sinh",
    code: "2.000635",
    title: "Cấp bản sao Giấy khai sinh",
    serviceId: "birth-copy-guidance",
  },
  {
    slug: "xac-nhan-dieu-kien-nha-o",
    code: "1.013314",
    title: "Xác nhận điều kiện diện tích bình quân nhà ở",
    serviceId: "housing-confirmation-guidance",
  },
  {
    slug: "dang-ky-tam-tru",
    code: "1.004194",
    title: "Đăng ký tạm trú",
    serviceId: "temporary-residence-guidance",
  },
] as const;

export function getProcedureContextByCode(code: string) {
  return procedureContexts.find((procedure) => procedure.code === code);
}

export function getConfirmedSubmissionRoute(code: string) {
  const procedure = getProcedureContextByCode(code);
  if (!procedure) return null;
  const query = new URLSearchParams({
    service: procedure.serviceId,
    confirmed: "1",
  });
  return `/hon-nhan-va-gia-dinh/${procedure.slug}/nop-ho-so?${query.toString()}`;
}

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
