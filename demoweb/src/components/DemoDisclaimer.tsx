"use client";

import { X } from "lucide-react";
import { useState } from "react";

const DISMISS_KEY = "vneguide:disclaimer-dismissed";

export function DemoDisclaimer() {
  const [dismissed, setDismissed] = useState(() =>
    typeof window !== "undefined"
      ? sessionStorage.getItem(DISMISS_KEY) === "1"
      : false,
  );

  if (dismissed) return null;

  return (
    <aside
      aria-label="Cảnh báo bản mô phỏng"
      className="relative z-[1001] border-b-2 border-[#991b1b] bg-[#fff4c2] px-4 py-2.5 text-[#7f1d1d] shadow-sm"
      data-demo-disclaimer
    >
      <div className="mx-auto flex w-full max-w-[1440px] items-start justify-center gap-2.5 pr-8 text-sm leading-5 sm:items-center sm:text-base">
        <span
          aria-hidden="true"
          className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-[#991b1b] text-sm font-extrabold text-white sm:mt-0"
        >
          !
        </span>
        <p>
          <strong className="font-extrabold uppercase">
            Bản mô phỏng phục vụ Hackathon.
          </strong>{" "}
          Đây không phải website của Chính phủ, không có giá trị thực hiện
          thủ tục hành chính.
        </p>
      </div>
      <button
        aria-label="Đóng cảnh báo"
        className="absolute top-1/2 right-2 flex -translate-y-1/2 size-7 items-center justify-center rounded text-[#7f1d1d] hover:bg-[#7f1d1d]/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#991b1b]"
        onClick={() => {
          sessionStorage.setItem(DISMISS_KEY, "1");
          setDismissed(true);
        }}
        type="button"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </aside>
  );
}
