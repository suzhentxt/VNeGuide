"use client";

import { Dialog } from "@base-ui/react/dialog";
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  FolderHeart,
  MessageCircle,
  RefreshCw,
  RotateCw,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

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
import {
  createWallet,
  INFORMATION_WALLET_KEY,
  walletValuesForProcedure,
  type InformationWallet,
} from "@/lib/information-wallet";
import type { JsonValue } from "@/types/chat";

import { BotMessage } from "./BotMessage";
import { ChatSection } from "./ChatSection";
import { SuggestionCard } from "./SuggestionCard";
import { TypingIndicator } from "./TypingIndicator";
import { useChatSession } from "./useChatSession";
import { toast } from "@/components/ui/sonner";
import { Skeleton } from "@/components/ui/skeleton";

const QUICK_START_CHIPS = [
  "Tôi muốn tra cứu thủ tục",
  "Hỏi căn cứ pháp lý và lệ phí",
  "Kiểm tra hồ sơ cần chuẩn bị",
];

const CHAT_OPEN_KEY = "vneguide:chat-open";

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
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.sessionStorage.getItem(CHAT_OPEN_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [closing, setClosing] = useState(false);
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
  const [declarationCompleted, setDeclarationCompleted] = useState(false);
  const [fieldEntry, setFieldEntry] = useState({ fieldId: "", value: "" });
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const {
    session,
    turn,
    messages,
    error,
    busy,
    lastUserMessage,
    ensureSession,
    sendMessage,
    sendHiddenMessage,
    chooseFieldValue,
    resolveSuggestion,
    resetSession,
    retryLastMessage,
  } = useChatSession(context);

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
    try {
      if (open) window.sessionStorage.setItem(CHAT_OPEN_KEY, "1");
      else window.sessionStorage.removeItem(CHAT_OPEN_KEY);
    } catch {
      // sessionStorage có thể bị chặn (riêng tư) — bỏ qua.
    }
  }, [open]);

  const [showJumpToNew, setShowJumpToNew] = useState(false);
  const isNearBottomRef = useRef(true);

  useEffect(() => {
    if (!open) return;
    const list = listRef.current;
    if (!list) return;
    if (isNearBottomRef.current) {
      list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
      setShowJumpToNew(false);
    } else {
      setShowJumpToNew(true);
    }
  }, [messages, open, turn?.suggestions]);

  function handleListScroll() {
    const list = listRef.current;
    if (!list) return;
    const distanceFromBottom = list.scrollHeight - list.scrollTop - list.clientHeight;
    const nearBottom = distanceFromBottom < 80;
    isNearBottomRef.current = nearBottom;
    if (nearBottom) setShowJumpToNew(false);
  }

  function jumpToNew() {
    const list = listRef.current;
    if (!list) return;
    isNearBottomRef.current = true;
    list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
    setShowJumpToNew(false);
  }

  function closePanel() {
    if (closing || !open) return;
    setClosing(true);
    window.setTimeout(() => {
      setOpen(false);
      setClosing(false);
    }, 200);
  }

  useEffect(() => {
    const notice = workspace.state.recovery_notice;
    if (notice) toast.info(notice, { duration: 4000 });
  }, [workspace.state.recovery_notice]);

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
      setOpen(true);
    };
    window.addEventListener("vneguide:declaration-completed", onDeclarationCompleted);
    return () => window.removeEventListener("vneguide:declaration-completed", onDeclarationCompleted);
  }, []);

  function confirmProcedure() {
    if (!selectedProcedure) return;
    const route = getConfirmedProcedureRoute(selectedProcedure.code);
    if (!route) return;
    setOpen(false);
    setSelectedProcedureCode(null);
    setChoosingProcedure(false);
    setDeclarationCompleted(false);
    router.push(route);
  }

  async function restartSession() {
    setDeclarationCompleted(false);
    await resetSession();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy) return;
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
    toast.success("Đã lưu trong phiên trình duyệt này. Tôi sẽ đề xuất điền lại khi gặp mục tương ứng.");
  };

  const applySuggestedWallet = () => {
    workspace.prefillFromWallet(walletAutofill);
    toast.success(
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
      {!open && !closing ? (
        <button
          aria-label="Mở trợ lý VNeGuide"
          className="fixed right-4 bottom-4 z-[1000] flex size-16 animate-in fade-in zoom-in-50 items-center justify-center rounded-full border-4 border-white bg-[#903938] text-white shadow-[0_10px_30px_rgba(54,20,20,0.3)] transition-transform hover:scale-105 hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] sm:right-7 sm:bottom-7"
          onClick={() => setOpen(true)}
          type="button"
        >
          <MessageCircle className="size-7" aria-hidden="true" />
          {pendingSuggestions?.length ? (
            <span className="absolute -top-1 -right-1 flex size-6 animate-in zoom-in-50 items-center justify-center rounded-full border-2 border-white bg-[#ffc251] text-xs font-extrabold text-[#1e2f41]">
              {pendingSuggestions.length}
            </span>
          ) : null}
        </button>
      ) : null}

      {open ? (
        <Dialog.Root
          open={open}
          onOpenChange={(next) => {
            if (!next) closePanel();
          }}
          modal="trap-focus"
          disablePointerDismissal
        >
          <Dialog.Portal>
          <Dialog.Popup
            aria-label="Trợ lý VNeGuide"
            className={`fixed inset-x-0 bottom-0 z-[1000] flex h-[calc(100dvh-3.5rem)] flex-col overflow-hidden border border-[#d9b2a3] bg-white shadow-2xl sm:inset-x-auto sm:right-6 sm:bottom-6 sm:h-[min(700px,calc(100dvh-3rem))] sm:w-[460px] sm:rounded-xl md:w-[500px] lg:h-[min(760px,calc(100dvh-3rem))] lg:w-[540px] xl:w-[580px] ${
              closing
                ? "animate-out slide-out-to-bottom-full sm:fade-out sm:zoom-out-95"
                : "animate-in slide-in-from-bottom-full sm:fade-in sm:zoom-in-95"
            }`}
            initialFocus={inputRef}
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
                onClick={() => closePanel()}
                type="button"
              >
                <ChevronDown className="size-6 sm:hidden" aria-hidden="true" />
                <X className="hidden size-5 sm:block" aria-hidden="true" />
              </button>
            </div>
          </header>

          {messages.length === 0 ? (
            <div className="border-b border-[#ead8d0] bg-[#fff8f5] px-4 py-2 text-xs leading-5 text-[#704238]">
              <p className="flex items-start gap-2">
                <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                Không nhập CCCD, số điện thoại hoặc dữ liệu cá nhân thật vào bản demo.
              </p>
            </div>
          ) : null}

          <div
            className="flex-1 space-y-3 overflow-y-auto bg-[#f7f8fa] px-4 py-4"
            onScroll={handleListScroll}
            ref={listRef}
          >
            {session?.scope_warning ? (
              <div className="flex items-start gap-2 rounded-lg border border-[#f0c36a] bg-[#fff8df] p-3 text-sm text-[#704d09]">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <p>{session.scope_warning}</p>
              </div>
            ) : null}

            {busy && !session && messages.length === 0 ? (
              <div className="space-y-3" aria-busy="true" aria-label="Đang kết nối trợ lý">
                <div className="max-w-[92%] space-y-2 rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 shadow-sm">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              </div>
            ) : null}

            {!busy && messages.length === 0 ? (
              <div className="space-y-3">
                <div className="max-w-[92%] rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 text-base leading-7 text-[#334155] shadow-sm">
                  <p className="font-bold text-[#903938]">Xin chào!</p>
                  <p className="mt-1">
                    Tôi có thể giúp bạn kiểm tra thông tin và chuẩn bị hồ sơ trong phạm vi đã được xác minh. Bạn đang cần hỗ trợ việc gì?
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {QUICK_START_CHIPS.map((chip) => (
                    <button
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-full border-2 border-[#ce7a58] bg-[#fff8f5] px-3 py-1.5 text-sm font-bold text-[#762b2b] shadow-sm transition-colors hover:bg-[#ffede5] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50"
                      disabled={busy}
                      key={chip}
                      onClick={() => void sendMessage(chip)}
                      type="button"
                    >
                      <Sparkles className="size-3.5" aria-hidden="true" />
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div aria-live="polite" className="space-y-3">
              {messages.map((message, index) => {
                const time = message.created_at
                  ? new Date(message.created_at).toLocaleTimeString("vi", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : null;
                return (
                  <div
                    className={`flex animate-in fade-in slide-in-from-bottom-1 duration-200 flex-col ${message.role === "user" ? "items-end" : "items-start"}`}
                    key={`${message.role}-${index}`}
                  >
                    {message.role === "user" ? (
                      <div className="max-w-[92%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-[#903938] px-4 py-3 text-base leading-7 text-white shadow-sm">
                        {message.content}
                      </div>
                    ) : (
                      <BotMessage content={message.content} sources={turn?.sources} />
                    )}
                    {time ? (
                      <time className="mt-0.5 px-1 text-[10px] text-[#9299a2]">{time}</time>
                    ) : null}
                  </div>
                );
              })}
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
              <ChatSection ariaLabel="Chọn thủ tục khác" label="Bạn muốn làm thủ tục nào?">
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
              </ChatSection>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && replyOptions.length ? (
              <ChatSection ariaLabel="Câu trả lời gợi ý" label="Chọn nhanh một câu trả lời">
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
              </ChatSection>
            ) : null}

            {!needsServiceConfirmation && !choosingProcedure && fixedChoiceField ? (
              <ChatSection
                ariaLabel={`Chọn ${fixedChoiceField.label}`}
                label={`Chọn ${fixedChoiceField.label.toLocaleLowerCase("vi")}`}
              >
                <p className="text-sm leading-6 text-[#52606d]">
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
              </ChatSection>
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
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-xs">
                      <span>Mức độ sẵn sàng</span>
                      <span className="font-bold">{turn.validation.readiness_score}%</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full bg-[#e2e6ea]">
                      <div
                        className="h-2 rounded-full bg-[#ce7a58] transition-all duration-300"
                        style={{ width: `${turn.validation.readiness_score}%` }}
                      />
                    </div>
                  </div>
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

            {error ? (
              <div className="flex items-start gap-2 rounded-lg border border-[#efb4b4] bg-[#fff1f1] p-3 text-sm text-[#8b1e1e]" role="alert">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <div className="flex-1">
                  <p>{error}</p>
                  {lastUserMessage ? (
                    <button
                      className="mt-2 inline-flex min-h-9 items-center gap-1.5 rounded-md border border-[#efb4b4] bg-white px-3 text-sm font-bold text-[#8b1e1e] hover:bg-[#fff8f8] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] disabled:opacity-50"
                      disabled={busy}
                      onClick={() => retryLastMessage()}
                      type="button"
                    >
                      <RotateCw className="size-4" aria-hidden="true" />
                      Thử lại
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}

            {busy ? <TypingIndicator /> : null}

            {showJumpToNew ? (
              <button
                className="sticky bottom-2 mx-auto flex min-h-9 animate-in fade-in slide-in-from-bottom-2 items-center gap-1.5 rounded-full border border-[#d9b2a3] bg-[#903938] px-4 text-sm font-bold text-white shadow-lg hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251]"
                onClick={jumpToNew}
                type="button"
              >
                <ChevronDown className="size-4 animate-bounce" aria-hidden="true" />
                Tin mới
              </button>
            ) : null}
          </div>

          <form className="border-t border-[#e2e6ea] bg-white p-3" onSubmit={submit}>
            <p className="mb-2 text-sm text-[#667085]">
              Bạn có thể chọn câu trả lời gợi ý hoặc nhập bằng lời của mình.
            </p>
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
              <button
                aria-label="Gửi tin nhắn"
                className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy || !draft.trim()}
                type="submit"
              >
                <Send className="size-5" aria-hidden="true" />
              </button>
            </div>
            {draft.length > 0 ? (
              <p className={`mt-1 text-right text-xs ${draft.length > 3500 ? "text-[#8b1e1e]" : "text-[#9299a2]"}`}>
                {draft.length}/4000
              </p>
            ) : null}
          </form>
          </Dialog.Popup>
          </Dialog.Portal>
        </Dialog.Root>
      ) : null}
    </>
  );
}
