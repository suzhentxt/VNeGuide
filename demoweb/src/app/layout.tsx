import type { Metadata } from "next";
import localFont from "next/font/local";
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
  applicationName: "Cổng Dịch vụ công Quốc gia",
  title:
    "Cổng Dịch vụ công Quốc gia - Trung tâm dữ liệu quốc gia, Bộ Công an",
  description:
    "Cổng Dịch vụ công Quốc gia, trực thuộc Trung tâm dữ liệu quốc gia - Bộ Công an. Nơi cung cấp thông tin, hỗ trợ đăng ký thủ tục hành chính trực tuyến, kết nối Cơ sở dữ liệu quốc gia về dân cư.",
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
  authors: [{ name: "Trung tâm dữ liệu quốc gia - Bộ Công An" }],
  robots: {
    index: true,
    follow: true,
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
    >
      <body suppressHydrationWarning className="flex min-h-full flex-col">
        {children}
      </body>
    </html>
  );
}
