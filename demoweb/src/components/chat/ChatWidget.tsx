"use client";

import {
  AlertTriangle,
  Bot,
  ChevronDown,
  LoaderCircle,
  MessageCircle,
  RefreshCw,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  getChatSessionContext,
  shouldRebindChatWorkspace,
  shouldRebindChatSession,
} from "@/data/chat-scope";
import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";
import {
  getChatStatusPresentation,
  getReviewedSourceHref,
} from "@/lib/chat-status-presentation";

import { SuggestionCard } from "./SuggestionCard";
import { useChatSession } from "./useChatSession";

const CHAT_STATUS_TONE_CLASSES = {
  danger: "border-[#efb4b4] bg-[#fff1f1] text-[#8b1e1e]",
  warning: "border-[#f0c36a] bg-[#fff8df] text-[#704d09]",
  info: "border-[#b9cde5] bg-[#f2f7fc] text-[#24496f]",
  success: "border-[#b9d8c4] bg-[#f1f8f3] text-[#28543a]",
} as const;

export function ChatWidget() {
  const pathname = usePathname();
  const context = useMemo(() => getChatSessionContext(pathname), [pathname]);
  const workspace = useProcedureWorkspace();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const switchSessionRef = useRef<HTMLButtonElement>(null);
  const retryConnectionRef = useRef<HTMLButtonElement>(null);
  const wasOpenRef = useRef(false);
  const {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    resolveSuggestion,
    rebindSession,
    resetSession,
  } = useChatSession(context);
  const scopeChanged = shouldRebindChatSession(
    session ? session.context : undefined,
    context,
  );
  const revisionChanged = Boolean(
    session &&
      !scopeChanged &&
      shouldRebindChatWorkspace(
        turn?.draft ?? session.draft,
        context,
        workspace.state,
      ),
  );
  const contextChanged = scopeChanged || revisionChanged;
  const sessionReady = Boolean(session) && !contextChanged;
  const visibleTurn = sessionReady ? turn : null;
  const visibleMessages = sessionReady ? messages : [];
  const statusPresentation = visibleTurn
    ? getChatStatusPresentation(visibleTurn)
    : null;
  const formSyncing = Object.values(workspace.state.fields).some(
    (field) => field.sync_status === "saving",
  );

  useEffect(() => {
    if (open) {
      void ensureSession();
      panelRef.current?.focus();
    } else if (wasOpenRef.current) {
      launcherRef.current?.focus();
    }
    wasOpenRef.current = open;
  }, [ensureSession, open]);

  useEffect(() => {
    if (!open || busy) return;
    if (contextChanged) switchSessionRef.current?.focus();
    else if (sessionReady) inputRef.current?.focus();
    else if (error) retryConnectionRef.current?.focus();
    else panelRef.current?.focus();
  }, [busy, contextChanged, error, open, sessionReady]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open, sessionReady, turn?.suggestions]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (
        event.key === "Escape" &&
        open &&
        panelRef.current?.contains(document.activeElement)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy || !sessionReady) return;
    setDraft("");
    await sendMessage(message);
    inputRef.current?.focus();
  }

  const pendingSuggestions = visibleTurn?.suggestions.filter(
    (suggestion) => suggestion.status === "pending",
  );
  return (
    <>
      {!open ? (
        <button
          aria-label="Mở trợ lý VNeGuide"
          aria-controls="vneguide-chat-panel"
          aria-haspopup="dialog"
          className="fixed right-4 bottom-4 z-[80] flex size-16 items-center justify-center rounded-full border-4 border-white bg-[#903938] text-white shadow-[0_10px_30px_rgba(54,20,20,0.3)] transition-transform hover:scale-105 hover:bg-[#762b2b] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] sm:right-7 sm:bottom-7"
          onClick={() => setOpen(true)}
          ref={launcherRef}
          type="button"
        >
          <MessageCircle className="size-7" aria-hidden="true" />
        </button>
      ) : null}

      {open ? (
        <section
          aria-label="Trợ lý VNeGuide"
          aria-modal="false"
          className="fixed inset-x-0 top-[7.5rem] bottom-0 z-[80] flex flex-col overflow-hidden border border-[#d9b2a3] bg-white shadow-2xl sm:inset-x-auto sm:top-auto sm:right-6 sm:bottom-6 sm:h-[min(680px,calc(100dvh-6rem))] sm:w-[420px] sm:rounded-xl"
          id="vneguide-chat-panel"
          ref={panelRef}
          role="dialog"
          tabIndex={-1}
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
                disabled={busy || !sessionReady || formSyncing}
                onClick={() => void resetSession()}
                title="Bắt đầu lại"
                type="button"
              >
                <RefreshCw className="size-5" aria-hidden="true" />
              </button>
              <button
                aria-label="Thu nhỏ trợ lý"
                className="flex size-10 items-center justify-center rounded-full hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white"
                onClick={() => setOpen(false)}
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

            {contextChanged ? (
              <div className="rounded-lg border border-[#b9cde5] bg-[#f2f7fc] p-3 text-sm text-[#24496f]">
                {scopeChanged ? (
                  <p>
                    Phiên hiện tại đang gắn với “{session?.context?.procedure_title ?? "phạm vi chung"}”. Bạn đã chuyển sang “{context.procedure_title}”.
                  </p>
                ) : (
                  <p>
                    Biểu mẫu đang có dữ liệu từ một phiên khác. Hãy tạo phiên mới để giữ dữ liệu trên form và đồng bộ an toàn.
                  </p>
                )}
                <button
                  className="mt-2 min-h-10 rounded-md bg-[#24496f] px-3 font-bold text-white hover:bg-[#183653] disabled:opacity-50"
                  disabled={busy || formSyncing}
                  onClick={() => void rebindSession()}
                  ref={switchSessionRef}
                  type="button"
                >
                  {formSyncing
                    ? "Đang đồng bộ biểu mẫu…"
                    : "Bắt đầu phiên cho trang này"}
                </button>
              </div>
            ) : null}

            {workspace.state.recovery_notice ? (
              <div className="rounded-lg border border-[#b9cde5] bg-[#f2f7fc] p-3 text-sm text-[#24496f]" role="status">
                {workspace.state.recovery_notice}
              </div>
            ) : null}

            {visibleMessages.length === 0 ? (
              <div className="max-w-[92%] rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 text-sm leading-6 text-[#334155] shadow-sm">
                <p className="font-bold text-[#903938]">Xin chào!</p>
                <p className="mt-1">
                  Tôi có thể giúp bạn kiểm tra thông tin và chuẩn bị hồ sơ trong phạm vi đã được xác minh. Bạn đang cần hỗ trợ việc gì?
                </p>
              </div>
            ) : null}

            <div aria-live="polite" className="space-y-3">
              {visibleMessages.map((message, index) => (
                <div
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  key={`${message.role}-${index}-${message.content.slice(0, 20)}`}
                >
                  <div
                    className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
                      message.role === "user"
                        ? "rounded-tr-sm bg-[#903938] text-white"
                        : "rounded-tl-sm border border-[#e2e6ea] bg-white text-[#334155]"
                    }`}
                  >
                    {message.content}
                  </div>
                </div>
              ))}
            </div>

            {pendingSuggestions?.map((suggestion) => (
              <SuggestionCard
                disabled={busy || !sessionReady || formSyncing}
                fieldLocked={workspace.isDirty(suggestion.field_id)}
                key={suggestion.id}
                onResolve={resolveSuggestion}
                suggestion={suggestion}
              />
            ))}

            {visibleTurn?.missing_fields.length ? (
              <details className="rounded-lg border border-[#d9e2ec] bg-white p-3 text-sm">
                <summary className="cursor-pointer font-bold text-[#1e2f41]">
                  Còn thiếu {visibleTurn.missing_fields.length} thông tin
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-[#5b6573]">
                  {visibleTurn.missing_fields.map((field) => (
                    <li key={field.field_id}>{field.label}</li>
                  ))}
                </ul>
              </details>
            ) : null}

            {statusPresentation && visibleTurn ? (
              <div
                className={`rounded-lg border p-3 text-sm ${CHAT_STATUS_TONE_CLASSES[statusPresentation.tone]}`}
              >
                <p className="font-bold">Trạng thái: {statusPresentation.label}</p>
                {statusPresentation.readinessScore !== null ? (
                  <p className="mt-1">
                    Mức độ sẵn sàng: {statusPresentation.readinessScore}%
                  </p>
                ) : null}
                {visibleTurn.validation?.issues.length ? (
                  <div className="mt-2">
                    <p className="font-semibold">Kết quả kiểm tra</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5">
                      {visibleTurn.validation.issues.map((issue) => (
                        <li key={issue.rule_id}>{issue.message}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}

            {visibleTurn?.sources.length ? (
              <details className="rounded-lg border border-[#d9e2ec] bg-white p-3 text-sm">
                <summary className="cursor-pointer font-bold text-[#1e2f41]">
                  Căn cứ tham khảo ({visibleTurn.sources.length})
                </summary>
                <ul className="mt-2 space-y-2 text-[#5b6573]">
                  {visibleTurn.sources.map((source) => {
                    const href = getReviewedSourceHref(source.url);
                    return (
                      <li key={source.id}>
                        {href ? (
                          <a
                            className="font-semibold text-[#903938] underline decoration-[#ce7a58] underline-offset-2"
                            href={href}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {source.title}
                          </a>
                        ) : (
                          <span className="font-semibold text-[#903938]">
                            {source.title}
                          </span>
                        )}
                        <span className="block text-xs">
                          {source.publisher} · kiểm chứng {source.verified_at}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </details>
            ) : null}

            {error ? (
              <div className="flex items-start gap-2 rounded-lg border border-[#efb4b4] bg-[#fff1f1] p-3 text-sm text-[#8b1e1e]" role="alert">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <div>
                  <p>{error}</p>
                  {!session && !busy ? (
                    <button
                      className="mt-2 min-h-10 rounded-md border border-[#8b1e1e] px-3 font-bold hover:bg-[#ffe1e1]"
                      onClick={() => void ensureSession()}
                      ref={retryConnectionRef}
                      type="button"
                    >
                      Thử kết nối lại
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}

            {busy ? (
              <div className="flex items-center gap-2 text-sm text-[#667085]" role="status">
                <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
                Trợ lý đang xử lý…
              </div>
            ) : null}
          </div>

          <form className="border-t border-[#e2e6ea] bg-white p-3" onSubmit={submit}>
            <div className="flex items-end gap-2 rounded-xl border border-[#c9cdcf] bg-white p-2 focus-within:border-[#ce7a58] focus-within:ring-2 focus-within:ring-[#ce7a58]/20">
              <textarea
                aria-label="Nội dung cần trợ lý hỗ trợ"
                className="max-h-32 min-h-11 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-[#9299a2]"
                disabled={busy || !sessionReady}
                maxLength={4000}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.nativeEvent.isComposing) return;
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder={
                  contextChanged
                    ? "Hãy bắt đầu phiên cho trang này trước khi gửi…"
                    : !session
                      ? "Đang kết nối tới trợ lý…"
                    : "Nhập câu hỏi của bạn…"
                }
                ref={inputRef}
                rows={1}
                value={draft}
              />
              <button
                aria-label="Gửi tin nhắn"
                className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy || !sessionReady || !draft.trim()}
                type="submit"
              >
                <Send className="size-5" aria-hidden="true" />
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </>
  );
}
