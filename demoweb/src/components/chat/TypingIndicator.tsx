"use client";

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        aria-label="Trợ lý đang nhập"
        className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 shadow-sm"
      >
        <span className="size-2 animate-bounce rounded-full bg-[#ce7a58] [animation-delay:-0.3s]" />
        <span className="size-2 animate-bounce rounded-full bg-[#ce7a58] [animation-delay:-0.15s]" />
        <span className="size-2 animate-bounce rounded-full bg-[#ce7a58]" />
      </div>
    </div>
  );
}
