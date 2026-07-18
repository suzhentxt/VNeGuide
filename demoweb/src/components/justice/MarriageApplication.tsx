"use client";

import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  FileText,
  FolderHeart,
  Info,
  Save,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { type ChangeEvent, type FormEvent, type ReactNode, useState } from "react";

import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { getEnumLabel, isBlockingRequirement, type GuidedFieldDefinition } from "@/data/guided-fields";
import { provinceOptions } from "@/data/portal-authorities";
import { standardMarriageExperience, type ProcedureExperience } from "@/data/procedure-experiences";
import { declarationGate } from "@/lib/guided-application";
import { createWallet, walletValuesForProcedure, type InformationWallet } from "@/lib/information-wallet";
import { markDeclarationSaved } from "@/lib/procedure-selection";
import type { JsonValue } from "@/types/chat";

type WizardStep = 1 | 2 | 3 | 4;
type ReceiptMethod = "counter" | "post" | "digital";

const wizardSteps = [
  "Nơi tiếp nhận",
  "Kê khai thông tin",
  "Giấy tờ hồ sơ",
  "Kiểm tra và nhận kết quả",
] as const;
const inputClass =
  "min-h-12 w-full rounded-xl border border-[#cbd5df] bg-white px-4 py-2 text-base text-[#1e2f41] outline-none transition focus:border-[#ce7a58] focus:ring-4 focus:ring-[#ce7a58]/15 aria-[invalid=true]:border-[#b42318] aria-[invalid=true]:bg-[#fff8f7]";
const WALLET_KEY = "vneguide:information-wallet:v1";

function text(value: JsonValue | undefined) {
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function booleanText(value: JsonValue | undefined) {
  return typeof value === "boolean" ? String(value) : "";
}

function FieldLabel({ children, required }: { children: ReactNode; required?: boolean }) {
  return (
    <span className="mb-2 block text-base font-extrabold text-[#334155]">
      {children}{required ? <span className="text-[#b42318]"> *</span> : null}
    </span>
  );
}

function WizardProgress({ currentStep, onSelect }: { currentStep: WizardStep; onSelect: (step: WizardStep) => void }) {
  return (
    <ol aria-label="Tiến trình nộp hồ sơ" className="grid grid-cols-4 gap-1 pt-5">
      {wizardSteps.map((label, index) => {
        const step = (index + 1) as WizardStep;
        const complete = step < currentStep;
        const active = step === currentStep;
        return (
          <li className="min-w-0 text-center" key={label}>
            <button
              aria-current={active ? "step" : undefined}
              className={`mx-auto flex size-9 items-center justify-center rounded-full text-sm font-extrabold text-white focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] ${complete || active ? "bg-[#903938]" : "bg-[#9aa4b2]"}`}
              disabled={step > currentStep}
              onClick={() => onSelect(step)}
              type="button"
            >
              {complete ? <Check className="size-5" aria-hidden="true" /> : step}
            </button>
            <span className={`mt-2 hidden text-sm font-bold sm:block ${active || complete ? "text-[#1e2f41]" : "text-[#7a8793]"}`}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function AssistantPanel({ step, missing }: { step: WizardStep; missing: string[] }) {
  const prompt = `Hãy hướng dẫn tôi hoàn thành bước ${step}: ${wizardSteps[step - 1]}${missing.length ? `. Tôi còn thiếu: ${missing.join(", ")}` : ""}.`;
  return (
    <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
      <section className="rounded-2xl border-2 border-[#d9b2a3] bg-[#fff8f5] p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-full bg-[#903938] text-white"><Bot className="size-6" aria-hidden="true" /></span>
          <div><p className="text-sm font-bold text-[#903938]">Trợ lý đi cùng hồ sơ</p><h2 className="font-extrabold text-[#1e2f41]">Đang ở bước {step}/4</h2></div>
        </div>
        <p className="mt-4 text-sm leading-6 text-[#52606d]">Bạn có thể hỏi cách điền, ý nghĩa của từng mục hoặc nói thông tin bằng lời tự nhiên.</p>
        <button
          className="mt-4 min-h-12 w-full rounded-xl bg-[#903938] px-4 font-extrabold text-white hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251]"
          onClick={() => window.dispatchEvent(new CustomEvent("vneguide:open-assistant", { detail: { prompt } }))}
          type="button"
        >
          Mở trợ lý cho bước này
        </button>
      </section>
      <section className="rounded-2xl border border-[#b9d8c4] bg-[#f1f8f3] p-5 text-sm leading-6 text-[#28543a]">
        <ShieldCheck className="mb-2 size-5" aria-hidden="true" />
        <p className="font-extrabold">Quy tắc an toàn</p>
        <p>Tự nhập hoặc tự chọn: có thể đi tiếp ngay khi đủ mục. Thông tin do trợ lý hoặc ví điền: phải được bạn xác nhận trước.</p>
      </section>
    </aside>
  );
}

function GuidedField({ definition, showError }: { definition: GuidedFieldDefinition; showError: boolean }) {
  const workspace = useProcedureWorkspace();
  const field = workspace.state.fields[definition.field_id];
  const value = field?.value;
  const required = isBlockingRequirement(definition.requirement);
  const missing = required && (value === undefined || value === null || value === "");
  const set = (next: JsonValue) => workspace.setField(definition.field_id, next);
  const commit = () => void workspace.commitField(definition.field_id);
  const common = {
    "aria-invalid": showError && missing,
    className: inputClass,
    id: definition.field_id,
    onBlur: commit,
  };

  let control: ReactNode;
  if (definition.type === "enum") {
    control = (
      <select {...common} value={text(value)} onChange={(event) => set(event.target.value)}>
        <option value="">Chọn một phương án</option>
        {definition.values?.map((option) => <option key={option} value={option}>{getEnumLabel(option)}</option>)}
      </select>
    );
  } else if (definition.type === "boolean") {
    control = (
      <select {...common} value={booleanText(value)} onChange={(event) => set(event.target.value === "" ? null : event.target.value === "true")}>
        <option value="">Chọn Có hoặc Không</option><option value="true">Có</option><option value="false">Không</option>
      </select>
    );
  } else {
    const inputType = definition.type === "date" ? "date" : definition.type === "integer" || definition.type === "number" ? "number" : "text";
    control = (
      <input
        {...common}
        inputMode={inputType === "number" ? "decimal" : undefined}
        min={definition.minimum}
        pattern={definition.pattern}
        step={definition.type === "integer" ? 1 : definition.type === "number" ? "any" : undefined}
        type={inputType}
        value={text(value)}
        onChange={(event) => set(inputType === "number" && event.target.value !== "" ? Number(event.target.value) : event.target.value)}
      />
    );
  }

  return (
    <div data-field-id={definition.field_id}>
      <label htmlFor={definition.field_id}><FieldLabel required={required}>{definition.label}</FieldLabel></label>
      {control}
      {field?.source === "wallet" && !field.confirmed ? <p className="mt-2 text-sm font-bold text-[#9a6700]">Ví thông tin đã điền · cần bạn xác nhận</p> : null}
      {field?.source === "assistant" && field.confirmed ? <p className="mt-2 text-sm font-bold text-[#28543a]">Đề xuất của trợ lý đã được bạn xác nhận</p> : null}
      {showError && missing ? <p className="mt-2 text-sm font-bold text-[#b42318]">Vui lòng hoàn thành mục này.</p> : null}
      {field?.error ? <p className="mt-2 text-sm text-[#b42318]">{field.error}</p> : null}
    </div>
  );
}

export function MarriageApplication({
  experience = standardMarriageExperience,
  initialStep = 1,
  selectedReceptionUnit: initialReceptionUnit,
  selectedServiceId,
  guidedFields,
}: {
  experience?: ProcedureExperience;
  initialStep?: WizardStep;
  selectedReceptionUnit: string;
  selectedServiceId: string;
  guidedFields: GuidedFieldDefinition[];
}) {
  const workspace = useProcedureWorkspace();
  const definitions = guidedFields;
  const selectedService = experience.services.find((service) => service.id === selectedServiceId);
  const [currentStep, setCurrentStep] = useState<WizardStep>(initialStep);
  const [provinceId, setProvinceId] = useState("");
  const [receptionUnit, setReceptionUnit] = useState(initialReceptionUnit);
  const [applicantRole, setApplicantRole] = useState("");
  const [receiptMethod, setReceiptMethod] = useState<ReceiptMethod>("counter");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [fileNames, setFileNames] = useState<Record<string, string>>({});
  const [attemptedStep, setAttemptedStep] = useState<WizardStep | null>(null);
  const [walletNotice, setWalletNotice] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  if (!selectedService) throw new Error("Dịch vụ công được chọn không hợp lệ.");

  const declaration = declarationGate(definitions, workspace.state.fields);
  const requiredDocuments = experience.justiceDossier.filter((row) => row.required && !row.eForm);
  const missingDocuments = requiredDocuments.filter((row) => !fileNames[row.id]);
  const stepMissing = {
    1: [!provinceId ? "Tỉnh/thành phố" : null, !receptionUnit.trim() ? "Phường/xã hoặc đơn vị tiếp nhận" : null, !applicantRole ? "Người thực hiện" : null].filter(Boolean) as string[],
    2: [...declaration.missing, ...declaration.unconfirmed].map((field) => field.label),
    3: missingDocuments.map((row) => row.name),
    4: receiptMethod === "post" && !deliveryAddress.trim() ? ["Địa chỉ nhận kết quả"] : [],
  } satisfies Record<WizardStep, string[]>;
  const canAdvance = stepMissing[currentStep].length === 0;

  const moveToStep = (step: WizardStep) => {
    setCurrentStep(step);
    setAttemptedStep(null);
    setSubmitted(false);
    window.requestAnimationFrame(() => document.getElementById("guided-application")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const saveWallet = () => {
    const wallet = createWallet(workspace.state.fields);
    if (!Object.keys(wallet).length) {
      setWalletNotice("Chưa có thông tin đã xác nhận để lưu vào ví.");
      return;
    }
    window.sessionStorage.setItem(WALLET_KEY, JSON.stringify(wallet));
    setWalletNotice("Đã lưu các thông tin dùng lại trong phiên trình duyệt này.");
  };

  const loadWallet = () => {
    try {
      const raw = window.sessionStorage.getItem(WALLET_KEY);
      if (!raw) { setWalletNotice("Ví thông tin của phiên này đang trống."); return; }
      const values = walletValuesForProcedure(JSON.parse(raw) as InformationWallet, definitions.map((field) => field.field_id));
      if (!Object.keys(values).length) { setWalletNotice("Ví chưa có thông tin phù hợp với thủ tục này."); return; }
      workspace.prefillFromWallet(values);
      setWalletNotice(`Đã điền ${Object.keys(values).length} mục từ ví. Hãy kiểm tra và xác nhận trước khi đi tiếp.`);
    } catch {
      setWalletNotice("Không thể đọc ví thông tin. Bạn vẫn có thể nhập trực tiếp.");
    }
  };

  const confirmAssistedFields = async () => {
    const fieldIds = declaration.unconfirmed.map((field) => field.field_id);
    workspace.confirmFields(fieldIds);
    for (const fieldId of fieldIds) await workspace.commitField(fieldId);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAttemptedStep(currentStep);
    if (!canAdvance) return;
    if (currentStep === 2) {
      markDeclarationSaved(experience, { receptionUnit, serviceId: selectedService.id });
    }
    if (currentStep < 4) moveToStep((currentStep + 1) as WizardStep);
    else setSubmitted(true);
  };

  const content: Record<WizardStep, ReactNode> = {
    1: (
      <div className="space-y-6">
        <div className="flex items-start gap-3 rounded-xl border border-[#b9d8c4] bg-[#f1f8f3] p-4 text-[#28543a]">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <div><p className="font-extrabold">Bạn đã xác nhận đúng dịch vụ</p><p className="mt-1 text-sm leading-6">{experience.title}</p></div>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <label><FieldLabel required>Tỉnh/thành phố nơi tiếp nhận</FieldLabel><select aria-invalid={attemptedStep === 1 && !provinceId} className={inputClass} value={provinceId} onChange={(event) => setProvinceId(event.target.value)}><option value="">Chọn tỉnh/thành phố</option>{provinceOptions.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
          <label><FieldLabel required>Phường/xã hoặc đơn vị tiếp nhận</FieldLabel><input aria-invalid={attemptedStep === 1 && !receptionUnit.trim()} className={inputClass} placeholder="Ví dụ: UBND phường…" value={receptionUnit} onChange={(event) => setReceptionUnit(event.target.value)} /></label>
          <label><FieldLabel required>Bạn thực hiện cho ai?</FieldLabel><select aria-invalid={attemptedStep === 1 && !applicantRole} className={inputClass} value={applicantRole} onChange={(event) => setApplicantRole(event.target.value)}><option value="">Chọn một phương án</option><option value="self">Cho bản thân</option><option value="relative">Cho người thân</option><option value="authorized">Theo ủy quyền</option></select></label>
          <div className="rounded-xl border border-[#d9e2ec] bg-[#f8fafc] p-4"><p className="text-sm text-[#667085]">Cơ quan thực hiện</p><p className="mt-1 font-extrabold text-[#1e2f41]">{selectedService.authority}</p></div>
        </div>
      </div>
    ),
    2: (
      <div className="space-y-6">
        <div className="rounded-xl border border-[#f0c36a] bg-[#fff9e8] p-4 text-sm leading-6 text-[#704d09]"><Info className="mr-2 inline size-5" aria-hidden="true" />Chỉ dùng dữ liệu giả trong bản demo. Dữ liệu do trợ lý đề xuất chỉ xuất hiện sau khi bạn bấm Chấp nhận hoặc Sửa.</div>
        <div className="flex flex-wrap gap-3 rounded-xl border border-[#d9e2ec] bg-[#f8fafc] p-4">
          <button className="min-h-11 rounded-xl border-2 border-[#903938] bg-white px-4 font-bold text-[#903938]" onClick={loadWallet} type="button"><FolderHeart className="mr-2 inline size-5" />Điền từ ví thông tin</button>
          <button className="min-h-11 rounded-xl border border-[#cbd5df] bg-white px-4 font-bold text-[#334155]" onClick={saveWallet} type="button"><Save className="mr-2 inline size-5" />Lưu thông tin dùng lại</button>
          {walletNotice ? <p className="w-full text-sm font-semibold text-[#52606d]" role="status">{walletNotice}</p> : null}
        </div>
        {declaration.unconfirmed.length ? (
          <section className="rounded-xl border-2 border-[#f0c36a] bg-[#fff9e8] p-4">
            <h3 className="font-extrabold text-[#704d09]">Cần bạn xác nhận {declaration.unconfirmed.length} thông tin đã được điền giúp</h3>
            <ul className="mt-2 list-disc pl-5 text-sm text-[#704d09]">{declaration.unconfirmed.map((field) => <li key={field.field_id}>{field.label}</li>)}</ul>
            <button className="mt-4 min-h-12 rounded-xl bg-[#903938] px-5 font-extrabold text-white" onClick={() => void confirmAssistedFields()} type="button">Tôi đã kiểm tra, thông tin chính xác</button>
          </section>
        ) : null}
        <div className="grid gap-6 sm:grid-cols-2">{definitions.map((definition) => <GuidedField definition={definition} key={definition.field_id} showError={attemptedStep === 2} />)}</div>
      </div>
    ),
    3: (
      <div className="space-y-4">
        <p className="rounded-xl border border-[#b9cde5] bg-[#f2f7fc] p-4 text-sm leading-6 text-[#24496f]">Tờ khai điện tử được tạo từ thông tin ở bước 2. Với giấy tờ khác, bản demo chỉ giữ tên tệp trên thiết bị và không tải lên máy chủ.</p>
        {experience.justiceDossier.map((row) => (
          <div className="flex flex-col gap-4 rounded-xl border border-[#d9e2ec] p-4 sm:flex-row sm:items-center sm:justify-between" key={row.id}>
            <div><p className="font-extrabold text-[#1e2f41]">{row.name}</p><p className="mt-1 text-sm text-[#667085]">{row.eForm ? "Đã kê khai ở bước 2" : row.required ? "Bắt buộc" : "Chỉ cần khi áp dụng"}</p>{fileNames[row.id] ? <p className="mt-1 text-sm font-bold text-[#28543a]">Đã chọn: {fileNames[row.id]}</p> : null}</div>
            {row.eForm ? <span className="inline-flex min-h-11 items-center rounded-xl bg-[#f1f8f3] px-4 font-bold text-[#28543a]"><Check className="mr-2 size-5" />Đã hoàn thành</span> : <label className="inline-flex min-h-11 cursor-pointer items-center justify-center rounded-xl border-2 border-[#ce7a58] px-4 font-bold text-[#762b2b]"><Upload className="mr-2 size-5" />Chọn tệp<input className="sr-only" type="file" onChange={(event: ChangeEvent<HTMLInputElement>) => setFileNames((current) => ({ ...current, [row.id]: event.target.files?.[0]?.name ?? "" }))} /></label>}
          </div>
        ))}
      </div>
    ),
    4: (
      <div className="space-y-6">
        <fieldset><legend className="mb-4 text-lg font-extrabold">Bạn muốn nhận kết quả bằng cách nào?</legend><div className="grid gap-3 sm:grid-cols-3">{([['counter','Nhận trực tiếp'],['post','Qua bưu chính'],['digital','Bản điện tử']] as const).map(([id, label]) => <label className={`cursor-pointer rounded-xl border-2 p-4 font-bold ${receiptMethod === id ? "border-[#903938] bg-[#fff8f5]" : "border-[#d9e2ec]"}`} key={id}><input checked={receiptMethod === id} className="mr-2 accent-[#903938]" name="receipt" onChange={() => setReceiptMethod(id)} type="radio" />{label}</label>)}</div></fieldset>
        {receiptMethod === "post" ? <label><FieldLabel required>Địa chỉ nhận kết quả</FieldLabel><textarea aria-invalid={attemptedStep === 4 && !deliveryAddress.trim()} className={`${inputClass} min-h-24`} value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} /></label> : null}
        <section className="rounded-xl border border-[#d9e2ec] bg-[#f8fafc] p-5"><h3 className="font-extrabold">Kiểm tra lần cuối</h3><dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2"><div><dt className="text-[#667085]">Thủ tục</dt><dd className="mt-1 font-bold">{experience.title}</dd></div><div><dt className="text-[#667085]">Nơi tiếp nhận</dt><dd className="mt-1 font-bold">{receptionUnit}</dd></div><div><dt className="text-[#667085]">Thông tin đã xác nhận</dt><dd className="mt-1 font-bold">{Object.values(workspace.state.fields).filter((field) => field.confirmed).length}/{definitions.length}</dd></div><div><dt className="text-[#667085]">Giấy tờ đã chuẩn bị</dt><dd className="mt-1 font-bold">{experience.justiceDossier.length - missingDocuments.length}/{experience.justiceDossier.length}</dd></div></dl></section>
        {submitted ? <div className="flex gap-3 rounded-xl border border-[#98d0aa] bg-[#effaf2] p-5 text-[#25633f]" role="status"><CheckCircle2 className="size-6 shrink-0" /><div><p className="font-extrabold">Đã hoàn tất bản mô phỏng hồ sơ</p><p className="mt-1 text-sm">Chưa có dữ liệu hoặc tài liệu nào được gửi tới cơ quan nhà nước.</p></div></div> : null}
      </div>
    ),
  };

  return (
    <main className="min-h-[calc(100vh-120px)] bg-[#f2f5f8] px-4 py-6 text-[#1e2f41] sm:px-6 sm:py-10">
      <div className="mx-auto max-w-7xl scroll-mt-4" id="guided-application">
        <header className="rounded-2xl bg-white p-5 shadow-sm sm:p-7"><div className="flex gap-3"><span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-[#903938] text-white"><FileText className="size-6" /></span><div><p className="text-sm font-extrabold tracking-wide text-[#903938] uppercase">Hồ sơ được trợ lý hướng dẫn</p><h1 className="mt-1 text-xl font-extrabold sm:text-2xl">{experience.title}</h1></div></div><WizardProgress currentStep={currentStep} onSelect={moveToStep} /></header>
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <form className="rounded-2xl bg-white p-5 shadow-sm sm:p-8" noValidate onSubmit={handleSubmit}>
            <div className="mb-6 border-b border-[#e5eaf0] pb-4"><p className="text-sm font-bold text-[#903938]">Bước {currentStep} / 4</p><h2 className="mt-1 text-2xl font-extrabold">{wizardSteps[currentStep - 1]}</h2></div>
            {attemptedStep === currentStep && !canAdvance ? <div className="mb-6 rounded-xl border border-[#efb4b4] bg-[#fff1f1] p-4 text-[#8b1e1e]" role="alert"><p className="font-extrabold">Chưa thể sang bước tiếp theo</p><ul className="mt-2 list-disc pl-5 text-sm">{stepMissing[currentStep].map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
            {content[currentStep]}
            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-[#e5eaf0] pt-6 sm:flex-row sm:justify-between">
              <button className="inline-flex min-h-12 items-center justify-center rounded-xl border border-[#cbd5df] px-5 font-bold text-[#334155] disabled:opacity-40" disabled={currentStep === 1} onClick={() => moveToStep((currentStep - 1) as WizardStep)} type="button"><ArrowLeft className="mr-2 size-5" />Quay lại</button>
              <button className="inline-flex min-h-12 items-center justify-center rounded-xl bg-[#903938] px-6 font-extrabold text-white hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50" disabled={submitted} type="submit">{currentStep === 4 ? submitted ? "Đã hoàn tất" : "Hoàn tất bản mô phỏng" : "Tiếp tục sang bước sau"}</button>
            </div>
          </form>
          <AssistantPanel missing={stepMissing[currentStep]} step={currentStep} />
        </div>
      </div>
    </main>
  );
}
