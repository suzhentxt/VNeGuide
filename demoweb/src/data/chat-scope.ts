import type {
  ChatSessionContext,
  ChatTurn,
  ProcedureWorkspaceState,
} from "@/types/chat";

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

export function getConfirmedProcedureRoute(code: string) {
  const procedure = getProcedureContextByCode(code);
  if (!procedure) return null;
  const query = new URLSearchParams({ confirmed: "1" });
  return `/hon-nhan-va-gia-dinh/${procedure.slug}?${query.toString()}`;
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

export function shouldRebindChatSession(
  sessionContext: ChatSessionContext | null | undefined,
  routeContext: ChatSessionContext,
): boolean {
  if (sessionContext === undefined) return false;
  return getChatContextKey(sessionContext) !== getChatContextKey(routeContext);
}

export function getChatContextKey(
  context: ChatSessionContext | null | undefined,
): string {
  return context?.procedure_code ?? "__general__";
}

export function shouldRebindChatWorkspace(
  sessionDraft: ChatTurn["draft"],
  routeContext: ChatSessionContext,
  workspace: ProcedureWorkspaceState,
): boolean {
  if (
    !routeContext.procedure_code ||
    !workspace.hydrated ||
    workspace.procedure_code !== routeContext.procedure_code
  ) return false;
  if (workspace.revision !== sessionDraft.revision) return true;

  const confirmed = new Set(sessionDraft.confirmed_fields);
  const dirty = new Set(sessionDraft.dirty_fields);
  return Object.entries(workspace.fields).some(
    ([fieldId, field]) =>
      JSON.stringify(sessionDraft.values[fieldId]) !== JSON.stringify(field.value) ||
      (field.confirmed && !confirmed.has(fieldId)) ||
      (field.dirty && !dirty.has(fieldId)),
  );
}
