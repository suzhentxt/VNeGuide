"use client";

import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  FileText,
  Info,
  ShieldCheck,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";

import { DocumentUploadCard } from "@/components/ocr/DocumentUploadCard";
import { useDocumentValidation } from "@/components/ocr/DocumentValidationProvider";
import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { getEnumLabel, isBlockingRequirement, type GuidedFieldDefinition } from "@/data/guided-fields";
import { standardMarriageExperience, type ProcedureExperience } from "@/data/procedure-experiences";
import { declarationGate } from "@/lib/guided-application";
import { markDeclarationSaved } from "@/lib/procedure-selection";
import type { JsonValue } from "@/types/chat";

type WizardStep = 1 | 2 | 3 | 4;
type ReceiptMethod = "counter" | "post" | "digital";

const wizardSteps = [
  "Kê khai thông tin",
  "Giấy tờ hồ sơ",
  "Nhận kết quả",
  "Kiểm tra hồ sơ",
] as const;
const inputClass =
  "min-h-12 w-full rounded-xl border border-[#cbd5df] bg-white px-4 py-2 text-base text-[#1e2f41] outline-none transition focus:border-[#ce7a58] focus:ring-4 focus:ring-[#ce7a58]/15 aria-[invalid=true]:border-[#b42318] aria-[invalid=true]:bg-[#fff8f7]";

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
  const prompts: Record<WizardStep, string> = {
    1: "Hãy hướng dẫn tôi điền hồ sơ từng bước.",
    2: "Tôi cần chuẩn bị những giấy tờ nào?",
    3: "Tôi có thể nhận kết quả bằng cách nào?",
    4: "Hãy hướng dẫn tôi điền hồ sơ từng bước.",
  };
  const prompt = prompts[step];
  return (
    <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
      <section className="rounded-2xl border-2 border-[#d9b2a3] bg-[#fff8f5] p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-full bg-[#903938] text-white"><Bot className="size-6" aria-hidden="true" /></span>
          <div><p className="text-sm font-bold text-[#903938]">Trợ lý đi cùng hồ sơ</p><h2 className="font-extrabold text-[#1e2f41]">Đang ở bước {step}/4</h2></div>
        </div>
        <p className="mt-4 text-sm leading-6 text-[#52606d]">Bạn có thể hỏi cách điền, ý nghĩa của từng mục hoặc nói thông tin bằng lời tự nhiên.</p>
        {missing.length ? <p className="mt-2 text-sm font-bold text-[#903938]">Còn {missing.length} mục cần hoàn thành ở bước này.</p> : null}
        <button
          className="mt-4 min-h-12 w-full rounded-xl bg-[#903938] px-4 font-extrabold text-white hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251]"
          onClick={() => window.dispatchEvent(new CustomEvent("vneguide:open-assistant", { detail: { prompt } }))}
          type="button"
        >
          Nhờ trợ lý điền cùng tôi
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

function GuidedField({ definition, showError, spotlighted }: { definition: GuidedFieldDefinition; showError: boolean; spotlighted: boolean }) {
  const workspace = useProcedureWorkspace();
  const field = workspace.state.fields[definition.field_id];
  const value = field?.value;
  const required = isBlockingRequirement(definition.requirement);
  const missing = required && (value === undefined || value === null || value === "");
  const set = (next: JsonValue) => workspace.setField(definition.field_id, next);
  const commit = () => void workspace.commitField(definition.field_id);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (spotlighted && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [spotlighted]);

  const spotlightClass = spotlighted
    ? "rounded-2xl border-2 border-[#ce7a58] bg-[#fff8f5] p-4 shadow-[0_0_0_4px_rgba(206,122,88,0.18)]"
    : "";
  const controlClass = spotlighted
    ? `${inputClass} ring-4 ring-[#ce7a58]/30 border-[#ce7a58]`
    : inputClass;
  const common = {
    "aria-invalid": showError && missing,
    className: controlClass,
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
    <div className={spotlightClass} data-field-id={definition.field_id} ref={containerRef}>
      {spotlighted ? (
        <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-[#903938] px-2 py-1 text-xs font-extrabold text-white">
          <ArrowRight className="size-3.5" aria-hidden="true" />
          Điền mục này trước nhé
        </div>
      ) : null}
      <label htmlFor={definition.field_id}><FieldLabel required={required}>{definition.label}</FieldLabel></label>
      {control}
      {spotlighted && definition.hint ? (
        <p className="mt-2 text-sm leading-5 text-[#704238]">{definition.hint}</p>
      ) : null}
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
  selectedReceptionUnit,
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
  const documentValidation = useDocumentValidation();
  const definitions = guidedFields;
  const selectedService = experience.services.find((service) => service.id === selectedServiceId);
  const [currentStep, setCurrentStep] = useState<WizardStep>(initialStep);
  const [receiptMethod, setReceiptMethod] = useState<ReceiptMethod>("counter");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [attemptedStep, setAttemptedStep] = useState<WizardStep | null>(null);
  const [submitted, setSubmitted] = useState(false);

  if (!selectedService) throw new Error("Dịch vụ công được chọn không hợp lệ.");

  const declaration = declarationGate(definitions, workspace.state.fields);
  const spotlightFieldId =
    currentStep === 1
      ? (declaration.missing[0]?.field_id ?? declaration.unconfirmed[0]?.field_id ?? null)
      : null;
  const stepMissing = {
    1: [...declaration.missing, ...declaration.unconfirmed].map((field) => field.label),
    2: documentValidation.blockingMessages,
    3: receiptMethod === "post" && !deliveryAddress.trim() ? ["Địa chỉ nhận kết quả"] : [],
    4: [],
  } satisfies Record<WizardStep, string[]>;
  const canAdvance = stepMissing[currentStep].length === 0;

  useEffect(() => {
    if (currentStep === 2) {
      window.dispatchEvent(new CustomEvent("vneguide:document-step-entered"));
    }
  }, [currentStep]);

  const moveToStep = (step: WizardStep) => {
    setCurrentStep(step);
    setAttemptedStep(null);
    setSubmitted(false);
    window.requestAnimationFrame(() => document.getElementById("guided-application")?.scrollIntoView({ behavior: "smooth", block: "start" }));
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
    if (currentStep === 1) {
      markDeclarationSaved(experience, { receptionUnit: selectedReceptionUnit, serviceId: selectedService.id });
      window.dispatchEvent(new CustomEvent("vneguide:declaration-completed"));
    }
    if (currentStep < 4) moveToStep((currentStep + 1) as WizardStep);
    else setSubmitted(true);
  };

  const content: Record<WizardStep, ReactNode> = {
    1: (
      <div className="space-y-6">
        <div className="rounded-xl border border-[#f0c36a] bg-[#fff9e8] p-4 text-sm leading-6 text-[#704d09]"><Info className="mr-2 inline size-5" aria-hidden="true" />Chỉ dùng dữ liệu giả trong bản demo. Dữ liệu do trợ lý đề xuất chỉ xuất hiện sau khi bạn bấm Chấp nhận hoặc Sửa.</div>
        {declaration.unconfirmed.length ? (
          <section className="rounded-xl border-2 border-[#f0c36a] bg-[#fff9e8] p-4">
            <h3 className="font-extrabold text-[#704d09]">Cần bạn xác nhận {declaration.unconfirmed.length} thông tin đã được điền giúp</h3>
            <ul className="mt-2 list-disc pl-5 text-sm text-[#704d09]">{declaration.unconfirmed.map((field) => <li key={field.field_id}>{field.label}</li>)}</ul>
            <button className="mt-4 min-h-12 rounded-xl bg-[#903938] px-5 font-extrabold text-white" onClick={() => void confirmAssistedFields()} type="button">Tôi đã kiểm tra, thông tin chính xác</button>
          </section>
        ) : null}
        <div className="grid gap-6 sm:grid-cols-2">{definitions.map((definition) => <GuidedField definition={definition} key={definition.field_id} showError={attemptedStep === 1} spotlighted={definition.field_id === spotlightFieldId} />)}</div>
      </div>
    ),
    2: (
      <div className="space-y-4">
        <p className="rounded-xl border border-[#b9cde5] bg-[#f2f7fc] p-4 text-sm leading-6 text-[#24496f]">OCR chỉ kiểm tra nhẹ tài liệu demo hoặc đã ẩn danh. Kết quả không xác minh chữ ký, quyền sở hữu hay giá trị pháp lý và không được gửi tới cơ quan nhà nước.</p>
        <div className="flex flex-col gap-4 rounded-xl border border-[#d9e2ec] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-extrabold text-[#1e2f41]">Tờ khai thay đổi thông tin cư trú – Mẫu CT01</p><p className="mt-1 text-sm text-[#667085]">Đã kê khai ở bước 1</p></div>
          <span className="inline-flex min-h-11 items-center rounded-xl bg-[#f1f8f3] px-4 font-bold text-[#28543a]"><Check className="mr-2 size-5" />Đã hoàn thành</span>
        </div>
        <DocumentUploadCard kind="legal_dwelling" />
        <DocumentUploadCard kind="minor_consent" />
      </div>
    ),
    3: (
      <div className="space-y-6">
        <fieldset><legend className="mb-4 text-lg font-extrabold">Bạn muốn nhận kết quả bằng cách nào?</legend><div className="grid gap-3 sm:grid-cols-3">{([['counter','Nhận trực tiếp'],['post','Qua bưu chính'],['digital','Bản điện tử']] as const).map(([id, label]) => <label className={`cursor-pointer rounded-xl border-2 p-4 font-bold ${receiptMethod === id ? "border-[#903938] bg-[#fff8f5]" : "border-[#d9e2ec]"}`} key={id}><input checked={receiptMethod === id} className="mr-2 accent-[#903938]" name="receipt" onChange={() => setReceiptMethod(id)} type="radio" />{label}</label>)}</div></fieldset>
        {receiptMethod === "post" ? <label><FieldLabel required>Địa chỉ nhận kết quả</FieldLabel><textarea aria-invalid={attemptedStep === 3 && !deliveryAddress.trim()} className={`${inputClass} min-h-24`} value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} /></label> : null}
      </div>
    ),
    4: (
      <div className="space-y-6">
        <section className="rounded-xl border border-[#d9e2ec] bg-[#f8fafc] p-5"><h3 className="font-extrabold">Kiểm tra lần cuối</h3><dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2"><div><dt className="text-[#667085]">Thủ tục</dt><dd className="mt-1 font-bold">{experience.title}</dd></div><div><dt className="text-[#667085]">Nơi tiếp nhận</dt><dd className="mt-1 font-bold">{selectedReceptionUnit}</dd></div><div><dt className="text-[#667085]">Thông tin đã xác nhận</dt><dd className="mt-1 font-bold">{Object.values(workspace.state.fields).filter((field) => field.confirmed).length}/{definitions.length}</dd></div><div><dt className="text-[#667085]">Kiểm tra tài liệu</dt><dd className="mt-1 font-bold">{documentValidation.blockingMessages.length ? "Còn nội dung cần xử lý" : "Đã đủ để hoàn tất mô phỏng"}</dd></div></dl></section>
        {submitted ? <div className="flex gap-3 rounded-xl border border-[#98d0aa] bg-[#effaf2] p-5 text-[#25633f]" role="status"><CheckCircle2 className="size-6 shrink-0" /><div><p className="font-extrabold">Đã hoàn tất bản mô phỏng hồ sơ</p><p className="mt-1 text-sm">Chưa có dữ liệu hoặc tài liệu nào được gửi tới cơ quan nhà nước.</p></div></div> : null}
      </div>
    ),
  };

  return (
    <main className="min-h-[calc(100vh-120px)] bg-[#f2f5f8] px-4 py-6 text-[#1e2f41] sm:px-6 sm:py-10">
      <div className="mx-auto max-w-7xl scroll-mt-4" id="guided-application">
        <header className="rounded-2xl bg-white p-5 shadow-sm sm:p-7"><div className="flex gap-3"><span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-[#903938] text-white"><FileText className="size-6" /></span><div><p className="text-sm font-extrabold tracking-wide text-[#903938] uppercase">Hồ sơ được trợ lý hướng dẫn</p><h1 className="mt-1 text-xl font-extrabold sm:text-2xl">{experience.title}</h1><p className="mt-2 text-sm text-[#52606d]">Nơi tiếp nhận đã chọn: <strong>{selectedReceptionUnit}</strong></p></div></div><WizardProgress currentStep={currentStep} onSelect={moveToStep} /></header>
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
