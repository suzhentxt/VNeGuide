"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "rounded-lg border border-[#e2e6ea] bg-white text-[#1e2f41] shadow-lg",
          description: "text-[#52606d]",
          actionButton: "bg-[#903938] text-white",
          cancelButton: "bg-white text-[#52606d] border border-[#c9cdcf]",
        },
      }}
    />
  );
}

export { toast } from "sonner";
