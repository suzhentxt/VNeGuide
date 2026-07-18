import type { JsonValue } from "@/types/chat";

export type OcrDocumentKind = "legal_dwelling" | "minor_consent";
type GateState = {
  status: string;
  reviewAcknowledged: boolean;
};

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
    if (document.status === "needs_review" && document.reviewAcknowledged) return [];
    if (document.status === "needs_review") return [`${label}: xác nhận chuyển kiểm tra chính thức`];
    if (["queued", "running", "uploading"].includes(document.status)) {
      return [`${label}: đang kiểm tra`];
    }
    if (document.status === "fail") return [`${label}: cần thay đúng tài liệu`];
    return [`${label}: chưa có kết quả kiểm tra`];
  });
}
