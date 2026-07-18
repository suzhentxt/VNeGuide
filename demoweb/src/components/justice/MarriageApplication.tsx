"use client";

import {
  ArrowLeft,
  Check,
  CircleUserRound,
  FileCheck2,
  FileText,
  Info,
  Mail,
  MapPin,
  Paperclip,
  Phone,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import {
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
  useState,
  useSyncExternalStore,
} from "react";

import {
  standardMarriageExperience,
  type OnlineDossierRow,
  type ProcedureExperience,
} from "@/data/procedure-experiences";
import {
  hasSavedDeclaration,
  withProcedureSelection,
} from "@/lib/procedure-selection";

type WizardStep = 1 | 2 | 3 | 4;
type ReceiptMethod = "counter" | "post" | "digital";
type ProcedureService = ProcedureExperience["services"][number];

const wizardSteps = [
  "Thông tin chủ hồ sơ",
  "Kê khai thông tin",
  "Thành phần hồ sơ",
  "Thông tin nhận kết quả",
] as const;

const identityDetails = [
  "Họ và tên",
  "Quốc tịch",
  "Giới tính",
  "Loại giấy tờ",
  "Ngày tháng năm sinh",
  "Số giấy tờ",
  "Địa chỉ chi tiết",
] as const;

const inputClassName =
  "h-11 w-full rounded-md border border-[#DCE3EA] bg-white px-3 text-[15px] text-[#212B36] shadow-[inset_0_1px_1px_rgba(17,24,39,0.02)] outline-none transition focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20 disabled:cursor-not-allowed disabled:bg-[#F4F6F8]";

const buttonFocusClassName =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#CE7A58] focus-visible:ring-offset-2";

const subscribeToDeclarationState = () => () => undefined;

function Field({
  children,
  label,
  required = false,
}: {
  children: ReactNode;
  label: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-[#637381]">
        {label}
        {required ? <span className="text-red-500"> *</span> : null}
      </p>
      {children}
    </div>
  );
}

function WizardProgress({
  currentStep,
  onSelect,
}: {
  currentStep: WizardStep;
  onSelect: (step: WizardStep) => void;
}) {
  return (
    <ol
      aria-label="Tiến trình nộp hồ sơ"
      className="grid grid-cols-4 px-1 pt-4 sm:px-4"
    >
      {wizardSteps.map((label, index) => {
        const step = (index + 1) as WizardStep;
        const complete = step < currentStep;
        const active = step === currentStep;
        const selectable = step <= currentStep;

        return (
          <li className="relative min-w-0 text-center" key={label}>
            {index < wizardSteps.length - 1 ? (
              <span
                aria-hidden="true"
                className={`absolute top-3 left-[calc(50%+18px)] h-px w-[calc(100%-36px)] ${
                  complete ? "bg-[#CE7A58]" : "bg-[#637381]/20"
                }`}
              />
            ) : null}
            <button
              aria-current={active ? "step" : undefined}
              className={`${buttonFocusClassName} relative z-10 mx-auto flex size-6 items-center justify-center rounded-full text-xs font-bold text-white transition ${
                complete || active ? "bg-[#CE7A58]" : "bg-[#637381]"
              } ${selectable ? "cursor-pointer" : "cursor-default"}`}
              disabled={!selectable}
              onClick={() => onSelect(step)}
              type="button"
            >
              {complete ? <Check aria-hidden="true" className="size-3.5" /> : step}
            </button>
            <span
              className={`mt-3 block px-1 text-[11px] leading-4 font-semibold sm:text-sm ${
                active || complete ? "text-[#212B36]" : "text-[#919EAB]"
              }`}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function IdentityCard() {
  return (
    <section className="rounded-lg bg-white p-4 shadow-[0_12px_24px_-4px_rgba(145,158,171,0.12),0_0_2px_rgba(145,158,171,0.2)] sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-4 border-b border-[#EEF1F4] pb-4">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-[#CE7A58]/10 text-[#CE7A58]">
            <CircleUserRound aria-hidden="true" className="size-5" />
          </span>
          <div>
            <h3 className="font-bold text-[#212B36]">Thông tin định danh</h3>
            <p className="mt-0.5 text-xs text-[#637381]">
              Chưa có dữ liệu định danh trong bản demo
            </p>
          </div>
        </div>
      </div>

      <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
        {identityDetails.map((label) => (
          <div className="flex min-w-0 gap-3" key={label}>
            <dt className="w-[42%] shrink-0 text-[#637381]">{label}:</dt>
            <dd className="min-w-0 break-words text-[#919EAB] italic">
              Chưa có dữ liệu
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ApplicantInformation() {
  return (
    <div className="space-y-6">
      <IdentityCard />

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Ngày cấp" required>
          <input
            aria-label="Ngày cấp giấy tờ"
            className={inputClassName}
            name="document-issued-date"
            required
            type="date"
          />
        </Field>
        <Field label="Nơi cấp (Nhập hoặc chọn)" required>
          <select className={inputClassName} defaultValue="" name="document-issuer" required>
            <option disabled value="">
              Chọn nơi cấp
            </option>
            <option value="national">Cơ quan quản lý căn cước</option>
            <option value="local">Công an địa phương</option>
            <option value="other">Cơ quan có thẩm quyền khác</option>
          </select>
        </Field>
        <Field label="Số điện thoại" required>
          <div className="relative">
            <Phone
              aria-hidden="true"
              className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[#919EAB]"
            />
            <input
              className={`${inputClassName} pl-10`}
              inputMode="tel"
              name="phone"
              pattern="[0-9]{10}"
              placeholder="Nhập số điện thoại"
              required
              type="tel"
            />
          </div>
        </Field>
        <Field label="Thư điện tử">
          <div className="relative">
            <Mail
              aria-hidden="true"
              className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[#919EAB]"
            />
            <input
              className={`${inputClassName} pl-10`}
              name="email"
              placeholder="Nhập thư điện tử"
              type="email"
            />
          </div>
        </Field>
        <div className="sm:col-span-2">
          <Field label="Địa chỉ chi tiết" required>
            <div className="relative">
              <MapPin
                aria-hidden="true"
                className="absolute top-3.5 left-3 size-4 text-[#919EAB]"
              />
              <textarea
                className="min-h-24 w-full resize-y rounded-md border border-[#DCE3EA] bg-white px-3 py-3 pl-10 text-[15px] text-[#212B36] outline-none transition focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20"
                name="address"
                placeholder="Nhập địa chỉ chi tiết"
                required
              />
            </div>
          </Field>
        </div>
      </div>
    </div>
  );
}

function DeclarationInformation({
  experience,
  selectedReceptionUnit,
  selectedService,
}: {
  experience: ProcedureExperience;
  selectedReceptionUnit: string;
  selectedService: ProcedureService;
}) {
  const isMarriage = experience.formKind === "marriage";

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[#E4E9EE] bg-[#F8FAFC] p-4 text-sm leading-6 text-[#52606D]">
        <div className="flex gap-3">
          <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-[#CE7A58]" />
          <p>
            Kiểm tra phạm vi hồ sơ trước khi chuyển sang thành phần hồ sơ. Tờ
            khai hộ tịch điện tử sẽ được mở ở bước tiếp theo.
          </p>
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Cơ quan thực hiện" required>
          <input
            className={inputClassName}
            readOnly
            value={selectedService.authority}
          />
        </Field>
        <Field label="Đơn vị tiếp nhận" required>
          <input
            className={inputClassName}
            readOnly
            value={selectedReceptionUnit}
          />
        </Field>
        <Field label="Đối tượng thực hiện" required>
          <select className={inputClassName} defaultValue="self" required>
            <option value="self">Làm thủ tục cho bản thân</option>
            <option value="representative">Nộp thay theo ủy quyền</option>
          </select>
        </Field>
        <Field label="Lĩnh vực">
          <input className={inputClassName} readOnly value={experience.field} />
        </Field>
        <Field label="Mã thủ tục">
          <input className={inputClassName} readOnly value={experience.code} />
        </Field>
      </div>

      <fieldset className="rounded-lg border border-[#E4E9EE] p-4 sm:p-5">
        <legend className="px-2 font-bold text-[#212B36]">Nội dung xác nhận</legend>
        <div className="space-y-4 text-sm leading-6 text-[#52606D]">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              className="mt-1 size-4 accent-[#CE7A58]"
              defaultChecked
              required
              type="checkbox"
            />
            <span>
              {isMarriage
                ? "Hai bên nam, nữ tự nguyện đăng ký kết hôn và chịu trách nhiệm về nội dung kê khai."
                : "Người yêu cầu xác nhận nội dung đề nghị thay đổi, cải chính hoặc bổ sung thông tin hộ tịch là đúng sự thật."}
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              className="mt-1 size-4 accent-[#CE7A58]"
              defaultChecked
              required
              type="checkbox"
            />
            <span>
              Các giấy tờ đính kèm là bản chụp rõ nét từ giấy tờ hợp lệ, còn
              giá trị sử dụng.
            </span>
          </label>
        </div>
      </fieldset>
    </div>
  );
}

function DossierTable({
  declarationSaved,
  eFormRoute,
  rows,
}: {
  declarationSaved: boolean;
  eFormRoute: string;
  rows: readonly OnlineDossierRow[];
}) {
  const [fileNames, setFileNames] = useState<Record<string, string>>({});

  const handleFileChange = (
    rowId: string,
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    const nextFileName = event.target.files?.[0]?.name ?? "";
    setFileNames((current) => ({ ...current, [rowId]: nextFileName }));
  };

  return (
    <div className="space-y-6">
      {declarationSaved ? (
        <div
          className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          <FileCheck2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p>Tờ khai điện tử đã được lưu trong phiên mô phỏng này.</p>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-md border border-[#E2E8EE]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <caption className="sr-only">Danh sách thành phần hồ sơ</caption>
            <thead className="bg-[#F4F6F8] text-[#52606D]">
              <tr>
                <th className="w-16 px-4 py-3 text-center font-semibold">STT</th>
                <th className="px-4 py-3 text-left font-semibold">
                  Tên thành phần hồ sơ
                </th>
                <th className="w-48 px-4 py-3 text-center font-semibold">
                  Đính kèm tệp tin
                </th>
                <th className="w-28 px-4 py-3 text-center font-semibold">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E9EEF2] bg-white">
              {rows.map((row, index) => {
                const fileName = fileNames[row.id];
                return (
                  <tr className="align-top hover:bg-[#FAFBFC]" key={row.id}>
                    <td className="px-4 py-5 text-center text-[#637381]">
                      {index + 1}
                    </td>
                    <td className="px-4 py-5 leading-6 text-[#212B36]">
                      <p>{row.name}</p>
                      {row.required ? (
                        <span className="mt-2 inline-flex rounded-full bg-red-50 px-2.5 py-1 text-xs font-bold text-red-600">
                          Bắt buộc
                        </span>
                      ) : (
                        <span className="mt-2 inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                          Khi có yêu cầu
                        </span>
                      )}
                      {fileName ? (
                        <p className="mt-2 max-w-md truncate text-xs text-[#2E7D32]">
                          Đã chọn: {fileName}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-4 py-5 text-center">
                      {row.eForm ? (
                        <Link
                          className={`${buttonFocusClassName} inline-flex h-10 items-center justify-center gap-2 rounded-md bg-[#C35428] px-4 font-semibold text-white transition hover:bg-[#A04520]`}
                          href={eFormRoute}
                        >
                          <FileText aria-hidden="true" className="size-4" />
                          Khai tờ khai
                        </Link>
                      ) : (
                        <>
                          <input
                            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx"
                            className="sr-only"
                            id={`dossier-file-${row.id}`}
                            onChange={(event) => handleFileChange(row.id, event)}
                            type="file"
                          />
                          <label
                            className={`${buttonFocusClassName} inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-[#C9D1D9] bg-white px-4 font-semibold text-[#52606D] transition hover:border-[#CE7A58] hover:text-[#CE7A58]`}
                            htmlFor={`dossier-file-${row.id}`}
                          >
                            <Upload aria-hidden="true" className="size-4" />
                            Chọn tệp
                          </label>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-5 text-center">
                      {!row.eForm && fileName ? (
                        <button
                          aria-label={`Bỏ tệp ${fileName}`}
                          className={`${buttonFocusClassName} inline-flex size-10 items-center justify-center rounded-md text-[#637381] transition hover:bg-red-50 hover:text-red-600`}
                          onClick={() =>
                            setFileNames((current) => ({
                              ...current,
                              [row.id]: "",
                            }))
                          }
                          type="button"
                        >
                          <Trash2 aria-hidden="true" className="size-5" />
                        </button>
                      ) : (
                        <Paperclip
                          aria-label="Chưa có tệp đính kèm"
                          className="mx-auto size-5 text-[#B7C0C8]"
                        />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <button
        className={`${buttonFocusClassName} w-full rounded-md border-2 border-dashed border-[#C9D1D9] px-4 py-3 text-sm font-bold text-[#52606D] transition hover:border-[#CE7A58] hover:text-[#CE7A58]`}
        type="button"
      >
        Thêm thành phần hồ sơ
      </button>

      <Field label="Ghi chú (Trích yếu nội dung hồ sơ)">
        <textarea
          className="min-h-24 w-full resize-y rounded-md border border-[#DCE3EA] bg-white px-3 py-3 text-[15px] outline-none transition placeholder:text-[#919EAB] focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20"
          maxLength={5000}
          name="note"
          placeholder="Nhập ghi chú"
        />
      </Field>
      <p className="text-xs leading-5 text-[#7A8793]">
        Bản mô phỏng chỉ hiển thị tên tệp trên thiết bị và không tải tài liệu lên
        máy chủ.
      </p>
    </div>
  );
}

function ReceiptInformation({
  experience,
  method,
  onMethodChange,
  selectedReceptionUnit,
  selectedService,
  submitted,
}: {
  experience: ProcedureExperience;
  method: ReceiptMethod;
  onMethodChange: (method: ReceiptMethod) => void;
  selectedReceptionUnit: string;
  selectedService: ProcedureService;
  submitted: boolean;
}) {
  const receiptOptions: Array<{
    description: string;
    id: ReceiptMethod;
    label: string;
  }> = [
    {
      id: "counter",
      label: "Nhận trực tiếp",
      description: "Nhận tại Trung tâm Phục vụ hành chính công có thẩm quyền.",
    },
    {
      id: "post",
      label: "Nhận qua dịch vụ bưu chính",
      description: "Kết quả được gửi tới địa chỉ đăng ký nhận hồ sơ.",
    },
    {
      id: "digital",
      label: "Nhận bản điện tử",
      description: "Nhận thông báo và kết quả điện tử trên tài khoản dịch vụ công.",
    },
  ];

  return (
    <div className="space-y-6">
      <fieldset>
        <legend className="mb-4 font-bold text-[#212B36]">
          Chọn hình thức nhận kết quả
        </legend>
        <div className="grid gap-4 md:grid-cols-3">
          {receiptOptions.map((option) => (
            <label
              className={`cursor-pointer rounded-lg border p-4 transition ${
                method === option.id
                  ? "border-[#CE7A58] bg-[#CE7A58]/5 shadow-[0_0_0_1px_#CE7A58]"
                  : "border-[#DFE5EA] bg-white hover:border-[#CE7A58]/60"
              }`}
              key={option.id}
            >
              <span className="flex items-start gap-3">
                <input
                  checked={method === option.id}
                  className="mt-1 size-4 accent-[#CE7A58]"
                  name="receipt-method"
                  onChange={() => onMethodChange(option.id)}
                  type="radio"
                />
                <span>
                  <span className="block font-bold text-[#212B36]">
                    {option.label}
                  </span>
                  <span className="mt-2 block text-sm leading-5 text-[#637381]">
                    {option.description}
                  </span>
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {method === "post" ? (
        <Field label="Địa chỉ nhận kết quả" required>
          <textarea
            className="min-h-24 w-full resize-y rounded-md border border-[#DCE3EA] bg-white px-3 py-3 text-[15px] outline-none transition focus:border-[#CE7A58] focus:ring-2 focus:ring-[#CE7A58]/20"
            name="result-delivery-address"
            placeholder="Nhập địa chỉ nhận kết quả"
            required
          />
        </Field>
      ) : null}

      <div className="rounded-lg border border-[#E3E8ED] bg-[#F8FAFC] p-5">
        <h3 className="font-bold text-[#212B36]">Tóm tắt hồ sơ</h3>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[#637381]">Thủ tục</dt>
            <dd className="mt-1 font-semibold">{experience.title}</dd>
          </div>
          <div>
            <dt className="text-[#637381]">Mã thủ tục</dt>
            <dd className="mt-1 font-semibold">{experience.code}</dd>
          </div>
          <div>
            <dt className="text-[#637381]">Cơ quan thực hiện</dt>
            <dd className="mt-1 font-semibold">{selectedService.authority}</dd>
          </div>
          <div>
            <dt className="text-[#637381]">Đơn vị tiếp nhận</dt>
            <dd className="mt-1 font-semibold">{selectedReceptionUnit}</dd>
          </div>
          <div>
            <dt className="text-[#637381]">Lệ phí</dt>
            <dd className="mt-1 font-semibold text-green-700">Miễn phí</dd>
          </div>
        </dl>
      </div>

      {submitted ? (
        <div
          className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-5 text-green-800"
          role="status"
        >
          <Check aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">Đã hoàn tất bản mô phỏng hồ sơ</p>
            <p className="mt-1 text-sm leading-5">
              Chưa có dữ liệu hoặc tài liệu nào được gửi tới cơ quan nhà nước.
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function MarriageApplication({
  experience = standardMarriageExperience,
  initialStep = 1,
  selectedReceptionUnit,
  selectedServiceId,
}: {
  experience?: ProcedureExperience;
  initialStep?: WizardStep;
  selectedReceptionUnit: string;
  selectedServiceId: string;
}) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(initialStep);
  const [receiptMethod, setReceiptMethod] =
    useState<ReceiptMethod>("counter");
  const [submitted, setSubmitted] = useState(false);
  const selectedService = experience.services.find(
    (service) => service.id === selectedServiceId,
  );

  const declarationSaved = useSyncExternalStore(
    subscribeToDeclarationState,
    () =>
      selectedService
        ? hasSavedDeclaration(experience, {
            receptionUnit: selectedReceptionUnit,
            serviceId: selectedService.id,
          })
        : false,
    () => false,
  );

  if (!selectedService) {
    throw new Error("Dịch vụ công được chọn không hợp lệ.");
  }

  const selection = {
    receptionUnit: selectedReceptionUnit,
    serviceId: selectedService.id,
  } as const;

  const moveToStep = (nextStep: WizardStep) => {
    setCurrentStep(nextStep);
    setSubmitted(false);
    window.requestAnimationFrame(() => {
      document
        .getElementById("marriage-application-wizard")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (currentStep < 4) {
      moveToStep((currentStep + 1) as WizardStep);
      return;
    }
    setSubmitted(true);
  };

  const content = {
    1: <ApplicantInformation />,
    2: (
      <DeclarationInformation
        experience={experience}
        selectedReceptionUnit={selectedReceptionUnit}
        selectedService={selectedService}
      />
    ),
    3: (
      <DossierTable
        declarationSaved={declarationSaved}
        eFormRoute={withProcedureSelection(experience.routes.eForm, selection)}
        rows={experience.justiceDossier}
      />
    ),
    4: (
      <ReceiptInformation
        experience={experience}
        method={receiptMethod}
        onMethodChange={setReceiptMethod}
        selectedReceptionUnit={selectedReceptionUnit}
        selectedService={selectedService}
        submitted={submitted}
      />
    ),
  } satisfies Record<WizardStep, ReactNode>;

  return (
    <section className="min-h-[calc(100vh-120px)] bg-[#F2F5F8] px-3 py-6 text-[#212B36] sm:px-6 sm:py-10">
      <div
        className="mx-auto w-full max-w-[1350px] scroll-mt-4"
        id="marriage-application-wizard"
      >
        <section className="rounded-lg bg-white px-3 py-5 shadow-sm sm:px-6 sm:py-6">
          <div className="mb-2 flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[#CE7A58]/10 text-[#CE7A58]">
              <FileText aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold tracking-[0.12em] text-[#CE7A58] uppercase">
                Nộp hồ sơ trực tuyến
              </p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">
                {experience.title}
              </h1>
            </div>
          </div>
          <WizardProgress currentStep={currentStep} onSelect={moveToStep} />
        </section>

        <form
          className="mt-6 rounded-lg bg-white px-4 py-5 shadow-sm sm:px-8 sm:py-7"
          onSubmit={handleSubmit}
        >
          <div className="mb-6 border-b border-[#EDF1F4] pb-4">
            <p className="text-xs font-semibold text-[#919EAB]">
              Bước {currentStep} / 4
            </p>
            <h2 className="mt-1 text-xl font-bold sm:text-2xl">
              {wizardSteps[currentStep - 1]}
            </h2>
          </div>

          {content[currentStep]}

          <div className="mt-8 flex flex-col-reverse justify-end gap-3 border-t border-[#EDF1F4] pt-6 sm:flex-row">
            <button
              className={`${buttonFocusClassName} inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#DCE3EA] bg-white px-5 text-sm font-bold text-[#52606D] transition hover:bg-[#F7F9FA] disabled:cursor-not-allowed disabled:opacity-45`}
              disabled={currentStep === 1}
              onClick={() => moveToStep((currentStep - 1) as WizardStep)}
              type="button"
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
              Quay lại
            </button>
            <button
              className={`${buttonFocusClassName} inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[#CE7A58] px-5 text-sm font-bold text-white transition hover:bg-[#BC5D37] disabled:cursor-not-allowed disabled:opacity-60`}
              disabled={submitted}
              type="submit"
            >
              {currentStep === 4
                ? submitted
                  ? "Hồ sơ đã hoàn tất"
                  : "Hoàn tất hồ sơ"
                : "Bước tiếp theo"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
