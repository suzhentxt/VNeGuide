"use client";

import { CheckCircle2, FileSearch, LoaderCircle, RefreshCw, Upload, XCircle } from "lucide-react";
import { type ChangeEvent, useState } from "react";

import { documentResultPresentation } from "@/lib/document-validation";

import { type DocumentKind, useDocumentValidation } from "./DocumentValidationProvider";

const labels: Record<DocumentKind, string> = {
  legal_dwelling: "Giấy tờ chứng minh chỗ ở hợp pháp",
  minor_consent: "Ý kiến đồng ý của cha, mẹ hoặc người giám hộ",
};

export function DocumentUploadCard({ kind, compact = false }: { kind: DocumentKind; compact?: boolean }) {
  const { documents, required, upload, reset } = useDocumentValidation();
  const [demoConfirmed, setDemoConfirmed] = useState(false);
  const state = documents[kind];
  const busy = ["uploading", "queued", "running"].includes(state.status);
  const result = documentResultPresentation(state.status);

  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) void upload(kind, file);
  };

  return (
    <section className={`min-w-0 max-w-full overflow-hidden rounded-xl border-2 ${compact ? "bg-white p-3" : "bg-[#fffdf9] p-4"} ${required[kind] ? "border-[#ce7a58]" : "border-[#d9e2ec]"}`}>
      <div className="flex min-w-0 items-start gap-3">
        <FileSearch className="mt-0.5 size-5 shrink-0 text-[#903938]" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className={`${compact ? "text-sm" : ""} break-words font-extrabold text-[#1e2f41]`}>{labels[kind]}</p>
          {!compact ? <p className="mt-1 text-sm text-[#667085]">{required[kind] ? "Cần kiểm tra cho hồ sơ này" : "Không bắt buộc theo thông tin bước 1"}</p> : null}
          {state.fileName ? <p className="mt-1 truncate text-xs font-bold text-[#24496f]" title={state.fileName}>Tệp: {state.fileName}</p> : null}
        </div>
      </div>

      <div aria-live="polite">
        {result === "invalid" ? (
          <p className="mt-3 flex items-start gap-2 rounded-lg border border-[#efb4b4] bg-[#fff1f1] p-2.5 text-sm font-bold text-[#8b1e1e]" role="alert">
            <XCircle className="size-5 shrink-0" aria-hidden="true" />Không hợp lệ
          </p>
        ) : null}
        {result === "valid_official_review" ? (
          <p className="mt-3 flex items-start gap-2 rounded-lg border border-[#98d0aa] bg-[#effaf2] p-2.5 text-sm font-bold text-[#25633f]" role="status">
            <CheckCircle2 className="size-5 shrink-0" aria-hidden="true" />
            <span>Hợp lệ, tài liệu sẽ cần kiểm tra chính thức</span>
          </p>
        ) : null}
        {busy ? (
          <p className="mt-3 flex items-start gap-2 text-sm font-bold text-[#24496f]" role="status">
            <LoaderCircle className="size-5 shrink-0 animate-spin" aria-hidden="true" />Đang kiểm tra tài liệu…
          </p>
        ) : null}
      </div>

      {!state.fileName ? (
        <label className="mt-3 flex min-w-0 items-start gap-2 text-xs leading-5 text-[#52606d]">
          <input checked={demoConfirmed} className="mt-1 shrink-0 accent-[#903938]" onChange={(event) => setDemoConfirmed(event.target.checked)} type="checkbox" />
          <span className="min-w-0 break-words">Tài liệu demo hoặc đã ẩn danh, không chứa dữ liệu cá nhân thật.</span>
        </label>
      ) : null}
      <div className="mt-3 flex min-w-0 flex-wrap gap-2">
        <label className={`inline-flex min-h-10 max-w-full items-center justify-center rounded-lg px-3 text-sm font-bold ${demoConfirmed && !busy ? "cursor-pointer bg-[#903938] text-white" : "cursor-not-allowed bg-[#d9e2ec] text-[#7a8793]"}`}>
          <Upload className="mr-2 size-4 shrink-0" aria-hidden="true" />{state.fileName ? "Thay tệp" : "Tải tài liệu"}
          <input accept="image/jpeg,image/png,application/pdf" className="sr-only" disabled={!demoConfirmed || busy} onChange={choose} type="file" />
        </label>
        {state.fileName && !busy ? (
          <button className="inline-flex min-h-10 max-w-full items-center rounded-lg border border-[#cbd5df] px-3 text-sm font-bold text-[#334155]" onClick={() => reset(kind)} type="button">
            <RefreshCw className="mr-2 size-4 shrink-0" aria-hidden="true" />Bỏ kết quả
          </button>
        ) : null}
      </div>
    </section>
  );
}
