"use client";

import {
  ArrowLeft,
  CheckCircle2,
  FilePenLine,
  Info,
  Save,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import {
  standardMarriageExperience,
  type ProcedureExperience,
} from "@/data/procedure-experiences";
import {
  markDeclarationSaved,
  withProcedureSelection,
} from "@/lib/procedure-selection";

type PartnerSide = "female" | "male";

interface PartnerDetails {
  dateOfBirth: string;
  documentNumber: string;
  documentType: string;
  ethnicity: string;
  fullName: string;
  issueDate: string;
  issuer: string;
  maritalStatus: string;
  marriageCount: string;
  nationality: string;
  personalId: string;
  residence: string;
  residenceScope: string;
  residenceType: string;
}

const createEmptyPartner = (): PartnerDetails => ({
  fullName: "",
  dateOfBirth: "",
  ethnicity: "",
  nationality: "Việt Nam",
  documentType: "Căn cước công dân",
  documentNumber: "",
  issueDate: "",
  issuer: "",
  personalId: "",
  residence: "",
  residenceScope: "Trong nước",
  residenceType: "Thường trú",
  maritalStatus: "Chưa từng kết hôn",
  marriageCount: "1",
});

const inputClassName =
  "h-11 w-full rounded-md border border-[#DCE3EA] bg-white px-3 text-[15px] text-[#212B36] outline-none transition placeholder:text-[#A0AAB4] focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20";

const focusClassName =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#CE7A58] focus-visible:ring-offset-2";

function EFormField({
  children,
  label,
  required = false,
}: {
  children: React.ReactNode;
  label: string;
  required?: boolean;
}) {
  return (
    <label className="block space-y-2">
      <span className="block text-sm font-semibold text-[#637381]">
        {label}
        {required ? <span className="text-red-500"> *</span> : null}
      </span>
      {children}
    </label>
  );
}

function PartnerPanel({
  accentClassName,
  details,
  label,
  onChange,
  showPhoto = false,
  side,
}: {
  accentClassName: string;
  details: PartnerDetails;
  label: string;
  onChange: (field: keyof PartnerDetails, value: string) => void;
  showPhoto?: boolean;
  side: PartnerSide;
}) {
  return (
    <fieldset className="min-w-0 rounded-lg border border-[#E1E7EC] bg-white p-4 shadow-[0_8px_20px_rgba(33,43,54,0.05)] sm:p-6">
      <legend className="px-2">
        <span
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-bold ${accentClassName}`}
        >
          <UserRound aria-hidden="true" className="size-4" />
          {label}
        </span>
      </legend>

      <div className="mt-2 grid gap-5 sm:grid-cols-2">
        {showPhoto ? (
          <div className="sm:col-span-2">
            <EFormField label="Ảnh (trường hợp đăng ký kết hôn có yếu tố nước ngoài)">
              <input
                accept="image/png,image/jpeg,image/webp"
                className={`${inputClassName} cursor-pointer py-2`}
                type="file"
              />
            </EFormField>
          </div>
        ) : null}
        <div className="sm:col-span-2">
          <EFormField label="Họ, chữ đệm, tên" required>
            <input
              autoComplete="off"
              className={inputClassName}
              id={`${side}-full-name`}
              onChange={(event) => onChange("fullName", event.target.value)}
              placeholder="Nhập họ và tên theo giấy tờ tùy thân"
              required
              value={details.fullName}
            />
          </EFormField>
        </div>

        <EFormField label="Ngày, tháng, năm sinh" required>
          <input
            className={inputClassName}
            id={`${side}-date-of-birth`}
            onChange={(event) => onChange("dateOfBirth", event.target.value)}
            required
            type="date"
            value={details.dateOfBirth}
          />
        </EFormField>

        <EFormField label="Dân tộc">
          <input
            className={inputClassName}
            id={`${side}-ethnicity`}
            onChange={(event) => onChange("ethnicity", event.target.value)}
            placeholder="Nhập dân tộc"
            value={details.ethnicity}
          />
        </EFormField>

        <EFormField label="Quốc tịch" required>
          <select
            className={inputClassName}
            id={`${side}-nationality`}
            onChange={(event) => onChange("nationality", event.target.value)}
            required
            value={details.nationality}
          >
            <option value="Việt Nam">Việt Nam</option>
            <option value="Khác">Quốc tịch khác</option>
          </select>
        </EFormField>

        <EFormField label="Loại giấy tờ" required>
          <select
            className={inputClassName}
            id={`${side}-document-type`}
            onChange={(event) => onChange("documentType", event.target.value)}
            required
            value={details.documentType}
          >
            <option value="Căn cước công dân">Căn cước công dân</option>
            <option value="Căn cước điện tử">Căn cước điện tử</option>
            <option value="Hộ chiếu">Hộ chiếu</option>
            <option value="Giấy tờ khác">Giấy tờ khác</option>
          </select>
        </EFormField>

        <EFormField label="Số định danh cá nhân">
          <input
            className={inputClassName}
            id={`${side}-personal-id`}
            inputMode="numeric"
            onChange={(event) => onChange("personalId", event.target.value)}
            placeholder="Nhập số định danh cá nhân"
            value={details.personalId}
          />
        </EFormField>

        <EFormField label="Số giấy tờ" required>
          <input
            className={inputClassName}
            id={`${side}-document-number`}
            onChange={(event) => onChange("documentNumber", event.target.value)}
            placeholder="Nhập số giấy tờ"
            required
            value={details.documentNumber}
          />
        </EFormField>

        <EFormField label="Ngày cấp">
          <input
            className={inputClassName}
            id={`${side}-issue-date`}
            onChange={(event) => onChange("issueDate", event.target.value)}
            type="date"
            value={details.issueDate}
          />
        </EFormField>

        <EFormField label="Cơ quan cấp">
          <input
            className={inputClassName}
            id={`${side}-issuer`}
            onChange={(event) => onChange("issuer", event.target.value)}
            placeholder="Nhập cơ quan cấp"
            value={details.issuer}
          />
        </EFormField>

        <EFormField label="Tình trạng hôn nhân" required>
          <select
            className={inputClassName}
            id={`${side}-marital-status`}
            onChange={(event) => onChange("maritalStatus", event.target.value)}
            required
            value={details.maritalStatus}
          >
            <option value="Chưa từng kết hôn">Chưa từng kết hôn</option>
            <option value="Đã ly hôn">Đã ly hôn</option>
            <option value="Vợ hoặc chồng đã chết">Vợ hoặc chồng đã chết</option>
            <option value="Khác">Khác</option>
          </select>
        </EFormField>

        <EFormField label="Kết hôn lần thứ" required>
          <input
            className={inputClassName}
            id={`${side}-marriage-count`}
            inputMode="numeric"
            max="99"
            min="1"
            onChange={(event) => onChange("marriageCount", event.target.value)}
            required
            type="number"
            value={details.marriageCount}
          />
        </EFormField>

        <EFormField label="Loại cư trú" required>
          <select
            className={inputClassName}
            id={`${side}-residence-type`}
            onChange={(event) => onChange("residenceType", event.target.value)}
            required
            value={details.residenceType}
          >
            <option value="Thường trú">Thường trú</option>
            <option value="Tạm trú">Tạm trú</option>
            <option value="Nơi đang sinh sống">Nơi đang sinh sống</option>
          </select>
        </EFormField>

        <EFormField label="Phạm vi cư trú" required>
          <select
            className={inputClassName}
            id={`${side}-residence-scope`}
            onChange={(event) => onChange("residenceScope", event.target.value)}
            required
            value={details.residenceScope}
          >
            <option value="Trong nước">Trong nước</option>
            <option value="Khác">Khác</option>
          </select>
        </EFormField>

        <div className="sm:col-span-2">
          <EFormField label="Nơi cư trú" required>
            <textarea
              className="min-h-24 w-full resize-y rounded-md border border-[#DCE3EA] bg-white px-3 py-3 text-[15px] text-[#212B36] outline-none transition placeholder:text-[#A0AAB4] focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20"
              id={`${side}-residence`}
              onChange={(event) => onChange("residence", event.target.value)}
              placeholder="Nhập địa chỉ cư trú hiện tại"
              required
              value={details.residence}
            />
          </EFormField>
        </div>
      </div>
    </fieldset>
  );
}

export function MarriageEForm({
  experience = standardMarriageExperience,
  selectedReceptionUnit,
  selectedServiceId,
}: {
  experience?: ProcedureExperience;
  selectedReceptionUnit: string;
  selectedServiceId: string;
}) {
  const [partners, setPartners] = useState<
    Record<PartnerSide, PartnerDetails>
  >({
    female: createEmptyPartner(),
    male: createEmptyPartner(),
  });
  const [saved, setSaved] = useState(false);
  const selection = {
    receptionUnit: selectedReceptionUnit,
    serviceId: selectedServiceId,
  } as const;
  const selectedService = experience.services.find(
    (service) => service.id === selectedServiceId,
  );
  const submissionHref = withProcedureSelection(
    experience.routes.submission,
    selection,
    { step: "3" },
  );

  const updatePartner = (
    side: PartnerSide,
    field: keyof PartnerDetails,
    value: string,
  ) => {
    setSaved(false);
    setPartners((current) => ({
      ...current,
      [side]: { ...current[side], [field]: value },
    }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    markDeclarationSaved(experience, selection);
    setSaved(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("marriage-e-form-status")
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  return (
    <section className="min-h-[calc(100vh-120px)] bg-[#F2F5F8] px-3 py-6 text-[#212B36] sm:px-6 sm:py-10">
      <div className="mx-auto w-full max-w-[1350px]">
        <div className="rounded-lg bg-white px-4 py-5 shadow-sm sm:px-7 sm:py-6">
          <div className="flex items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#CE7A58]/10 text-[#CE7A58]">
              <FilePenLine aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold tracking-[0.12em] text-[#CE7A58] uppercase">
                Mẫu hộ tịch điện tử tương tác
              </p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">
                Tờ khai đăng ký kết hôn
              </h1>
              <p className="mt-1 text-sm text-[#637381]">
                {experience.title} · Mã thủ tục: {experience.code}
              </p>
            </div>
          </div>
        </div>

        <form
          className="mt-6 rounded-lg bg-white px-4 py-6 shadow-sm sm:px-7 sm:py-8"
          onSubmit={handleSubmit}
        >
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-[#F1D3C7] bg-[#FFF8F5] p-4 text-sm leading-6 text-[#5A4A43]">
            <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-[#CE7A58]" />
            <p>
              Nhập thông tin đúng theo giấy tờ hợp lệ của hai bên. Biểu mẫu này
              là bản mô phỏng, không gửi hoặc lưu thông tin lên máy chủ.
            </p>
          </div>

          <div className="grid items-start gap-6 xl:grid-cols-2">
            <PartnerPanel
              accentClassName="bg-[#903938]/10 text-[#903938]"
              details={partners.female}
              label="Thông tin bên nữ"
              onChange={(field, value) => updatePartner("female", field, value)}
              showPhoto={experience.slug === "dang-ky-ket-hon-co-yeu-to-nuoc-ngoai"}
              side="female"
            />
            <PartnerPanel
              accentClassName="bg-[#CE7A58]/10 text-[#B55632]"
              details={partners.male}
              label="Thông tin bên nam"
              onChange={(field, value) => updatePartner("male", field, value)}
              side="male"
            />
          </div>

          <section className="mt-6 rounded-lg border border-[#E1E7EC] bg-[#F8FAFC] p-4 sm:p-6">
            <h2 className="font-bold">Thông tin đăng ký</h2>
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <EFormField label="Cơ quan đăng ký hộ tịch">
                <input
                  className={inputClassName}
                  readOnly
                  value={selectedService?.authority ?? ""}
                />
              </EFormField>
              <EFormField label="Đơn vị tiếp nhận">
                <input
                  className={inputClassName}
                  readOnly
                  value={selectedReceptionUnit}
                />
              </EFormField>
              <EFormField label="Hình thức nộp hồ sơ">
                <input className={inputClassName} readOnly value="Trực tuyến" />
              </EFormField>
              <EFormField label="Loại đăng ký" required>
                <select className={inputClassName} defaultValue="first" required>
                  <option value="first">Đăng ký lần đầu</option>
                  <option value="repeat">Đăng ký lại</option>
                </select>
              </EFormField>
              <EFormField label="Đề nghị cấp bản sao" required>
                <select className={inputClassName} defaultValue="no" required>
                  <option value="no">Không</option>
                  <option value="yes">Có</option>
                </select>
              </EFormField>
            </div>

            <label className="mt-6 flex cursor-pointer items-start gap-3 text-sm leading-6 text-[#52606D]">
              <input
                className="mt-1 size-4 accent-[#CE7A58]"
                required
                type="checkbox"
              />
              <span>
                Chúng tôi cam đoan lời khai trên là đúng sự thật, việc kết hôn
                là hoàn toàn tự nguyện và chịu trách nhiệm trước pháp luật về
                nội dung kê khai.
              </span>
            </label>
          </section>

          {saved ? (
            <div
              className="mt-6 flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800"
              id="marriage-e-form-status"
              role="status"
            >
              <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              <div>
                <p className="font-bold">Đã lưu tờ khai trong phiên mô phỏng</p>
                <p className="mt-1 text-sm">
                  Quay lại thành phần hồ sơ để tiếp tục quy trình.
                </p>
              </div>
            </div>
          ) : null}

          <div className="mt-8 flex flex-col-reverse justify-end gap-3 border-t border-[#EDF1F4] pt-6 sm:flex-row">
            <Link
              className={`${focusClassName} inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#DCE3EA] bg-white px-5 text-sm font-bold text-[#52606D] transition hover:bg-[#F7F9FA]`}
              href={submissionHref}
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
              Quay lại
            </Link>
            {saved ? (
              <Link
                className={`${focusClassName} inline-flex h-10 items-center justify-center rounded-lg bg-[#CE7A58] px-5 text-sm font-bold text-white transition hover:bg-[#BC5D37]`}
                href={submissionHref}
              >
                Trở về thành phần hồ sơ
              </Link>
            ) : (
              <button
                className={`${focusClassName} inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[#CE7A58] px-5 text-sm font-bold text-white transition hover:bg-[#BC5D37]`}
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
