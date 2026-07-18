"use client";

import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { documentBlockingMessages, documentRequirements } from "@/lib/document-validation";

export type DocumentKind = "legal_dwelling" | "minor_consent";
export type DocumentStatus = "idle" | "uploading" | "queued" | "running" | "pass" | "needs_review" | "fail" | "error";

export interface DocumentCheck {
  code: string;
  result: "pass" | "uncertain" | "fail";
  message: string;
}

export interface DocumentValidationState {
  fileName: string | null;
  status: DocumentStatus;
  checks: DocumentCheck[];
  warnings: string[];
  error: string | null;
  reviewAcknowledged: boolean;
}

const emptyState = (): DocumentValidationState => ({
  fileName: null,
  status: "idle",
  checks: [],
  warnings: [],
  error: null,
  reviewAcknowledged: false,
});

interface DocumentValidationContextValue {
  documents: Record<DocumentKind, DocumentValidationState>;
  required: Record<DocumentKind, boolean>;
  blockingMessages: string[];
  upload: (kind: DocumentKind, file: File) => Promise<void>;
  acknowledgeReview: (kind: DocumentKind) => void;
  reset: (kind: DocumentKind) => void;
}

const Context = createContext<DocumentValidationContextValue | null>(null);

async function responseBody(response: Response) {
  const body = await response.json() as Record<string, unknown>;
  if (!response.ok) {
    const error = body.error as { message?: string } | undefined;
    throw new Error(error?.message || "Không thể kiểm tra tài liệu.");
  }
  return body;
}

export function DocumentValidationProvider({ children }: { children: ReactNode }) {
  const workspace = useProcedureWorkspace();
  const [documents, setDocuments] = useState<Record<DocumentKind, DocumentValidationState>>({
    legal_dwelling: emptyState(),
    minor_consent: emptyState(),
  });

  const required = useMemo(() => documentRequirements(Object.fromEntries(
    Object.entries(workspace.state.fields).map(([fieldId, field]) => [fieldId, field.value]),
  )), [workspace.state.fields]);

  const setDocument = useCallback(
    (kind: DocumentKind, update: (current: DocumentValidationState) => DocumentValidationState) => {
      setDocuments((current) => ({ ...current, [kind]: update(current[kind]) }));
    },
    [],
  );

  const upload = useCallback(async (kind: DocumentKind, file: File) => {
    setDocument(kind, () => ({ ...emptyState(), fileName: file.name, status: "uploading" }));
    try {
      const createdResponse = await fetch("/api/ocr/jobs", {
        method: "POST",
        headers: { "Content-Type": file.type, "X-Document-Kind": kind },
        body: file,
      });
      if (createdResponse.status === 503) {
        const body = await createdResponse.json() as { error?: { message?: string } };
        setDocument(kind, (current) => ({
          ...current,
          status: "needs_review",
          error: body.error?.message ?? "OCR chưa sẵn sàng.",
          warnings: ["official_review_required"],
        }));
        return;
      }
      const created = await responseBody(createdResponse) as { job_id: string };
      setDocument(kind, (current) => ({ ...current, status: "queued" }));

      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 750));
        const polled = await fetch(`/api/ocr/jobs/${encodeURIComponent(created.job_id)}`, { cache: "no-store" });
        if (polled.status === 503) {
          setDocument(kind, (current) => ({
            ...current,
            status: "needs_review",
            error: "Không thể lấy kết quả OCR; tài liệu cần kiểm tra chính thức.",
            warnings: ["official_review_required"],
          }));
          return;
        }
        const result = await responseBody(polled) as {
          status: DocumentStatus;
          checks?: DocumentCheck[];
          warnings?: string[];
          error_code?: string | null;
        };
        setDocument(kind, (current) => ({
          ...current,
          status: result.status,
          checks: result.checks ?? [],
          warnings: result.warnings ?? [],
          error: result.error_code ? "OCR chưa thể kết luận; tài liệu cần kiểm tra chính thức." : null,
        }));
        if (!["queued", "running"].includes(result.status)) return;
      }
      setDocument(kind, (current) => ({
        ...current,
        status: "needs_review",
        error: "OCR phản hồi quá thời gian; tài liệu cần kiểm tra chính thức.",
        warnings: ["official_review_required"],
      }));
    } catch (error) {
      setDocument(kind, (current) => ({
        ...current,
        status: "error",
        error: error instanceof Error ? error.message : "Không thể kiểm tra tài liệu.",
      }));
    }
  }, [setDocument]);

  const acknowledgeReview = useCallback((kind: DocumentKind) => {
    setDocument(kind, (current) => ({ ...current, reviewAcknowledged: true }));
  }, [setDocument]);

  const reset = useCallback((kind: DocumentKind) => {
    setDocument(kind, () => emptyState());
  }, [setDocument]);

  const blockingMessages = documentBlockingMessages(required, documents);

  return (
    <Context.Provider value={{ documents, required, blockingMessages, upload, acknowledgeReview, reset }}>
      {children}
    </Context.Provider>
  );
}

export function useDocumentValidation() {
  const value = useContext(Context);
  if (!value) throw new Error("useDocumentValidation must be used inside DocumentValidationProvider");
  return value;
}
