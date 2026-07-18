import type { JsonValue } from "@/types/chat";

export type OcrDocumentKind = "legal_dwelling" | "minor_consent";
type GateState = {
  status: string;
};

export type DocumentResultPresentation = "invalid" | "valid_official_review";

const labels: Record<OcrDocumentKind, string> = {
  legal_dwelling: "Giấy tờ chứng minh chỗ ở hợp pháp",
  minor_consent: "Ý kiến đồng ý của cha, mẹ hoặc người giám hộ",
};

export function documentRequirements(values: Record<string, JsonValue | undefined>) {
  return {
    legal_dwelling: values.legal_dwelling_data_retrievable === false,
    minor_consent:
      values.applicant_is_minor === true && values.minor_consent_present !== true,
  } satisfies Record<OcrDocumentKind, boolean>;
}

export function documentBlockingMessages(
  required: Record<OcrDocumentKind, boolean>,
  documents: Record<OcrDocumentKind, GateState>,
) {
  return (Object.keys(required) as OcrDocumentKind[]).flatMap((kind) => {
    if (!required[kind]) return [];
    const document = documents[kind];
    const label = labels[kind];
    if (document.status === "pass") return [];
    if (["queued", "running", "uploading"].includes(document.status)) {
      return [`${label}: đang kiểm tra`];
    }
    if (["fail", "needs_review", "error"].includes(document.status)) {
      return [`${label}: không hợp lệ, cần thay tài liệu`];
    }
    return [`${label}: chưa có kết quả kiểm tra`];
  });
}

export function documentResultPresentation(status: string): DocumentResultPresentation | null {
  if (status === "pass") return "valid_official_review";
  if (["fail", "needs_review", "error"].includes(status)) return "invalid";
  return null;
}
