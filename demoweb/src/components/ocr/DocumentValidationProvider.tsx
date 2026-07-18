"use client";

import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { documentBlockingMessages, documentRequirements } from "@/lib/document-validation";

export type DocumentKind = "legal_dwelling" | "minor_consent";
export type DocumentStatus = "idle" | "uploading" | "queued" | "running" | "pass" | "needs_review" | "fail" | "error";

export interface DocumentValidationState {
  fileName: string | null;
  status: DocumentStatus;
}

const emptyState = (): DocumentValidationState => ({
  fileName: null,
  status: "idle",
});

interface DocumentValidationContextValue {
  documents: Record<DocumentKind, DocumentValidationState>;
  required: Record<DocumentKind, boolean>;
  blockingMessages: string[];
  upload: (kind: DocumentKind, file: File) => Promise<void>;
  reset: (kind: DocumentKind) => void;
}

const Context = createContext<DocumentValidationContextValue | null>(null);
const RESULT_STATUSES = new Set<DocumentStatus>(["queued", "running", "pass", "needs_review", "fail"]);

async function responseBody(response: Response) {
  const body = await response.json() as Record<string, unknown>;
  if (!response.ok) throw new Error("ocr_request_failed");
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
    setDocument(kind, () => ({ fileName: file.name, status: "uploading" }));
    try {
      const createdResponse = await fetch("/api/ocr/jobs", {
        method: "POST",
        headers: { "Content-Type": file.type, "X-Document-Kind": kind },
        body: file,
      });
      if (createdResponse.status === 503) {
        setDocument(kind, (current) => ({ ...current, status: "needs_review" }));
        return;
      }
      const created = await responseBody(createdResponse);
      if (typeof created.job_id !== "string" || !created.job_id) {
        setDocument(kind, (current) => ({ ...current, status: "error" }));
        return;
      }
      setDocument(kind, (current) => ({ ...current, status: "queued" }));

      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 750));
        const polled = await fetch(`/api/ocr/jobs/${encodeURIComponent(created.job_id)}`, { cache: "no-store" });
        if (polled.status === 503) {
          setDocument(kind, (current) => ({ ...current, status: "needs_review" }));
          return;
        }
        const result = await responseBody(polled);
        const status = typeof result.status === "string" && RESULT_STATUSES.has(result.status as DocumentStatus)
          ? result.status as DocumentStatus
          : "error";
        setDocument(kind, (current) => ({ ...current, status }));
        if (!["queued", "running"].includes(status)) return;
      }
      setDocument(kind, (current) => ({ ...current, status: "needs_review" }));
    } catch {
      setDocument(kind, (current) => ({ ...current, status: "error" }));
    }
  }, [setDocument]);

  const reset = useCallback((kind: DocumentKind) => {
    setDocument(kind, () => emptyState());
  }, [setDocument]);

  const blockingMessages = documentBlockingMessages(required, documents);

  return (
    <Context.Provider value={{ documents, required, blockingMessages, upload, reset }}>
      {children}
    </Context.Provider>
  );
}

export function useDocumentValidation() {
  const value = useContext(Context);
  if (!value) throw new Error("useDocumentValidation must be used inside DocumentValidationProvider");
  return value;
}
