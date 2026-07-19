"use client";

import { LoaderCircle, Pause, Play, RotateCcw, Square, Volume2 } from "lucide-react";

import type { TextToSpeechController } from "./useTextToSpeech";

interface MessageSpeechControlsProps {
  assistantIndex: number;
  disabled: boolean;
  speech: TextToSpeechController;
}

export function MessageSpeechControls({
  assistantIndex,
  disabled,
  speech,
}: MessageSpeechControlsProps) {
  if (!speech.enabled) return null;

  const isActive = speech.activeAssistantIndex === assistantIndex;
  const phase = isActive ? speech.phase : "idle";
  const messageError = speech.error?.assistantIndex === assistantIndex
    ? speech.error.message
    : null;
  const isBusy = phase === "loading";
  const showStop = isActive && ["loading", "playing", "paused"].includes(phase);

  const primary = {
    completed: {
      action: () => void speech.play(assistantIndex),
      icon: RotateCcw,
      label: "Nghe lại",
    },
    idle: {
      action: () => void speech.play(assistantIndex),
      icon: Volume2,
      label: "Nghe",
    },
    loading: {
      action: () => undefined,
      icon: LoaderCircle,
      label: "Đang tạo…",
    },
    paused: {
      action: () => void speech.resume(),
      icon: Play,
      label: "Tiếp tục",
    },
    playing: {
      action: speech.pause,
      icon: Pause,
      label: "Tạm dừng",
    },
  }[phase];
  const PrimaryIcon = primary.icon;

  return (
    <div
      aria-busy={isBusy}
      className="mt-2 border-t border-[#e8ecef] pt-2 text-xs leading-5 text-[#667085]"
    >
      <div className="flex flex-wrap items-center gap-2">
        <button
          aria-label={`${primary.label} câu trả lời này`}
          aria-pressed={phase === "playing"}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-[#c9cdcf] bg-white px-2.5 font-semibold text-[#704238] hover:border-[#ce7a58] hover:bg-[#fff8f5] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled || isBusy}
          onClick={primary.action}
          type="button"
        >
          <PrimaryIcon
            aria-hidden="true"
            className={`size-4 ${isBusy ? "animate-spin" : ""}`}
          />
          {primary.label}
        </button>
        {showStop ? (
          <button
            aria-label="Dừng đọc câu trả lời này"
            className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2.5 font-semibold text-[#8b1e1e] hover:bg-[#fff1f1] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
            onClick={speech.stop}
            type="button"
          >
            <Square aria-hidden="true" className="size-3 fill-current" />
            Dừng
          </button>
        ) : null}
        <span>Giọng đọc do AI tạo; nội dung sẽ được gửi tới dịch vụ tạo giọng nói.</span>
      </div>
      {isActive ? (
        <span aria-live="polite" className="sr-only">
          {phase === "loading"
            ? "Đang tạo giọng đọc tiếng Việt."
            : phase === "playing"
              ? "Đang đọc câu trả lời."
              : phase === "paused"
                ? "Đã tạm dừng giọng đọc."
                : phase === "completed"
                  ? "Đã đọc xong câu trả lời."
                  : "Đã dừng giọng đọc."}
        </span>
      ) : null}
      {messageError ? (
        <p className="mt-1 text-[#8b1e1e]" role="alert">
          {messageError}
        </p>
      ) : null}
    </div>
  );
}
