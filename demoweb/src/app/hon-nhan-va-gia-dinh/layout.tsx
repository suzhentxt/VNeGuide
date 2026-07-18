import type { ReactNode } from "react";

import { ChatWidget } from "@/components/chat/ChatWidget";

export default function MarriageAndFamilyLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <ChatWidget />
    </>
  );
}
