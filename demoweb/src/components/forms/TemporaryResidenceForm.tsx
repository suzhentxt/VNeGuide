"use client";

import { AlertTriangle, CheckCircle2, CloudOff, Save, ShieldCheck } from "lucide-react";
import { cloneElement, type FormEvent, type ReactElement, useMemo, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { markDeclarationSaved } from "@/lib/procedure-selection";
import type { ProcedureExperience } from "@/data/procedure-experiences";
import type { JsonValue } from "@/types/chat";

const inputClass =
  "min-h-12 w-full rounded-lg border border-[#cbd5df] bg-white px-3 py-2 text-base text-[#1e2f41] outline-none transition focus:border-[#ce7a58] focus:ring-2 focus:ring-[#ce7a58]/20 aria-[invalid=true]:border-[#b42318] aria-[invalid=true]:bg-[#fff8f7]";

interface LocalIssue {
  field_id: string;
  message: string;
}

function text(value: JsonValue | undefined) {
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function boolValue(value: JsonValue | undefined) {
  return typeof value === "boolean" ? String(value) : "";
}

function Field({
  fieldId,
  label,
  required = false,
  hint,
  errors,
  children,
}: {
  fieldId: string;
  label: string;
  required?: boolean;
  hint?: string;
  errors: string[];
  children: ReactElement<{ "aria-describedby"?: string }>;
}) {
  const { state } = useProcedureWorkspace();
  const field = state.fields[fieldId];
  const describedBy = [hint ? `${fieldId}-hint` : null, errors.length ? `${fieldId}-error` : null]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <div className="space-y-2" data-field-id={fieldId}>
      <label className="block font-semibold text-[#334155]" htmlFor={fieldId}>
        {label}
        {required ? <span className="text-[#b42318]"> *</span> : null}
      </label>
      <div>{cloneElement(children, { "aria-describedby": describedBy })}</div>
      {hint ? <p className="text-sm text-[#667085]" id={`${fieldId}-hint`}>{hint}</p> : null}
      {errors.length ? (
        <ul className="space-y-1 text-sm font-medium text-[#b42318]" id={`${fieldId}-error`}>
          {errors.map((error) => <li key={error}>{error}</li>)}
        </ul>
      ) : null}
      {field ? (
        <p className="text-xs text-[#667085]" aria-live="polite">
          {field.sync_status === "saving" ? "Đang đồng bộ với trợ lý…" : null}
          {field.sync_status === "saved" ? "Đã đồng bộ với trợ lý" : null}
          {field.sync_status === "dirty" ? "Đã lưu trên form; chờ đồng bộ" : null}
          {field.sync_status === "error" ? field.error : null}
        </p>
      ) : null}
    </div>
  );
}

export function TemporaryResidenceForm({
  experience,
  selectedReceptionUnit,
  selectedServiceId,
}: {
  experience: ProcedureExperience;
  selectedReceptionUnit: string;
  selectedServiceId: string;
}) {
  const workspace = useProcedureWorkspace();
  const [submitted, setSubmitted] = useState(false);
  const values = useMemo(
    () => Object.fromEntries(Object.entries(workspace.state.fields).map(([id, field]) => [id, field.value])),
    [workspace.state.fields],
  );

  const localIssues = useMemo<LocalIssue[]>(() => {
    const issues: LocalIssue[] = [];
    const required = [
      ["registration_mode", "Chọn hình thức đăng ký."],
      ["applicant_full_name", "Nhập họ tên người đăng ký."],
      ["applicant_date_of_birth", "Chọn ngày sinh."],
      ["applicant_personal_id", "Nhập số định danh cá nhân giả lập gồm 12 chữ số."],
      ["applicant_is_minor", "Xác định người đăng ký có phải người chưa thành niên hay không."],
      ["temporary_address", "Nhập địa chỉ tạm trú."],
      ["temporary_start_date", "Chọn ngày bắt đầu tạm trú."],
      ["temporary_end_date", "Chọn ngày kết thúc dự kiến."],
      ["legal_dwelling_data_retrievable", "Xác định khả năng khai thác dữ liệu chỗ ở."],
      ["dwelling_basis", "Chọn căn cứ sử dụng chỗ ở."],
      ["submission_channel", "Chọn kênh nộp."],
    ] as const;
    for (const [fieldId, message] of required) {
      if (values[fieldId] === undefined || values[fieldId] === null || values[fieldId] === "") {
        issues.push({ field_id: fieldId, message });
      }
    }
    if (typeof values.applicant_personal_id === "string" && values.applicant_personal_id && !/^\d{12}$/.test(values.applicant_personal_id)) {
      issues.push({ field_id: "applicant_personal_id", message: "Số định danh phải gồm đúng 12 chữ số." });
    }
    if (
      typeof values.temporary_start_date === "string" &&
      typeof values.temporary_end_date === "string" &&
      values.temporary_start_date &&
      values.temporary_end_date &&
      values.temporary_end_date <= values.temporary_start_date
    ) {
      issues.push({ field_id: "temporary_end_date", message: "Ngày kết thúc phải sau ngày bắt đầu." });
    }
    if (values.applicant_is_minor === true && values.minor_consent_present !== true) {
      issues.push({ field_id: "minor_consent_present", message: "Cần có ý kiến đồng ý của cha, mẹ hoặc người giám hộ." });
    }
    if (values.legal_dwelling_data_retrievable === false && values.legal_dwelling_document_present !== true) {
      issues.push({ field_id: "legal_dwelling_document_present", message: "Cần giấy tờ chỗ ở khi cơ sở dữ liệu không khai thác được." });
    }
    return issues;
  }, [values]);

  const allIssues = useMemo(() => {
    const aiIssues = workspace.state.validation_issues
      .filter((issue) => issue.field_id)
      .map((issue) => ({ field_id: issue.field_id as string, message: issue.message }));
    return [...localIssues, ...aiIssues].filter(
      (issue, index, list) => list.findIndex((item) => item.field_id === issue.field_id && item.message === issue.message) === index,
    );
  }, [localIssues, workspace.state.validation_issues]);

  const errorsFor = (fieldId: string) => {
    const local = submitted
      ? localIssues.filter((issue) => issue.field_id === fieldId).map((issue) => issue.message)
      : [];
    const ai = workspace.state.validation_issues
      .filter((issue) => issue.field_id === fieldId)
      .map((issue) => issue.message);
    return [...new Set([...local, ...ai])];
  };
  const invalid = (fieldId: string) => errorsFor(fieldId).length > 0;
  const set = (fieldId: string, value: JsonValue) => {
    setSubmitted(false);
    workspace.setField(fieldId, value);
  };
  const commit = (fieldId: string) => void workspace.commitField(fieldId);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitted(true);
    if (allIssues.length) {
      window.requestAnimationFrame(() => document.getElementById(allIssues[0].field_id)?.focus());
      return;
    }
    markDeclarationSaved(experience, {
      receptionUnit: selectedReceptionUnit,
      serviceId: selectedServiceId,
    });
  };

  return (
    <main className="min-h-screen bg-[#f3f6f8] px-4 py-8 text-[#1e2f41] sm:px-6">
      <div className="mx-auto max-w-6xl">
        <header className="rounded-2xl bg-gradient-to-br from-[#7d302f] to-[#a84c3e] p-6 text-white shadow-lg sm:p-8">
          <p className="text-sm font-bold tracking-widest text-white/80 uppercase">Hero flow · Mã 1.004194</p>
          <h1 className="mt-2 text-2xl font-extrabold sm:text-4xl">Chuẩn bị đăng ký tạm trú</h1>
          <p className="mt-3 max-w-3xl leading-7 text-white/90">
            Biểu mẫu là nguồn dữ liệu chính. Chat chỉ đề xuất; bạn quyết định giá trị cuối cùng và có thể tiếp tục ngay cả khi AI lỗi.
          </p>
        </header>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <form className="space-y-7 rounded-2xl bg-white p-5 shadow-sm sm:p-8" noValidate onSubmit={handleSubmit}>
            <div className="flex items-start gap-3 rounded-xl border border-[#f2c4b4] bg-[#fff8f5] p-4 text-sm leading-6 text-[#704238]">
              <ShieldCheck className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <p>Chỉ dùng dữ liệu giả trong bản demo. Giá trị bạn sửa trực tiếp được đánh dấu đã xác nhận và AI không được tự ghi đè.</p>
            </div>

            {submitted && allIssues.length ? (
              <section className="rounded-xl border border-[#f1a7a2] bg-[#fff4f3] p-4" role="alert" aria-labelledby="form-errors-title">
                <h2 className="font-extrabold text-[#912018]" id="form-errors-title">Cần sửa {allIssues.length} thông tin</h2>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#912018]">
                  {allIssues.map((issue) => (
                    <li key={`${issue.field_id}:${issue.message}`}>
                      <a className="underline" href={`#${issue.field_id}`}>{issue.message}</a>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <fieldset className="space-y-5">
              <legend className="text-xl font-extrabold">1. Người đăng ký</legend>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field fieldId="registration_mode" label="Hình thức đăng ký" required errors={errorsFor("registration_mode")}>
                  <select aria-invalid={invalid("registration_mode")} className={inputClass} id="registration_mode" value={text(values.registration_mode)} onBlur={() => commit("registration_mode")} onChange={(e) => set("registration_mode", e.target.value)}>
                    <option value="">Chọn hình thức</option>
                    <option value="individual_or_household">Cá nhân hoặc hộ gia đình</option>
                    <option value="by_list">Theo danh sách — cần kiểm tra chính thức</option>
                    <option value="armed_forces">Đơn vị lực lượng vũ trang — cần kiểm tra chính thức</option>
                  </select>
                </Field>
                <Field fieldId="applicant_full_name" label="Họ tên người đăng ký" required errors={errorsFor("applicant_full_name")}>
                  <input aria-invalid={invalid("applicant_full_name")} autoComplete="off" className={inputClass} id="applicant_full_name" value={text(values.applicant_full_name)} onBlur={() => commit("applicant_full_name")} onChange={(e) => set("applicant_full_name", e.target.value)} />
                </Field>
                <Field fieldId="applicant_date_of_birth" label="Ngày sinh" required errors={errorsFor("applicant_date_of_birth")}>
                  <input aria-invalid={invalid("applicant_date_of_birth")} className={inputClass} id="applicant_date_of_birth" type="date" value={text(values.applicant_date_of_birth)} onBlur={() => commit("applicant_date_of_birth")} onChange={(e) => set("applicant_date_of_birth", e.target.value)} />
                </Field>
                <Field fieldId="applicant_personal_id" label="Số định danh cá nhân" required hint="Bản demo: chỉ nhập 12 chữ số giả." errors={errorsFor("applicant_personal_id")}>
                  <input aria-invalid={invalid("applicant_personal_id")} className={inputClass} id="applicant_personal_id" inputMode="numeric" maxLength={12} value={text(values.applicant_personal_id)} onBlur={() => commit("applicant_personal_id")} onChange={(e) => set("applicant_personal_id", e.target.value.replace(/\D/g, ""))} />
                </Field>
                <Field fieldId="applicant_is_minor" label="Người đăng ký chưa thành niên?" required errors={errorsFor("applicant_is_minor")}>
                  <select aria-invalid={invalid("applicant_is_minor")} className={inputClass} id="applicant_is_minor" value={boolValue(values.applicant_is_minor)} onBlur={() => commit("applicant_is_minor")} onChange={(e) => set("applicant_is_minor", e.target.value === "" ? null : e.target.value === "true")}>
                    <option value="">Chọn câu trả lời</option><option value="false">Không</option><option value="true">Có</option>
                  </select>
                </Field>
                {values.applicant_is_minor === true ? (
                  <Field fieldId="minor_consent_present" label="Đã có ý kiến đồng ý của cha/mẹ/người giám hộ?" required errors={errorsFor("minor_consent_present")}>
                    <select aria-invalid={invalid("minor_consent_present")} className={inputClass} id="minor_consent_present" value={boolValue(values.minor_consent_present)} onBlur={() => commit("minor_consent_present")} onChange={(e) => set("minor_consent_present", e.target.value === "" ? null : e.target.value === "true")}>
                      <option value="">Chọn câu trả lời</option><option value="false">Chưa có</option><option value="true">Đã có</option>
                    </select>
                  </Field>
                ) : null}
              </div>
            </fieldset>

            <fieldset className="space-y-5 border-t border-[#e2e8f0] pt-6">
              <legend className="text-xl font-extrabold">2. Nơi và thời gian tạm trú</legend>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Field fieldId="temporary_address" label="Địa chỉ tạm trú" required errors={errorsFor("temporary_address")}>
                    <textarea aria-invalid={invalid("temporary_address")} className={`${inputClass} min-h-24 resize-y`} id="temporary_address" value={text(values.temporary_address)} onBlur={() => commit("temporary_address")} onChange={(e) => set("temporary_address", e.target.value)} />
                  </Field>
                </div>
                <Field fieldId="temporary_start_date" label="Ngày bắt đầu" required errors={errorsFor("temporary_start_date")}>
                  <input aria-invalid={invalid("temporary_start_date")} className={inputClass} id="temporary_start_date" type="date" value={text(values.temporary_start_date)} onBlur={() => commit("temporary_start_date")} onChange={(e) => set("temporary_start_date", e.target.value)} />
                </Field>
                <Field fieldId="temporary_end_date" label="Ngày kết thúc dự kiến" required errors={errorsFor("temporary_end_date")}>
                  <input aria-invalid={invalid("temporary_end_date")} className={inputClass} id="temporary_end_date" type="date" value={text(values.temporary_end_date)} onBlur={() => commit("temporary_end_date")} onChange={(e) => set("temporary_end_date", e.target.value)} />
                </Field>
              </div>
            </fieldset>

            <fieldset className="space-y-5 border-t border-[#e2e8f0] pt-6">
              <legend className="text-xl font-extrabold">3. Chỗ ở và kênh nộp</legend>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field fieldId="dwelling_basis" label="Căn cứ sử dụng chỗ ở" required errors={errorsFor("dwelling_basis")}>
                  <select aria-invalid={invalid("dwelling_basis")} className={inputClass} id="dwelling_basis" value={text(values.dwelling_basis)} onBlur={() => commit("dwelling_basis")} onChange={(e) => set("dwelling_basis", e.target.value)}>
                    <option value="">Chọn căn cứ</option><option value="owned">Sở hữu</option><option value="rented">Thuê</option><option value="borrowed">Mượn</option><option value="accommodated">Ở nhờ</option><option value="join_family_household">Về với hộ gia đình</option><option value="other">Khác</option>
                  </select>
                </Field>
                <Field fieldId="owner_or_householder_consent" label="Đã có sự đồng ý của chủ hộ/chủ sở hữu khi cần?" errors={errorsFor("owner_or_householder_consent")}>
                  <select aria-invalid={invalid("owner_or_householder_consent")} className={inputClass} id="owner_or_householder_consent" value={boolValue(values.owner_or_householder_consent)} onBlur={() => commit("owner_or_householder_consent")} onChange={(e) => set("owner_or_householder_consent", e.target.value === "" ? null : e.target.value === "true")}>
                    <option value="">Chưa xác định</option><option value="false">Chưa có</option><option value="true">Đã có</option>
                  </select>
                </Field>
                <Field fieldId="legal_dwelling_data_retrievable" label="Thông tin chỗ ở có thể khai thác từ CSDL?" required errors={errorsFor("legal_dwelling_data_retrievable")}>
                  <select aria-invalid={invalid("legal_dwelling_data_retrievable")} className={inputClass} id="legal_dwelling_data_retrievable" value={boolValue(values.legal_dwelling_data_retrievable)} onBlur={() => commit("legal_dwelling_data_retrievable")} onChange={(e) => set("legal_dwelling_data_retrievable", e.target.value === "" ? null : e.target.value === "true")}>
                    <option value="">Chọn câu trả lời</option><option value="true">Có</option><option value="false">Không</option>
                  </select>
                </Field>
                {values.legal_dwelling_data_retrievable === false ? (
                  <Field fieldId="legal_dwelling_document_present" label="Đã có giấy tờ chứng minh chỗ ở hợp pháp?" required errors={errorsFor("legal_dwelling_document_present")}>
                    <select aria-invalid={invalid("legal_dwelling_document_present")} className={inputClass} id="legal_dwelling_document_present" value={boolValue(values.legal_dwelling_document_present)} onBlur={() => commit("legal_dwelling_document_present")} onChange={(e) => set("legal_dwelling_document_present", e.target.value === "" ? null : e.target.value === "true")}>
                      <option value="">Chọn câu trả lời</option><option value="false">Chưa có</option><option value="true">Đã có</option>
                    </select>
                  </Field>
                ) : null}
                <Field fieldId="submission_channel" label="Kênh nộp" required errors={errorsFor("submission_channel")}>
                  <select aria-invalid={invalid("submission_channel")} className={inputClass} id="submission_channel" value={text(values.submission_channel)} onBlur={() => commit("submission_channel")} onChange={(e) => set("submission_channel", e.target.value)}>
                    <option value="">Chọn kênh nộp</option><option value="online">Trực tuyến</option><option value="direct">Trực tiếp</option>
                  </select>
                </Field>
                <Field fieldId="fee_exemption_claimed" label="Đề nghị miễn lệ phí?" errors={errorsFor("fee_exemption_claimed")}>
                  <select aria-invalid={invalid("fee_exemption_claimed")} className={inputClass} id="fee_exemption_claimed" value={boolValue(values.fee_exemption_claimed)} onBlur={() => commit("fee_exemption_claimed")} onChange={(e) => set("fee_exemption_claimed", e.target.value === "" ? null : e.target.value === "true")}>
                    <option value="">Không đề nghị</option><option value="true">Có</option><option value="false">Không</option>
                  </select>
                </Field>
              </div>
            </fieldset>

            <button className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#903938] px-6 font-bold text-white hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] sm:w-auto" type="submit">
              <Save className="size-5" aria-hidden="true" /> Kiểm tra và lưu bản nháp
            </button>
            {submitted && !allIssues.length ? (
              <div className="flex items-start gap-2 rounded-xl border border-[#98d0aa] bg-[#effaf2] p-4 text-[#25633f]" role="status">
                <CheckCircle2 className="mt-0.5 size-5" aria-hidden="true" /> Bản nháp đã đủ thông tin kiểm tra tại UI.
              </div>
            ) : null}
          </form>

          <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
            <div className="rounded-2xl border border-[#d7e0e8] bg-white p-5 shadow-sm">
              <h2 className="font-extrabold">Trạng thái biểu mẫu</h2>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between gap-3"><dt>Revision</dt><dd className="font-bold">{workspace.state.revision}</dd></div>
                <div className="flex justify-between gap-3"><dt>Đã xác nhận</dt><dd className="font-bold">{Object.values(workspace.state.fields).filter((field) => field.confirmed).length}</dd></div>
                <div className="flex justify-between gap-3"><dt>Đã sửa tay</dt><dd className="font-bold">{Object.values(workspace.state.fields).filter((field) => field.dirty).length}</dd></div>
              </dl>
            </div>
            <div className="rounded-2xl border border-[#f0c36a] bg-[#fff9e8] p-5 text-sm leading-6 text-[#704d09]">
              <CloudOff className="mb-2 size-5" aria-hidden="true" />
              <p className="font-bold">AI là tùy chọn</p>
              <p>Form vẫn nhập, kiểm tra và lưu bản nháp khi trợ lý mất kết nối.</p>
            </div>
            {workspace.state.recovery_notice ? (
              <div className="flex items-start gap-2 rounded-2xl border border-[#b9cde5] bg-[#f2f7fc] p-4 text-sm text-[#24496f]" role="status">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                {workspace.state.recovery_notice}
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </main>
  );
}
