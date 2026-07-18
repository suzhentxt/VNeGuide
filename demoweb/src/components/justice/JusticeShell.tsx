import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import {
  ChevronDown,
  Home,
  Landmark,
  RefreshCw,
} from "lucide-react";

export type JusticeNavKey =
  | "procedures"
  | "payments"
  | "feedback"
  | "lookup"
  | "support";

interface JusticeShellProps {
  activeNav?: JusticeNavKey;
  children: ReactNode;
}

const navigationItems: ReadonlyArray<{
  href: string;
  key: JusticeNavKey;
  label: string;
}> = [
  {
    key: "procedures",
    label: "Danh sách thủ tục",
    href: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru/truc-tuyen",
  },
  {
    key: "payments",
    label: "Thanh toán trực tuyến",
    href: "https://dichvucong.gov.vn/p/home/dvc-thanh-toan-phi-le-phi-ho-so.html",
  },
  {
    key: "feedback",
    label: "Phản ánh kiến nghị",
    href: "https://dichvucong.gov.vn/p/phananhkiennghi/pakn-gui-pakn.html",
  },
  {
    key: "lookup",
    label: "Tra cứu hồ sơ",
    href: "https://dichvucongnganhtuphap.moj.gov.vn/tra-cuu-tinh-trang-ho-so",
  },
  {
    key: "support",
    label: "Hỗ trợ",
    href: "https://dichvucong.gov.vn/p/home/dvc-huong-dan-cong-dan-doanh-nghiep.html",
  },
];

export function JusticeShell({
  activeNav = "procedures",
  children,
}: JusticeShellProps) {
  return (
    <div className="flex min-h-screen flex-1 flex-col bg-[#f7f8fa] text-[16px] leading-normal text-[#212b36]">
      <header className="relative overflow-hidden border-b border-[#012d6914] bg-[#fffdfa]">
        <div className="pointer-events-none absolute inset-0">
          <Image
            alt=""
            aria-hidden="true"
            className="object-cover object-right"
            fill
            priority
            sizes="100vw"
            src="/target/p/home/theme/img/bg-news.jpg"
          />
        </div>

        <div className="relative mx-auto flex min-h-[138px] w-full max-w-[1440px] items-center justify-between gap-6 px-4 py-5 sm:px-8 lg:px-12">
          <Link
            aria-label="VNeGuide - Về trang chủ"
            className="flex min-w-0 items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#ce7a58] sm:gap-6"
            href="/"
          >
            <Image
              alt="Quốc huy Việt Nam"
              className="h-[72px] w-[72px] shrink-0 object-contain sm:h-[92px] sm:w-[92px]"
              height={96}
              priority
              src="/target/p/home/img/header/quoc_huy.png"
              width={96}
            />
            <span className="min-w-0 text-[15px] leading-[1.3] font-extrabold text-[#903938] uppercase sm:text-[22px] lg:text-[26px]">
              <span className="block">VNeGuide hỗ trợ chuẩn bị</span>
              <span className="block">ba thủ tục hành chính</span>
            </span>
          </Link>

          <div className="relative z-10 hidden shrink-0 items-center gap-3 text-[#23406e] md:flex">
            <span className="inline-flex size-10 items-center justify-center rounded-full bg-[#eef2f7] text-sm font-bold">
              CD
            </span>
            <span className="max-w-[180px] truncate text-sm font-medium uppercase lg:text-base">
              Công dân mẫu
            </span>
            <ChevronDown aria-hidden="true" className="size-4" />
            <span aria-hidden="true" className="mx-1 h-6 w-px bg-[#d8dee8]" />
            <RefreshCw aria-hidden="true" className="size-5" />
          </div>
        </div>
      </header>

      <nav
        aria-label="Điều hướng mô phỏng VNeGuide"
        className="border-b border-[#e6e9ee] bg-white shadow-sm"
      >
        <div className="mx-auto flex w-full max-w-[1440px] items-stretch overflow-x-auto px-4 sm:px-8 lg:px-12">
          <Link
            aria-label="Trang chủ danh sách thủ tục"
            className="flex min-h-14 w-14 shrink-0 items-center justify-center text-[#212b36] transition-colors hover:bg-[#f4e7e2] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#ce7a58]"
            href="/hon-nhan-va-gia-dinh/dang-ky-tam-tru/truc-tuyen"
          >
            <Home aria-hidden="true" className="size-6" strokeWidth={2.4} />
          </Link>

          {navigationItems.map((item) => {
            const isActive = item.key === activeNav;

            return (
              <Link
                aria-current={isActive ? "page" : undefined}
                className={`flex min-h-14 shrink-0 items-center px-5 text-sm font-semibold whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#ce7a58] sm:text-base ${
                  isActive
                    ? "bg-[#903938] text-white"
                    : "text-[#42526b] hover:bg-[#f4e7e2] hover:text-[#903938]"
                }`}
                href={item.href}
                key={item.key}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <main
        className="relative flex flex-1 flex-col bg-[#f6f7f9]"
        style={{
          backgroundImage:
            "linear-gradient(135deg, rgba(144,57,56,0.025) 25%, transparent 25%), linear-gradient(315deg, rgba(144,57,56,0.025) 25%, transparent 25%)",
          backgroundPosition: "0 0, 18px 18px",
          backgroundSize: "36px 36px",
        }}
      >
        {children}
      </main>

      <footer className="bg-[#903938] text-white">
        <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-center gap-x-8 gap-y-3 px-4 py-5 text-sm sm:px-8 sm:text-base lg:px-12">
          <span className="inline-flex items-center gap-2 font-semibold uppercase">
            <Landmark aria-hidden="true" className="size-4" />
            VNeGuide Hackathon
          </span>
          <span>Không phải website Chính phủ · Không tiếp nhận hồ sơ thật</span>
        </div>
      </footer>
    </div>
  );
}
