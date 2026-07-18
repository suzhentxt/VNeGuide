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

import { getChatSessionContext } from "@/data/chat-scope";
import { useProcedureWorkspace } from "@/components/workspace/ProcedureWorkspaceProvider";

import { SuggestionCard } from "./SuggestionCard";
import { useChatSession } from "./useChatSession";

export function ChatWidget() {
  const pathname = usePathname();
  const context = useMemo(() => getChatSessionContext(pathname), [pathname]);
  const workspace = useProcedureWorkspace();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const {
    session,
    turn,
    messages,
    error,
    busy,
    ensureSession,
    sendMessage,
    resolveSuggestion,
    resetSession,
  } = useChatSession(context);

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
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

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
  const contextChanged = Boolean(
    session?.context?.procedure_code &&
      context.procedure_code &&
      session.context.procedure_code !== context.procedure_code,
  );

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
                <p>
                  Phiên hiện tại đang gắn với “{session?.context?.procedure_title}”. Bạn đã chuyển sang “{context.procedure_title}”.
                </p>
                <button
                  className="mt-2 min-h-10 rounded-md bg-[#24496f] px-3 font-bold text-white hover:bg-[#183653] disabled:opacity-50"
                  disabled={busy}
                  onClick={() => void resetSession()}
                  type="button"
                >
                  Bắt đầu phiên cho trang này
                </button>
              </div>
            ) : null}

            {workspace.state.recovery_notice ? (
              <div className="rounded-lg border border-[#b9cde5] bg-[#f2f7fc] p-3 text-sm text-[#24496f]" role="status">
                {workspace.state.recovery_notice}
              </div>
            ) : null}

            {messages.length === 0 ? (
              <div className="max-w-[92%] rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 text-sm leading-6 text-[#334155] shadow-sm">
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
                disabled={busy}
                fieldLocked={workspace.isDirty(suggestion.field_id)}
                key={suggestion.id}
                onResolve={resolveSuggestion}
                suggestion={suggestion}
              />
            ))}

            {turn?.missing_fields.length ? (
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

            {turn?.validation ? (
              <div className="rounded-lg border border-[#b9d8c4] bg-[#f1f8f3] p-3 text-sm text-[#28543a]">
                <p className="font-bold">Trạng thái: {turn.validation.status}</p>
                {turn.validation.readiness_score !== null ? (
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
            <div className="flex items-end gap-2 rounded-xl border border-[#c9cdcf] bg-white p-2 focus-within:border-[#ce7a58] focus-within:ring-2 focus-within:ring-[#ce7a58]/20">
              <textarea
                aria-label="Nội dung cần trợ lý hỗ trợ"
                className="max-h-32 min-h-11 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-[#9299a2]"
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
          </form>
        </section>
      ) : null}
    </>
  );
}
