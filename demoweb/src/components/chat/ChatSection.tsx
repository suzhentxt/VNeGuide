"use client";

import type { ComponentType, ReactNode } from "react";

type Tone = "default" | "accent" | "danger" | "success" | "warning";

const TONE_STYLES: Record<Tone, { box: string; label: string }> = {
  default: {
    box: "border-[#d9e2ec] bg-white",
    label: "text-[#334155]",
  },
  accent: {
    box: "border-2 border-[#ce7a58] bg-[#fff8f5]",
    label: "text-[#903938]",
  },
  danger: {
    box: "border-[#efb4b4] bg-[#fff1f1]",
    label: "text-[#8b1e1e]",
  },
  success: {
    box: "border-[#b9d8c4] bg-[#f1f8f3]",
    label: "text-[#28543a]",
  },
  warning: {
    box: "border-2 border-[#b9cde5] bg-[#f2f7fc]",
    label: "text-[#24496f]",
  },
};

interface ChatSectionProps {
  label?: string;
  icon?: ComponentType<{ className?: string }>;
  tone?: Tone;
  bordered?: boolean;
  ariaLabel?: string;
  children: ReactNode;
}

export function ChatSection({
  label,
  icon: Icon,
  tone = "default",
  bordered = true,
  ariaLabel,
  children,
}: ChatSectionProps) {
  const styles = TONE_STYLES[tone];
  return (
    <section
      aria-label={ariaLabel}
      className={`rounded-xl p-3 shadow-sm ${bordered ? `border ${styles.box}` : ""} ${label ? "space-y-2" : ""}`}
    >
      {label ? (
        <p
          className={`flex items-center gap-1.5 text-xs font-extrabold tracking-wide uppercase ${styles.label}`}
        >
          {Icon ? <Icon className="size-4 shrink-0" /> : null}
          {label}
        </p>
      ) : null}
      {children}
    </section>
  );
}
