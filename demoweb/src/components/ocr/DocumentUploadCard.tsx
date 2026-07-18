"use client";

import { AlertTriangle, CheckCircle2, FileSearch, LoaderCircle, RefreshCw, Upload, XCircle } from "lucide-react";
import { type ChangeEvent, useState } from "react";

import { type DocumentKind, useDocumentValidation } from "./DocumentValidationProvider";

const labels: Record<DocumentKind, string> = {
  legal_dwelling: "Giấy tờ chứng minh chỗ ở hợp pháp",
  minor_consent: "Ý kiến đồng ý của cha, mẹ hoặc người giám hộ",
};

export function DocumentUploadCard({ kind, compact = false }: { kind: DocumentKind; compact?: boolean }) {
  const { documents, required, upload, acknowledgeReview, reset } = useDocumentValidation();
  const [demoConfirmed, setDemoConfirmed] = useState(false);
  const state = documents[kind];
  const busy = ["uploading", "queued", "running"].includes(state.status);

  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) void upload(kind, file);
  };

  return (
    <section className={`rounded-xl border-2 p-4 ${compact ? "bg-white" : "bg-[#fffdf9]"} ${required[kind] ? "border-[#ce7a58]" : "border-[#d9e2ec]"}`}>
      <div className="flex items-start gap-3">
        <FileSearch className="mt-0.5 size-5 shrink-0 text-[#903938]" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-extrabold text-[#1e2f41]">{labels[kind]}</p>
          <p className="mt-1 text-sm text-[#667085]">{required[kind] ? "Cần kiểm tra cho hồ sơ này" : "Không bắt buộc theo thông tin bước 1"}</p>
          {state.fileName ? <p className="mt-1 truncate text-sm font-bold text-[#24496f]">Tệp: {state.fileName}</p> : null}
        </div>
      </div>

      {state.status === "pass" ? <p className="mt-3 flex gap-2 text-sm font-bold text-[#25633f]"><CheckCircle2 className="size-5 shrink-0" />Tài liệu đạt kiểm tra hỗ trợ.</p> : null}
      {state.status === "fail" ? <p className="mt-3 flex gap-2 text-sm font-bold text-[#8b1e1e]"><XCircle className="size-5 shrink-0" />Tài liệu sai nhóm rõ ràng; vui lòng thay tệp.</p> : null}
      {state.status === "needs_review" ? (
        <div className="mt-3 rounded-lg border border-[#f0c36a] bg-[#fff8df] p-3 text-sm text-[#704d09]">
          <p className="flex gap-2 font-bold"><AlertTriangle className="size-5 shrink-0" />OCR chưa thể kết luận; tài liệu sẽ cần kiểm tra chính thức.</p>
          {required[kind] && !state.reviewAcknowledged ? <button className="mt-3 min-h-11 rounded-lg bg-[#704d09] px-3 font-bold text-white" onClick={() => acknowledgeReview(kind)} type="button">Tôi hiểu và muốn tiếp tục</button> : null}
        </div>
      ) : null}
      {busy ? <p className="mt-3 flex gap-2 text-sm font-bold text-[#24496f]"><LoaderCircle className="size-5 animate-spin" />Đang kiểm tra tài liệu…</p> : null}
      {state.error && state.status !== "needs_review" ? <p className="mt-3 text-sm font-bold text-[#8b1e1e]">{state.error}</p> : null}
      {state.checks.length ? <ul className="mt-3 space-y-1 text-sm text-[#52606d]">{state.checks.map((check) => <li key={check.code}>• {check.message}: {check.result === "pass" ? "đạt" : check.result === "fail" ? "không đạt" : "chưa rõ"}</li>)}</ul> : null}

      <label className="mt-4 flex items-start gap-2 text-sm leading-5 text-[#52606d]">
        <input checked={demoConfirmed} className="mt-1 accent-[#903938]" onChange={(event) => setDemoConfirmed(event.target.checked)} type="checkbox" />
        Tôi xác nhận đây là tài liệu demo, tổng hợp hoặc đã ẩn danh; không chứa dữ liệu cá nhân thật.
      </label>
      <div className="mt-3 flex flex-wrap gap-2">
        <label className={`inline-flex min-h-11 items-center justify-center rounded-lg px-4 font-bold ${demoConfirmed && !busy ? "cursor-pointer bg-[#903938] text-white" : "cursor-not-allowed bg-[#d9e2ec] text-[#7a8793]"}`}>
          <Upload className="mr-2 size-5" />{state.fileName ? "Thay tệp" : "Tải tài liệu"}
          <input accept="image/jpeg,image/png,application/pdf" className="sr-only" disabled={!demoConfirmed || busy} onChange={choose} type="file" />
        </label>
        {state.fileName && !busy ? <button className="inline-flex min-h-11 items-center rounded-lg border border-[#cbd5df] px-3 font-bold text-[#334155]" onClick={() => reset(kind)} type="button"><RefreshCw className="mr-2 size-4" />Bỏ kết quả</button> : null}
      </div>
    </section>
  );
}
