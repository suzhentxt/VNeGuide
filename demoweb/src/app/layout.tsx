import type { Metadata } from "next";
import localFont from "next/font/local";

import { ChatWidget } from "@/components/chat/ChatWidget";
import { DemoDisclaimer } from "@/components/DemoDisclaimer";
import { DocumentValidationProvider } from "@/components/ocr/DocumentValidationProvider";
import { ProcedureWorkspaceProvider } from "@/components/workspace/ProcedureWorkspaceProvider";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

const nunito = localFont({
  variable: "--font-nunito",
  display: "swap",
  src: [
    {
      path: "../../public/target/p/home/theme/fonts/nunito/NunitoSans-Regular.woff",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../public/target/p/home/theme/fonts/nunito/NunitoSans-SemiBold.woff",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/target/p/home/theme/fonts/nunito/NunitoSans-Bold.woff",
      weight: "700",
      style: "normal",
    },
  ],
});

export const metadata: Metadata = {
  applicationName: "Demoweb Hackathon - Bản mô phỏng",
  title: {
    default: "Bản mô phỏng Hackathon | Cổng Dịch vụ công",
    template: "%s | Bản mô phỏng Hackathon",
  },
  description:
    "Bản mô phỏng giao diện dịch vụ công phục vụ Hackathon; không phải website chính thức của Chính phủ và không tiếp nhận hồ sơ thật.",
  keywords: [
    "dịch vụ công",
    "dịch vụ công trực tuyến",
    "thủ tục hành chính",
    "đề án 06",
    "trung tâm dữ liệu quốc gia",
    "bộ công an",
    "vneid",
    "dichvucong.gov.vn",
  ],
  authors: [{ name: "Nhóm dự thi Hackathon" }],
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
    },
  },
  icons: {
    icon: "/target/p/home/img/header/quoc_huy.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      className={`${nunito.variable} h-full`}
      data-scroll-behavior="smooth"
      suppressHydrationWarning
    >
      <body suppressHydrationWarning className="flex min-h-full flex-col">
        <DemoDisclaimer />
        <ProcedureWorkspaceProvider>
          <DocumentValidationProvider>
            {children}
            <ChatWidget />
          </DocumentValidationProvider>
          <Toaster />
        </ProcedureWorkspaceProvider>
      </body>
    </html>
  );
}
