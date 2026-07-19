"use client";

import {
  AlertTriangle,
  Bot,
  ChevronDown,
  FolderHeart,
  LoaderCircle,
  MessageCircle,
  Mic,
  RefreshCw,
  Send,
  ShieldCheck,
  Square,
  Upload,
  X,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  getChatSessionContext,
  getConfirmedProcedureRoute,
  getProcedureContextByCode,
  procedureContexts,
} from "@/data/chat-scope";
import { getEnumLabel } from "@/data/guided-fields";
import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import { getChatValidationPresentation } from "@/lib/chat-presentation";
import { getChatReplyOptions } from "@/lib/chat-reply-options";
import { AUDIO_FILE_ACCEPT, mergeTranscriptIntoDraft } from "@/lib/stt";
import { getAssistantMessageOrdinals } from "@/lib/tts";
import {
  createWallet,
  INFORMATION_WALLET_KEY,
  walletValuesForProcedure,
  type InformationWallet,
} from "@/lib/information-wallet";
import type { JsonValue } from "@/types/chat";

import { MessageSpeechControls } from "./MessageSpeechControls";
import { SuggestionCard } from "./SuggestionCard";
import { useChatSession } from "./useChatSession";
import { useSpeechToText } from "./useSpeechToText";
import { useTextToSpeech } from "./useTextToSpeech";

function choiceLabel(value: JsonValue) {
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "string") return getEnumLabel(value);
  return String(value);
}

export function ChatWidget() {
  const pathname = usePathname();
  const router = useRouter();
  const context = useMemo(() => getChatSessionContext(pathname), [pathname]);
  const workspace = useProcedureWorkspace();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [selectedProcedureCode, setSelectedProcedureCode] = useState<string | null>(null);
  const [choosingProcedure, setChoosingProcedure] = useState(false);
  const [wallet, setWallet] = useState<InformationWallet | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const saved = window.sessionStorage.getItem(INFORMATION_WALLET_KEY);
      return saved ? (JSON.parse(saved) as InformationWallet) : null;
    } catch {
      return null;
    }
  });
  const [walletNotice, setWalletNotice] = useState<string | null>(null);
  const [declarationCompleted, setDeclarationCompleted] = useState(false);
  const [fieldEntry, setFieldEntry] = useState({ fieldId: "", value: "" });
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const audioFileInputRef = useRef<HTMLInputElement>(null);
  const {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    sendHiddenMessage,
    chooseFieldValue,
    resolveSuggestion,
    resetSession,
  } = useChatSession(context);
  const applyTranscript = useCallback((transcript: string) => {
    setDraft((currentDraft) => mergeTranscriptIntoDraft(currentDraft, transcript));
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }, []);
  const speech = useSpeechToText({ active: open, onTranscript: applyTranscript });
  const textToSpeech = useTextToSpeech({
    active: open,
    disabled: busy || speech.phase !== "idle",
  });
  const stopSpeaking = textToSpeech.stop;
  const assistantIndexes = useMemo(
    () => getAssistantMessageOrdinals(messages),
    [messages],
  );

  const inferredProcedure = turn?.procedure
    ? getProcedureContextByCode(turn.procedure.code)
    : undefined;
  const selectedProcedure = selectedProcedureCode
    ? getProcedureContextByCode(selectedProcedureCode)
    : inferredProcedure;
  const needsServiceConfirmation = Boolean(
    !choosingProcedure && selectedProcedure && context.procedure_code !== selectedProcedure.code,
  );

  useEffect(() => {
    if (!open) return;
    void ensureSession();
    inputRef.current?.focus();
  }, [ensureSession, open]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open, turn?.suggestions]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        stopSpeaking();
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [stopSpeaking]);

  useEffect(() => {
    stopSpeaking();
  }, [pathname, stopSpeaking]);

  useEffect(() => {
    if (busy) stopSpeaking();
  }, [busy, stopSpeaking]);

  useEffect(() => {
    stopSpeaking();
  }, [messages, stopSpeaking]);

  useEffect(() => {
    const openForStep = (event: Event) => {
      const detail = (event as CustomEvent<{ prompt?: string }>).detail;
      setOpen(true);
      if (detail?.prompt) {
        void ensureSession().then(() => sendHiddenMessage(detail.prompt ?? ""));
      }
    };
    window.addEventListener("vneguide:open-assistant", openForStep);
    return () => window.removeEventListener("vneguide:open-assistant", openForStep);
  }, [ensureSession, sendHiddenMessage]);

  useEffect(() => {
    const onDeclarationCompleted = () => {
      setDeclarationCompleted(true);
      setWalletNotice(null);
      setOpen(true);
    };
    window.addEventListener("vneguide:declaration-completed", onDeclarationCompleted);
    return () => window.removeEventListener("vneguide:declaration-completed", onDeclarationCompleted);
  }, []);

  function confirmProcedure() {
    if (!selectedProcedure) return;
    const route = getConfirmedProcedureRoute(selectedProcedure.code);
    if (!route) return;
    textToSpeech.stop();
    setOpen(false);
    setSelectedProcedureCode(null);
    setChoosingProcedure(false);
    setDeclarationCompleted(false);
    router.push(route);
  }

  async function restartSession() {
    textToSpeech.stop();
    setDeclarationCompleted(false);
    setWalletNotice(null);
    await resetSession();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy || speech.phase !== "idle") return;
    textToSpeech.stop();
    setDraft("");
    await sendMessage(message);
    inputRef.current?.focus();
  }

  const pendingSuggestions = turn?.suggestions.filter(
    (suggestion) => suggestion.status === "pending",
  );
  const validationPresentation = getChatValidationPresentation(turn);
  const replyOptions = getChatReplyOptions(turn);
  const activeMissingField =
    !declarationCompleted && !pendingSuggestions?.length && replyOptions.length === 0
      ? turn?.missing_fields[0] ?? null
      : null;
  const fixedChoiceField =
    activeMissingField?.choices.length
      ? activeMissingField
      : null;
  const freeEntryField =
    activeMissingField && activeMissingField.choices.length === 0
      ? activeMissingField
      : null;
  const fieldDraft =
    freeEntryField && fieldEntry.fieldId === freeEntryField.field_id
      ? fieldEntry.value
      : "";

  const walletCandidate = createWallet(workspace.state.fields);
  const walletAutofill = wallet
    ? walletValuesForProcedure(
        wallet,
        turn?.missing_fields.map((field) => field.field_id) ?? [],
      )
    : {};
  const canOfferWalletSave =
    declarationCompleted &&
    !wallet &&
    Object.keys(walletCandidate).length > 0 &&
    Boolean(turn?.procedure);
  const canOfferWalletAutofill = Object.keys(walletAutofill).length > 0;

  const saveSuggestedWallet = () => {
    window.sessionStorage.setItem(INFORMATION_WALLET_KEY, JSON.stringify(walletCandidate));
    setWallet(walletCandidate);
    setWalletNotice("Đã lưu trong phiên trình duyệt này. Tôi sẽ đề xuất điền lại khi gặp mục tương ứng.");
  };

  const applySuggestedWallet = () => {
    workspace.prefillFromWallet(walletAutofill);
    setWalletNotice(
      `Tôi đã điền ${Object.keys(walletAutofill).length} mục từ ví. Hãy kiểm tra trên biểu mẫu và bấm xác nhận trước khi đi tiếp.`,
    );
  };

  const submitGuidedField = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!freeEntryField || !fieldDraft.trim() || busy) return;
    const raw = fieldDraft.trim();
    let value: JsonValue = raw;
    if (freeEntryField.field_type === "integer") {
      const parsed = Number(raw);
      if (!Number.isInteger(parsed)) return;
      value = parsed;
    } else if (freeEntryField.field_type === "number") {
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) return;
      value = parsed;
    }
    setFieldEntry({ fieldId: "", value: "" });
    await chooseFieldValue(freeEntryField.field_id, value, raw);
  };
  const validationToneClass = {
    danger: "border-[#efb4b4] bg-[#fff1f1] text-[#8b1e1e]",
    incomplete: "border-[#f0c36a] bg-[#fff8df] text-[#704d09]",
    success: "border-[#b9d8c4] bg-[#f1f8f3] text-[#28543a]",
    warning: "border-[#b9cde5] bg-[#f2f7fc] text-[#24496f]",
  }[validationPresentation?.tone ?? "warning"];

  return (
    <>
      {!open ? (
        <button
          aria-label="Mở trợ lý VNeGuide"
          className="fixed right-4 bottom-4 z-[1000] flex size-16 items-center justify-center rounded-full border-4 border-white bg-[#903938] text-white shadow-[0_10px_30px_rgba(54,20,20,0.3)] transition-transform hover:scale-105 hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] sm:right-7 sm:bottom-7"
          onClick={() => setOpen(true)}
          type="button"
        >
          <MessageCircle className="size-7" aria-hidden="true" />
        </button>
      ) : null}

      {open ? (
        <section
          aria-label="Trợ lý VNeGuide"
          aria-modal="false"
          className="fixed inset-x-0 bottom-0 z-[1000] flex h-[calc(100dvh-3.5rem)] flex-col overflow-hidden border border-[#d9b2a3] bg-white shadow-2xl sm:inset-x-auto sm:right-6 sm:bottom-6 sm:h-[min(680px,calc(100dvh-3rem))] sm:w-[420px] sm:rounded-xl"
          role="dialog"
        >
          <header className="flex items-center justify-between gap-3 bg-[#903938] px-4 py-3 text-white">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white/15">
                <Bot className="size-6" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="truncate text-base font-extrabold">Trợ lý VNeGuide</h2>
                <p className="truncate text-xs text-white/80">3 thủ tục đã xác minh · Bản mô phỏng</p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <button
                aria-label="Bắt đầu lại phiên trò chuyện"
                className="flex size-10 items-center justify-center rounded-full hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white disabled:opacity-50"
                disabled={busy}
                onClick={() => void restartSession()}
                title="Bắt đầu lại"
                type="button"
              >
                <RefreshCw className="size-5" aria-hidden="true" />
              </button>
              <button
                aria-label="Thu nhỏ trợ lý"
                className="flex size-10 items-center justify-center rounded-full hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white"
                onClick={() => {
                  textToSpeech.stop();
                  setOpen(false);
                }}
                type="button"
              >
                <ChevronDown className="size-6 sm:hidden" aria-hidden="true" />
                <X className="hidden size-5 sm:block" aria-hidden="true" />
              </button>
            </div>
          </header>

          <div className="border-b border-[#ead8d0] bg-[#fff8f5] px-4 py-2 text-xs leading-5 text-[#704238]">
            <p className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              Không nhập CCCD, số điện thoại hoặc dữ liệu cá nhân thật vào bản demo.
            </p>
          </div>

          <div
            className="flex-1 space-y-3 overflow-y-auto bg-[#f7f8fa] px-4 py-4"
            ref={listRef}
          >
            {session?.scope_warning ? (
              <div className="flex items-start gap-2 rounded-lg border border-[#f0c36a] bg-[#fff8df] p-3 text-sm text-[#704d09]">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <p>{session.scope_warning}</p>
              </div>
            ) : null}

            {workspace.state.recovery_notice ? (
              <div className="rounded-lg border border-[#b9cde5] bg-[#f2f7fc] p-3 text-sm text-[#24496f]" role="status">
                {workspace.state.recovery_notice}
              </div>
            ) : null}

            {messages.length === 0 ? (
              <div className="max-w-[92%] rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 text-base leading-7 text-[#334155] shadow-sm">
                <p className="font-bold text-[#903938]">Xin chào!</p>
                <p className="mt-1">
                  Tôi có thể giúp bạn kiểm tra thông tin và chuẩn bị hồ sơ trong phạm vi đã được xác minh. Bạn đang cần hỗ trợ việc gì?
                </p>
              </div>
            ) : null}

            <div aria-live="polite" className="space-y-3">
              {messages.map((message, index) => (
                <div
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  key={`${message.role}-${index}-${message.content.slice(0, 20)}`}
                >
                  <div
                    className={`max-w-[92%] rounded-2xl px-4 py-3 text-base leading-7 shadow-sm ${
                      message.role === "user"
                        ? "rounded-tr-sm bg-[#903938] text-white"
                        : "rounded-tl-sm border border-[#e2e6ea] bg-white text-[#334155]"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    {assistantIndexes[index] !== null ? (
                      <MessageSpeechControls
                        assistantIndex={assistantIndexes[index]}
                        disabled={busy || speech.phase !== "idle"}
                        speech={textToSpeech}
                      />
                    ) : null}
                  </div>
                </div>
              ))}
            </div>

            {needsServiceConfirmation && selectedProcedure ? (
              <section
                aria-labelledby="service-confirmation-title"
                className="rounded-xl border-2 border-[#ce7a58] bg-[#fff8f5] p-4 shadow-sm"
              >
                <p className="text-xs font-extrabold tracking-wide text-[#903938] uppercase">
                  Cần xác nhận trước khi chọn nơi nộp
                </p>
                <h3 className="mt-2 text-base font-extrabold text-[#1e2f41]" id="service-confirmation-title">
                  {selectedProcedure.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[#52606d]">
                  Đây có đúng là thủ tục bạn muốn thực hiện không? Sau khi xác nhận,
                  VNeGuide sẽ mở trang chi tiết để bạn chọn tỉnh, phường/xã và cơ quan tiếp nhận.
                </p>
                <div className="mt-4 grid gap-2">
                  <button
                    className="min-h-12 rounded-lg bg-[#903938] px-4 font-extrabold text-white hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50"
                    disabled={busy}
                    onClick={() => void confirmProcedure()}
                    type="button"
                  >
                    Đúng, chọn nơi nộp hồ sơ
                  </button>
                  <button
                    className="min-h-12 rounded-lg border-2 border-[#cbd5df] bg-white px-4 font-bold text-[#334155] hover:border-[#ce7a58]"
                    disabled={busy}
                    onClick={() => {
                      setSelectedProcedureCode(null);
                      setChoosingProcedure(true);
                    }}
                    type="button"
                  >
                    Không đúng, chọn lại
                  </button>
                </div>
              </section>
            ) : null}

            {choosingProcedure ? (
              <section className="rounded-xl border border-[#d9e2ec] bg-white p-3" aria-label="Chọn thủ tục khác">
                <p className="mb-2 font-extrabold text-[#334155]">Bạn muốn làm thủ tục nào?</p>
                <div className="grid gap-2">
                  {procedureContexts.map((procedure) => (
                    <button
                      className="min-h-12 rounded-lg border-2 border-[#ce7a58] bg-[#fff8f5] px-3 py-2 text-left font-bold text-[#762b2b] hover:bg-[#ffede5]"
                      key={procedure.code}
                      onClick={() => {
                        setSelectedProcedureCode(procedure.code);
                        setChoosingProcedure(false);
                      }}
                      type="button"
                    >
                      {procedure.title}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && replyOptions.length ? (
              <div
                aria-label="Câu trả lời gợi ý"
                className="rounded-xl border border-[#d9e2ec] bg-white p-3"
                role="group"
              >
                <p className="mb-2 text-sm font-bold text-[#334155]">
                  Chọn nhanh một câu trả lời
                </p>
                <div className="grid gap-2">
                  {replyOptions.map((option) => (
                    <button
                      className="min-h-12 rounded-lg border-2 border-[#ce7a58] bg-[#fff8f5] px-4 py-2 text-left text-base font-bold text-[#762b2b] hover:bg-[#ffede5] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50"
                      disabled={busy}
                      key={option}
                      onClick={() => void sendMessage(option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && fixedChoiceField ? (
              <div
                aria-label={`Chọn ${fixedChoiceField.label}`}
                className="rounded-xl border border-[#d9e2ec] bg-white p-3"
                role="group"
              >
                <p className="mb-2 text-sm font-bold text-[#334155]">
                  Chọn {fixedChoiceField.label.toLocaleLowerCase("vi")}
                </p>
                <p className="mb-3 text-sm leading-6 text-[#5b6573]">
                  {fixedChoiceField.input_hint}
                </p>
                <div className="grid gap-2">
                  {fixedChoiceField.choices.map((choice) => {
                    const label = choiceLabel(choice);
                    return (
                      <button
                        className="min-h-12 rounded-lg border-2 border-[#ce7a58] bg-[#fff8f5] px-4 py-2 text-left text-base font-bold text-[#762b2b] hover:bg-[#ffede5] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50"
                        disabled={busy}
                        key={`${fixedChoiceField.field_id}:${JSON.stringify(choice)}`}
                        onClick={() => void chooseFieldValue(fixedChoiceField.field_id, choice, label)}
                        type="button"
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && freeEntryField ? (
              <form
                className="rounded-xl border-2 border-[#b9cde5] bg-white p-4"
                onSubmit={submitGuidedField}
              >
                <p className="text-xs font-extrabold tracking-wide text-[#24496f] uppercase">
                  Mục đang điền
                </p>
                <label
                  className="mt-1 block text-base font-extrabold text-[#1e2f41]"
                  htmlFor={`chat-field-${freeEntryField.field_id}`}
                >
                  {freeEntryField.label}
                </label>
                <p className="mt-2 text-sm leading-6 text-[#52606d]">
                  {freeEntryField.input_hint}
                </p>
                <input
                  autoComplete="off"
                  className="mt-3 min-h-12 w-full rounded-lg border-2 border-[#cbd5df] bg-white px-3 text-base text-[#1e2f41] outline-none focus:border-[#ce7a58] focus:ring-4 focus:ring-[#ce7a58]/15"
                  disabled={busy}
                  id={`chat-field-${freeEntryField.field_id}`}
                  inputMode={
                    freeEntryField.field_type === "integer" || freeEntryField.field_type === "number"
                      ? "decimal"
                      : undefined
                  }
                  onChange={(event) => setFieldEntry({
                    fieldId: freeEntryField.field_id,
                    value: event.target.value,
                  })}
                  step={freeEntryField.field_type === "integer" ? 1 : freeEntryField.field_type === "number" ? "any" : undefined}
                  type={
                    freeEntryField.field_type === "date"
                      ? "date"
                      : freeEntryField.field_type === "integer" || freeEntryField.field_type === "number"
                        ? "number"
                        : "text"
                  }
                  value={fieldDraft}
                />
                <button
                  className="mt-3 min-h-12 w-full rounded-lg bg-[#903938] px-4 font-extrabold text-white hover:bg-[#762b2b] disabled:opacity-50"
                  disabled={busy || !fieldDraft.trim()}
                  type="submit"
                >
                  Xác nhận và điền mục này
                </button>
              </form>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure ? pendingSuggestions?.map((suggestion) => (
              <SuggestionCard
                disabled={busy}
                fieldLocked={workspace.isDirty(suggestion.field_id)}
                key={suggestion.id}
                onResolve={resolveSuggestion}
                suggestion={suggestion}
              />
            )) : null}

            {!needsServiceConfirmation && !choosingProcedure && !pendingSuggestions?.length && (canOfferWalletAutofill || canOfferWalletSave) ? (
              <section className="rounded-xl border-2 border-[#b9cde5] bg-[#f2f7fc] p-4 text-[#24496f]">
                <div className="flex items-start gap-3">
                  <FolderHeart className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                  <div>
                    <p className="font-extrabold">
                      {canOfferWalletAutofill ? "Tôi có thể điền lại thông tin đã lưu" : "Bạn có muốn lưu thông tin dùng lại?"}
                    </p>
                    <p className="mt-1 text-sm leading-6">
                      {canOfferWalletAutofill
                        ? `Có ${Object.keys(walletAutofill).length} mục phù hợp. Tôi chỉ điền sau khi bạn đồng ý và bạn vẫn phải xác nhận lại.`
                        : "Chỉ lưu trong phiên trình duyệt này; không gửi thêm dữ liệu ra ngoài."}
                    </p>
                  </div>
                </div>
                <button
                  className="mt-3 min-h-11 rounded-lg bg-[#24496f] px-4 font-bold text-white hover:bg-[#183653]"
                  onClick={canOfferWalletAutofill ? applySuggestedWallet : saveSuggestedWallet}
                  type="button"
                >
                  {canOfferWalletAutofill ? "Đồng ý, điền giúp tôi" : "Đồng ý, lưu trong phiên"}
                </button>
              </section>
            ) : null}

            {walletNotice ? (
              <div className="rounded-lg border border-[#b9d8c4] bg-[#f1f8f3] p-3 text-sm text-[#28543a]" role="status">
                {walletNotice}
              </div>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && turn?.missing_fields.length ? (
              <details className="rounded-lg border border-[#d9e2ec] bg-white p-3 text-sm">
                <summary className="cursor-pointer font-bold text-[#1e2f41]">
                  Còn thiếu {turn.missing_fields.length} thông tin
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-[#5b6573]">
                  {turn.missing_fields.map((field) => (
                    <li key={field.field_id}>{field.label}</li>
                  ))}
                </ul>
              </details>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && turn?.validation && validationPresentation ? (
              <div className={`rounded-lg border p-3 text-sm ${validationToneClass}`}>
                <p className="font-bold">Trạng thái hồ sơ: {validationPresentation.label}</p>
                {validationPresentation.showReadinessScore &&
                turn.validation.readiness_score !== null ? (
                  <p className="mt-1">Mức độ sẵn sàng: {turn.validation.readiness_score}%</p>
                ) : null}
                {turn.validation.issues.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {turn.validation.issues.map((issue) => (
                      <li key={issue.rule_id}>
                        {issue.message}
                        {issue.field_id ? ` — ${issue.field_id}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            {turn?.sources.length ? (
              <details className="rounded-lg border border-[#d9e2ec] bg-white p-3 text-sm">
                <summary className="cursor-pointer font-bold text-[#1e2f41]">
                  Căn cứ tham khảo ({turn.sources.length})
                </summary>
                <ul className="mt-2 space-y-2 text-[#5b6573]">
                  {turn.sources.map((source) => (
                    <li key={source.id}>
                      <a
                        className="font-semibold text-[#903938] underline decoration-[#ce7a58] underline-offset-2"
                        href={source.url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {source.title}
                      </a>
                      <span className="block text-xs">
                        {source.publisher} · kiểm chứng {source.verified_at}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}

            {error ? (
              <div className="flex items-start gap-2 rounded-lg border border-[#efb4b4] bg-[#fff1f1] p-3 text-sm text-[#8b1e1e]" role="alert">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <p>{error}</p>
              </div>
            ) : null}

            {busy ? (
              <div className="flex items-center gap-2 text-sm text-[#667085]">
                <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
                Trợ lý đang xử lý…
              </div>
            ) : null}
          </div>

          <form className="border-t border-[#e2e6ea] bg-white p-3" onSubmit={submit}>
            <p className="mb-2 text-sm text-[#667085]">
              Bạn có thể chọn câu trả lời gợi ý hoặc nhập bằng lời của mình.
            </p>
            <input
              accept={AUDIO_FILE_ACCEPT}
              aria-label="Chọn tệp âm thanh để chuyển thành văn bản"
              className="sr-only"
              disabled={busy || speech.phase !== "idle"}
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                event.currentTarget.value = "";
                if (file) {
                  textToSpeech.stop();
                  void speech.transcribeFile(file);
                }
              }}
              ref={audioFileInputRef}
              tabIndex={-1}
              type="file"
            />
            <div className="flex items-end gap-2 rounded-xl border border-[#c9cdcf] bg-white p-2 focus-within:border-[#ce7a58] focus-within:ring-2 focus-within:ring-[#ce7a58]/20">
              <textarea
                aria-label="Nội dung cần trợ lý hỗ trợ"
                className="max-h-32 min-h-12 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-base outline-none placeholder:text-[#9299a2]"
                disabled={busy}
                maxLength={4000}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Nhập câu hỏi của bạn…"
                ref={inputRef}
                rows={1}
                value={draft}
              />
              {speech.enabled && speech.phase === "recording" ? (
                <button
                  aria-describedby="chat-stt-status"
                  aria-label="Dừng ghi âm và chuyển thành văn bản"
                  aria-pressed="true"
                  className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#a12f2f] text-white hover:bg-[#842525] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  onClick={speech.stopRecording}
                  title="Dừng ghi âm"
                  type="button"
                >
                  <Square className="size-4 fill-current" aria-hidden="true" />
                </button>
              ) : speech.enabled && speech.canRecord ? (
                <button
                  aria-describedby="chat-stt-status"
                  aria-label="Bắt đầu nhập bằng giọng nói"
                  className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-[#c9cdcf] bg-white text-[#704238] hover:border-[#ce7a58] hover:bg-[#fff8f5] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={busy || speech.phase !== "idle"}
                  onClick={() => {
                    textToSpeech.stop();
                    void speech.startRecording();
                  }}
                  title="Nhập bằng giọng nói"
                  type="button"
                >
                  <Mic className="size-5" aria-hidden="true" />
                </button>
              ) : null}
              {speech.enabled ? (
                <button
                  aria-describedby="chat-stt-status"
                  aria-label="Chọn tệp âm thanh để chuyển thành văn bản"
                  className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-[#c9cdcf] bg-white text-[#704238] hover:border-[#ce7a58] hover:bg-[#fff8f5] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={busy || speech.phase !== "idle"}
                  onClick={() => {
                    textToSpeech.stop();
                    audioFileInputRef.current?.click();
                  }}
                  title="Chọn tệp âm thanh"
                  type="button"
                >
                  <Upload className="size-5" aria-hidden="true" />
                </button>
              ) : null}
              <button
                aria-label="Gửi tin nhắn"
                className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy || speech.phase !== "idle" || !draft.trim()}
                type="submit"
              >
                <Send className="size-5" aria-hidden="true" />
              </button>
            </div>
            <div
              aria-live="polite"
              className="mt-2 min-h-5 text-xs leading-5 text-[#667085]"
              id="chat-stt-status"
            >
              {speech.checking
                ? "Đang kiểm tra tính năng nhập bằng giọng nói…"
                : speech.enabled && speech.phase === "requesting"
                  ? "Đang chờ quyền sử dụng mic…"
                  : speech.enabled && speech.phase === "recording"
                    ? `Đang ghi âm. Bản ghi sẽ tự dừng sau tối đa ${speech.maxDurationSeconds} giây.`
                    : speech.enabled && speech.phase === "transcribing"
                      ? "Đang chuyển giọng nói thành văn bản…"
                      : speech.enabled && !speech.microphoneSupported && speech.phase === "idle"
                        ? "Mic không khả dụng tại địa chỉ này; bạn vẫn có thể chọn một tệp âm thanh."
                        : null}
            </div>
            {speech.error ? (
              <div
                className="mt-1 flex items-start gap-2 rounded-lg border border-[#efb4b4] bg-[#fff1f1] p-2 text-xs leading-5 text-[#8b1e1e]"
                role="alert"
              >
                <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <p>{speech.error}</p>
              </div>
            ) : null}
          </form>
        </section>
      ) : null}
    </>
  );
}
