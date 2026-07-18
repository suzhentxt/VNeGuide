import type { ReactNode } from "react";

import { ChatWidget } from "@/components/chat/ChatWidget";
import { ProcedureWorkspaceProvider } from "@/components/workspace/ProcedureWorkspaceProvider";

export default function MarriageAndFamilyLayout({ children }: { children: ReactNode }) {
  return (
    <ProcedureWorkspaceProvider>
      {children}
      <ChatWidget />
    </ProcedureWorkspaceProvider>
  );
}
