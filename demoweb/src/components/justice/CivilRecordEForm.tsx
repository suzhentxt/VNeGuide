"use client";

import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  FilePenLine,
  Info,
  Save,
  ShieldCheck,
} from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";

import type { ProcedureExperience } from "@/data/procedure-experiences";
import {
  markDeclarationSaved,
  withProcedureSelection,
} from "@/lib/procedure-selection";

type ResidenceScope = "domestic" | "other";
type Relationship = "self" | "other";
type CopyRequest = "no" | "yes";
type ReceiptMethod = "direct" | "online" | "post";

const inputClassName =
  "h-11 w-full rounded-md border border-[#DCE3EA] bg-white px-3 text-[15px] text-[#212B36] outline-none transition placeholder:text-[#A0AAB4] focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20 disabled:cursor-not-allowed disabled:bg-[#F4F6F8]";

const textareaClassName =
  "min-h-24 w-full resize-y rounded-md border border-[#DCE3EA] bg-white px-3 py-3 text-[15px] text-[#212B36] outline-none transition placeholder:text-[#A0AAB4] focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20";

const focusClassName =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#CE7A58] focus-visible:ring-offset-2";

function Field({
  children,
  className = "",
  label,
  required = false,
}: {
  children: ReactNode;
  className?: string;
  label: string;
  required?: boolean;
}) {
  return (
    <fieldset className={`min-w-0 space-y-2 ${className}`}>
      <legend className="mb-2 text-sm font-semibold text-[#637381]">
        {label}
        {required ? <span className="text-red-500"> *</span> : null}
      </legend>
      {children}
    </fieldset>
  );
}

function SectionCard({
  children,
  description,
  number,
  title,
}: {
  children: ReactNode;
  description?: string;
  number: string;
  title: string;
}) {
  return (
    <fieldset className="min-w-0 rounded-lg border border-[#E1E7EC] bg-white p-4 shadow-[0_8px_20px_rgba(33,43,54,0.04)] sm:p-6">
      <legend className="max-w-full px-2">
        <span className="inline-flex max-w-full items-start gap-3 text-base font-bold text-[#212B36] sm:text-lg">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#CE7A58] text-sm text-white">
            {number}
          </span>
          <span className="pt-1">{title}</span>
        </span>
      </legend>
      {description ? (
        <p className="mt-2 text-sm leading-6 text-[#637381]">{description}</p>
      ) : null}
      <div className="mt-6">{children}</div>
    </fieldset>
  );
}

function RadioChoice({
  checked,
  label,
  name,
  onChange,
  value,
}: {
  checked: boolean;
  label: string;
  name: string;
  onChange: () => void;
  value: string;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-sm text-[#52606D] hover:border-[#E6C8BC] hover:bg-[#FFF8F5]">
      <input
        checked={checked}
        className="size-4 accent-[#CE7A58]"
        name={name}
        onChange={onChange}
        type="radio"
        value={value}
      />
      {label}
    </label>
  );
}

export function CivilRecordEForm({
  experience,
  selectedReceptionUnit,
  selectedServiceId,
}: {
  experience: ProcedureExperience;
  selectedReceptionUnit: string;
  selectedServiceId: string;
}) {
  const [applicantResidence, setApplicantResidence] =
    useState<ResidenceScope>("domestic");
  const [subjectResidence, setSubjectResidence] =
    useState<ResidenceScope>("domestic");
  const [relationship, setRelationship] = useState<Relationship>("self");
  const [copyRequest, setCopyRequest] = useState<CopyRequest>("no");
  const [receiptMethod, setReceiptMethod] =
    useState<ReceiptMethod>("direct");
  const [saved, setSaved] = useState(false);

  const selection = {
    receptionUnit: selectedReceptionUnit,
    serviceId: selectedServiceId,
  } as const;
  const selectedService = experience.services.find(
    (service) => service.id === selectedServiceId,
  );
  const backHref = withProcedureSelection(
    experience.routes.submission,
    selection,
    { step: "3" },
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    markDeclarationSaved(experience, selection);
    setSaved(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("civil-record-e-form-status")
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  return (
    <section className="min-h-[calc(100vh-120px)] bg-[#F2F5F8] px-3 py-6 text-[#212B36] sm:px-6 sm:py-10">
      <div className="mx-auto w-full max-w-[1350px]">
        <header className="rounded-lg bg-white px-4 py-5 shadow-sm sm:px-7 sm:py-6">
          <div className="flex items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#CE7A58]/10 text-[#CE7A58]">
              <FilePenLine aria-hidden="true" className="size-5" />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-bold tracking-[0.12em] text-[#CE7A58] uppercase">
                Mẫu hộ tịch điện tử tương tác
              </p>
              <h1 className="mt-1 text-xl leading-tight font-bold sm:text-2xl">
                {experience.title}
              </h1>
              <p className="mt-2 text-sm text-[#637381]">
                Mã thủ tục:{" "}
                <strong className="text-[#212B36]">{experience.code}</strong>
              </p>
            </div>
          </div>
        </header>

        <form
          aria-describedby="civil-record-e-form-notice"
          className="mt-6 space-y-6"
          onChange={() => setSaved(false)}
          onSubmit={handleSubmit}
        >
          <div
            className="flex items-start gap-3 rounded-lg border border-[#F1D3C7] bg-[#FFF8F5] p-4 text-sm leading-6 text-[#5A4A43]"
            id="civil-record-e-form-notice"
          >
            <Info
              aria-hidden="true"
              className="mt-0.5 size-5 shrink-0 text-[#CE7A58]"
            />
            <p>
              Đây là biểu mẫu mô phỏng. Thông tin định danh bên dưới đã được ẩn
              danh; dữ liệu kê khai không được gửi hoặc lưu trên máy chủ.
            </p>
          </div>

          <section className="grid gap-4 rounded-lg border border-[#E1E7EC] bg-white p-4 text-sm shadow-[0_8px_20px_rgba(33,43,54,0.04)] sm:grid-cols-2 sm:p-5">
            <div>
              <p className="text-[#637381]">Cơ quan thực hiện</p>
              <p className="mt-1 font-bold text-[#212B36]">
                {selectedService?.authority}
              </p>
            </div>
            <div>
              <p className="text-[#637381]">Đơn vị tiếp nhận</p>
              <p className="mt-1 font-bold text-[#212B36]">
                {selectedReceptionUnit}
              </p>
            </div>
          </section>

          <SectionCard
            description="Thông tin người đang thực hiện thủ tục."
            number="I"
            title="Thông tin về người yêu cầu đăng ký"
          >
            <div className="mb-6 flex items-start gap-3 rounded-lg border border-[#DCE8DF] bg-[#F6FBF7] p-4 text-sm text-[#35633E]">
              <ShieldCheck
                aria-hidden="true"
                className="mt-0.5 size-5 shrink-0"
              />
              <p>
                Bản demo không điền sẵn hoặc gửi dữ liệu cá nhân tới máy chủ.
                Thông tin nhập tại đây chỉ tồn tại trong biểu mẫu hiện tại.
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              <Field className="lg:col-span-2" label="Họ, chữ đệm, tên" required>
                <input
                  autoComplete="name"
                  className={inputClassName}
                  name="applicant-name"
                  placeholder="Nhập họ và tên"
                  required
                />
              </Field>
              <Field label="Số định danh cá nhân">
                <input
                  className={inputClassName}
                  inputMode="numeric"
                  maxLength={12}
                  name="applicant-personal-id"
                  placeholder="Nhập số định danh cá nhân"
                />
              </Field>
              <Field label="Giấy tờ tùy thân">
                <select
                  className={inputClassName}
                  defaultValue=""
                  name="applicant-document-type"
                >
                  <option disabled value="">
                    -- Chọn --
                  </option>
                  <option value="citizen-card">Thẻ căn cước công dân</option>
                  <option value="identity-card">Thẻ căn cước</option>
                  <option value="passport">Hộ chiếu</option>
                  <option value="other">Giấy tờ khác</option>
                </select>
              </Field>
              <Field label="Số giấy tờ">
                <input
                  className={inputClassName}
                  name="applicant-document-number"
                  placeholder="Nhập số giấy tờ"
                />
              </Field>
              <Field label="Ngày cấp">
                <input
                  className={inputClassName}
                  name="applicant-document-issued-date"
                  type="date"
                />
              </Field>
              <Field className="sm:col-span-2 lg:col-span-3" label="Cơ quan cấp">
                <input
                  className={inputClassName}
                  name="applicant-document-issuer"
                  placeholder="Nhập cơ quan cấp"
                />
              </Field>
              <Field label="Loại cư trú" required>
                <select
                  className={inputClassName}
                  defaultValue=""
                  name="applicant-residence-type"
                  required
                >
                  <option disabled value="">
                    -- Chọn --
                  </option>
                  <option value="permanent">Thường trú</option>
                  <option value="temporary">Tạm trú</option>
                  <option value="other">Khác</option>
                </select>
              </Field>
              <Field className="sm:col-span-2" label="Nơi cư trú" required>
                <fieldset>
                  <legend className="sr-only">Phạm vi nơi cư trú của người yêu cầu</legend>
                  <div className="mb-2 flex flex-wrap gap-2">
                    <RadioChoice
                      checked={applicantResidence === "domestic"}
                      label="Trong nước"
                      name="applicant-residence-scope"
                      onChange={() => setApplicantResidence("domestic")}
                      value="domestic"
                    />
                    <RadioChoice
                      checked={applicantResidence === "other"}
                      label="Khác"
                      name="applicant-residence-scope"
                      onChange={() => setApplicantResidence("other")}
                      value="other"
                    />
                  </div>
                  <input
                    className={inputClassName}
                    key={applicantResidence}
                    name="applicant-residence"
                    placeholder={
                      applicantResidence === "domestic"
                        ? "Nhập địa chỉ cư trú trong nước"
                        : "Nhập địa chỉ cư trú khác"
                    }
                    required
                  />
                </fieldset>
              </Field>
              <Field
                className="sm:col-span-2 lg:col-span-3"
                label="Quan hệ với người có nội dung thay đổi"
                required
              >
                <fieldset>
                  <legend className="sr-only">
                    Quan hệ với người có nội dung thay đổi
                  </legend>
                  <div className="flex flex-wrap gap-2">
                    <RadioChoice
                      checked={relationship === "self"}
                      label="Bản thân"
                      name="applicant-relationship"
                      onChange={() => setRelationship("self")}
                      value="self"
                    />
                    <RadioChoice
                      checked={relationship === "other"}
                      label="Khác"
                      name="applicant-relationship"
                      onChange={() => setRelationship("other")}
                      value="other"
                    />
                  </div>
                  {relationship === "other" ? (
                    <input
                      className={`${inputClassName} mt-2`}
                      name="relationship-detail"
                      placeholder="Nhập mối quan hệ"
                      required
                    />
                  ) : null}
                </fieldset>
              </Field>
            </div>
          </SectionCard>

          <SectionCard
            number="II"
            title="Thông tin về người có nội dung thay đổi"
          >
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              <Field className="lg:col-span-2" label="Họ, chữ đệm, tên" required>
                <input
                  autoComplete="off"
                  className={inputClassName}
                  name="subject-full-name"
                  placeholder="Nhập họ và tên theo giấy tờ hộ tịch"
                  required
                />
              </Field>
              <Field label="Ngày, tháng, năm sinh" required>
                <input
                  className={inputClassName}
                  name="subject-date-of-birth"
                  required
                  type="date"
                />
              </Field>
              <Field label="Giới tính" required>
                <select className={inputClassName} defaultValue="" name="subject-gender" required>
                  <option disabled value="">-- Chọn --</option>
                  <option value="female">Nữ</option>
                  <option value="male">Nam</option>
                  <option value="other">Khác</option>
                </select>
              </Field>
              <Field label="Dân tộc">
                <input
                  className={inputClassName}
                  name="subject-ethnicity"
                  placeholder="Nhập dân tộc"
                />
              </Field>
              <Field label="Quốc tịch" required>
                <select
                  className={inputClassName}
                  defaultValue="vietnam"
                  name="subject-nationality"
                  required
                >
                  <option value="vietnam">Việt Nam</option>
                  <option value="other">Quốc tịch khác</option>
                </select>
              </Field>
              <Field label="Số định danh cá nhân">
                <input
                  className={inputClassName}
                  inputMode="numeric"
                  maxLength={12}
                  name="subject-personal-id"
                  placeholder="Nhập số định danh"
                />
              </Field>
              <Field label="Giấy tờ tùy thân">
                <select className={inputClassName} defaultValue="citizen-card" name="subject-document-type">
                  <option value="citizen-card">Thẻ căn cước công dân</option>
                  <option value="identity-card">Thẻ căn cước</option>
                  <option value="passport">Hộ chiếu</option>
                  <option value="other">Giấy tờ khác</option>
                </select>
              </Field>
              <Field label="Số giấy tờ">
                <input
                  className={inputClassName}
                  name="subject-document-number"
                  placeholder="Nhập số giấy tờ"
                />
              </Field>
              <Field label="Ngày cấp">
                <input className={inputClassName} name="subject-document-date" type="date" />
              </Field>
              <Field className="sm:col-span-2 lg:col-span-3" label="Cơ quan cấp">
                <input
                  className={inputClassName}
                  name="subject-document-issuer"
                  placeholder="Nhập cơ quan cấp"
                />
              </Field>
              <Field label="Loại cư trú" required>
                <select className={inputClassName} defaultValue="permanent" name="subject-residence-type" required>
                  <option value="permanent">Thường trú</option>
                  <option value="temporary">Tạm trú</option>
                  <option value="other">Khác</option>
                </select>
              </Field>
              <Field className="sm:col-span-2" label="Nơi cư trú" required>
                <fieldset>
                  <legend className="sr-only">Phạm vi nơi cư trú của người có nội dung thay đổi</legend>
                  <div className="mb-2 flex flex-wrap gap-2">
                    <RadioChoice
                      checked={subjectResidence === "domestic"}
                      label="Trong nước"
                      name="subject-residence-scope"
                      onChange={() => setSubjectResidence("domestic")}
                      value="domestic"
                    />
                    <RadioChoice
                      checked={subjectResidence === "other"}
                      label="Khác"
                      name="subject-residence-scope"
                      onChange={() => setSubjectResidence("other")}
                      value="other"
                    />
                  </div>
                  <input
                    className={inputClassName}
                    key={subjectResidence}
                    name="subject-residence"
                    placeholder={
                      subjectResidence === "domestic"
                        ? "Nhập địa chỉ cư trú trong nước"
                        : "Nhập địa chỉ cư trú khác"
                    }
                    required
                  />
                </fieldset>
              </Field>
            </div>
          </SectionCard>

          <SectionCard
            number="III"
            title="Thông tin về nội dung đề nghị đăng ký"
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Việc đăng ký" required>
                <select className={inputClassName} defaultValue="" name="registration-kind" required>
                  <option disabled value="">-- Chọn --</option>
                  <option value="change">Thay đổi thông tin hộ tịch</option>
                  <option value="correction">Cải chính hộ tịch</option>
                  <option value="addition">Bổ sung thông tin hộ tịch</option>
                  <option value="ethnicity">Xác định lại dân tộc</option>
                </select>
              </Field>
              <Field label="Nghiệp vụ đăng ký" required>
                <select className={inputClassName} defaultValue="" name="registration-operation" required>
                  <option disabled value="">-- Chọn --</option>
                  <option value="birth">Khai sinh</option>
                  <option value="marriage">Kết hôn</option>
                  <option value="death">Khai tử</option>
                  <option value="other">Hộ tịch khác</option>
                </select>
              </Field>
            </div>

            <section
              aria-labelledby="registered-civil-document-title"
              className="mt-6 rounded-lg border border-[#E4E9EE] bg-[#F8FAFC] p-4 sm:p-5"
            >
              <h2 id="registered-civil-document-title" className="font-bold">
                Giấy tờ hộ tịch đã đăng ký
              </h2>
              <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <Field className="lg:col-span-2" label="Tên loại giấy tờ hộ tịch" required>
                  <input
                    className={inputClassName}
                    name="civil-document-type"
                    placeholder="Ví dụ: Giấy khai sinh"
                    required
                  />
                </Field>
                <Field label="Số">
                  <input className={inputClassName} name="civil-document-number" />
                </Field>
                <Field label="Quyển số">
                  <input className={inputClassName} name="civil-document-book" />
                </Field>
                <Field label="Ngày, tháng, năm đăng ký" required>
                  <input className={inputClassName} name="original-registration-date" required type="date" />
                </Field>
                <Field className="sm:col-span-2 lg:col-span-3" label="Nơi đăng ký hồ sơ gốc" required>
                  <input
                    className={inputClassName}
                    name="original-registration-place"
                    placeholder="Nhập cơ quan và địa phương đăng ký"
                    required
                  />
                </Field>
              </div>
            </section>

            <div className="mt-6 grid gap-5">
              <Field label="Nội dung đề nghị thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc" required>
                <textarea
                  className={textareaClassName}
                  name="requested-change"
                  placeholder="Mô tả rõ nội dung hiện tại và nội dung đề nghị điều chỉnh"
                  required
                />
              </Field>
              <Field label="Lý do đề nghị" required>
                <textarea
                  className={textareaClassName}
                  name="request-reason"
                  placeholder="Nhập lý do và căn cứ của đề nghị"
                  required
                />
              </Field>
            </div>

            <div className="mt-6 grid gap-5 lg:grid-cols-2">
              <Field label="Đề nghị cấp bản sao" required>
                <fieldset>
                  <legend className="sr-only">Có đề nghị cấp bản sao hay không</legend>
                  <div className="flex flex-wrap gap-2">
                    <RadioChoice
                      checked={copyRequest === "no"}
                      label="Không"
                      name="copy-request"
                      onChange={() => setCopyRequest("no")}
                      value="no"
                    />
                    <RadioChoice
                      checked={copyRequest === "yes"}
                      label="Có"
                      name="copy-request"
                      onChange={() => setCopyRequest("yes")}
                      value="yes"
                    />
                  </div>
                  {copyRequest === "yes" ? (
                    <input
                      aria-label="Số lượng bản sao"
                      className={`${inputClassName} mt-2`}
                      inputMode="numeric"
                      max={20}
                      min={1}
                      name="copy-quantity"
                      placeholder="Nhập số lượng bản sao"
                      required
                      type="number"
                    />
                  ) : null}
                </fieldset>
              </Field>

              <Field label="Phương thức nhận kết quả" required>
                <fieldset>
                  <legend className="sr-only">Chọn phương thức nhận kết quả</legend>
                  <div className="flex flex-wrap gap-2">
                    <RadioChoice
                      checked={receiptMethod === "direct"}
                      label="Trực tiếp"
                      name="receipt-method"
                      onChange={() => setReceiptMethod("direct")}
                      value="direct"
                    />
                    <RadioChoice
                      checked={receiptMethod === "online"}
                      label="Trực tuyến"
                      name="receipt-method"
                      onChange={() => setReceiptMethod("online")}
                      value="online"
                    />
                    <RadioChoice
                      checked={receiptMethod === "post"}
                      label="Bưu chính"
                      name="receipt-method"
                      onChange={() => setReceiptMethod("post")}
                      value="post"
                    />
                  </div>
                  {receiptMethod === "post" ? (
                    <textarea
                      aria-label="Địa chỉ nhận kết quả qua bưu chính"
                      className={`${textareaClassName} mt-2`}
                      name="postal-address"
                      placeholder="Nhập địa chỉ nhận kết quả"
                      required
                    />
                  ) : null}
                  {receiptMethod === "online" ? (
                    <p className="mt-2 rounded-md bg-[#F4F6F8] px-3 py-2 text-sm leading-5 text-[#637381]">
                      Kết quả điện tử được trả trên tài khoản dịch vụ công mô phỏng.
                    </p>
                  ) : null}
                </fieldset>
              </Field>
            </div>

            <div className="mt-6 rounded-lg border border-[#E4E9EE] bg-[#F8FAFC] p-4 text-sm leading-6 text-[#52606D]">
              <p className="font-bold text-[#212B36]">Hồ sơ đính kèm theo quy định</p>
              <p className="mt-1">
                Tài liệu chứng minh và văn bản ủy quyền (nếu có) được chọn tại
                bước Thành phần hồ sơ sau khi lưu tờ khai.
              </p>
            </div>

            <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-lg border border-[#F1D3C7] bg-[#FFF8F5] p-4 text-sm leading-6 text-[#5A4A43]">
              <input
                className="mt-1 size-4 shrink-0 accent-[#CE7A58]"
                name="declaration"
                required
                type="checkbox"
              />
              <span>
                Tôi cam đoan các thông tin cung cấp là đúng sự thật và chịu hoàn
                toàn trách nhiệm trước pháp luật về nội dung cam đoan của mình.
              </span>
            </label>
          </SectionCard>

          {saved ? (
            <div
              className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800"
              id="civil-record-e-form-status"
              role="status"
              tabIndex={-1}
            >
              <CheckCircle2
                aria-hidden="true"
                className="mt-0.5 size-5 shrink-0"
              />
              <div>
                <p className="font-bold">Đã lưu tờ khai trong phiên mô phỏng</p>
                <p className="mt-1 text-sm leading-5">
                  Không có thông tin nào được gửi tới cơ quan nhà nước. Bạn có
                  thể trở về bước Thành phần hồ sơ để tiếp tục luồng mô phỏng.
                </p>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col-reverse justify-end gap-3 rounded-lg bg-white px-4 py-5 shadow-sm sm:flex-row sm:px-6">
            <Link
              className={`${focusClassName} inline-flex h-11 items-center justify-center gap-2 rounded-md border border-[#DCE3EA] bg-white px-5 text-sm font-bold text-[#52606D] transition hover:bg-[#F7F9FA]`}
              href={backHref}
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
              Quay lại
            </Link>
            {saved ? (
              <Link
                className={`${focusClassName} inline-flex h-11 items-center justify-center rounded-lg bg-[#CE7A58] px-5 text-sm font-bold text-white transition hover:bg-[#BC5D37]`}
                href={backHref}
              >
                Trở về thành phần hồ sơ
              </Link>
            ) : (
              <button
                className={`${focusClassName} inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[#CE7A58] px-5 text-sm font-bold text-white transition hover:bg-[#BC5D37]`}
                type="submit"
              >
                <Save aria-hidden="true" className="size-4" />
                Lưu tờ khai
              </button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
