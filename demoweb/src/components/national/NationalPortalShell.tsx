import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  CircleUserRound,
  HeartHandshake,
  HelpCircle,
  Home,
  Menu,
  Phone,
} from "lucide-react";

import { marriageRoutes } from "@/data/marriage";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface NationalPortalShellProps {
  breadcrumbs: readonly BreadcrumbItem[];
  children: ReactNode;
}

const navItems = [
  { label: "Thông tin và dịch vụ", href: marriageRoutes.category },
  { label: "Thanh toán trực tuyến", href: "https://dichvucong.gov.vn/thanh-toan-truc-tuyen" },
  { label: "Phản ánh kiến nghị", href: "https://dichvucong.gov.vn/phan-anh-kien-nghi" },
  { label: "Hỗ trợ", href: "https://dichvucong.gov.vn/ho-tro" },
] as const;

function PortalLogo() {
  return (
    <Link
      href="/"
      className="block w-full max-w-[536px] rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#ce7a58]"
      aria-label="Về trang chủ Cổng Dịch vụ công Quốc gia"
    >
      <Image
        src="/target/p/home/theme/img/header/logo.png"
        alt="Cổng Dịch vụ công Quốc gia"
        width={1072}
        height={164}
        priority
        className="h-auto w-full"
      />
    </Link>
  );
}

function MobileMenu() {
  return (
    <details className="group relative ml-auto lg:hidden">
      <summary className="flex size-12 cursor-pointer list-none items-center justify-center bg-[#ce7a58] text-white [&::-webkit-details-marker]:hidden">
        <Menu className="size-6" aria-hidden="true" />
        <span className="sr-only">Mở trình đơn chính</span>
      </summary>
      <div className="absolute top-full right-0 z-50 w-[min(92vw,360px)] border border-[#e2e2e2] bg-white p-3 shadow-xl">
        <nav aria-label="Trình đơn trên thiết bị di động">
          <ul className="divide-y divide-[#e2e2e2]">
            <li>
              <Link
                href="/"
                className="flex items-center gap-3 px-3 py-3 font-medium hover:bg-[#ce7a58]/10 focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
              >
                <Home className="size-5 text-[#ce7a58]" aria-hidden="true" />
                Trang chủ
              </Link>
            </li>
            {navItems.map((item) => (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className="block px-3 py-3 font-medium hover:bg-[#ce7a58]/10 focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <a
          href="https://sso.dancuquocgia.gov.vn/auth?response_type=code&client_id=sso-c12-dvc-web&redirect_uri=https%3A%2F%2Fdichvucong.gov.vn%2Fsso&scope=openid"
          className="mt-3 flex items-center gap-3 rounded-lg bg-[#f5f5f5] px-3 py-3 font-semibold hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
        >
          <CircleUserRound className="size-7 text-[#ce7a58]" aria-hidden="true" />
          Đăng nhập
        </a>
      </div>
    </details>
  );
}

function NationalHeader() {
  return (
    <>
      <header className="bg-white">
        <div className="mx-auto flex min-h-[92px] w-full max-w-[1200px] items-center justify-between gap-6 px-4 py-3">
          <PortalLogo />
          <a
            id="dang-nhap"
            href="https://sso.dancuquocgia.gov.vn/auth?response_type=code&client_id=sso-c12-dvc-web&redirect_uri=https%3A%2F%2Fdichvucong.gov.vn%2Fsso&scope=openid"
            className="hidden shrink-0 items-center gap-3 rounded-lg px-4 py-2 text-lg font-semibold text-[#374151] hover:bg-[#f5f5f5] hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58] lg:flex"
          >
            <span className="flex size-10 items-center justify-center rounded-full bg-[#ce7a58] text-white">
              <CircleUserRound className="size-6" aria-hidden="true" />
            </span>
            Đăng nhập
            <ChevronDown className="size-4 text-[#6b7280]" aria-hidden="true" />
          </a>
          <MobileMenu />
        </div>
      </header>

      <div className="border-y border-[#e5e7eb] bg-[#f5f5f5]">
        <div className="mx-auto hidden min-h-14 w-full max-w-[1200px] items-stretch px-4 lg:flex">
          <Link
            href="/"
            aria-label="Trang chủ"
            className="flex w-14 items-center justify-center bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
          >
            <Home className="size-6" aria-hidden="true" />
          </Link>
          <nav aria-label="Trình đơn chính">
            <ul className="flex h-full items-stretch">
              {navItems.map((item) => (
                <li key={item.label} className="flex">
                  <Link
                    href={item.href}
                    className="flex items-center gap-1 px-5 text-base font-medium text-[#374151] hover:bg-white hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
                  >
                    {item.label}
                    {item.label === "Thông tin và dịch vụ" || item.label === "Hỗ trợ" ? (
                      <ChevronDown className="size-3.5" aria-hidden="true" />
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </>
  );
}

function Breadcrumbs({ items }: { items: readonly BreadcrumbItem[] }) {
  return (
    <nav
      className="mx-auto w-full max-w-[1200px] px-4 py-5"
      aria-label="Đường dẫn trang"
    >
      <ol className="flex flex-wrap items-center gap-2 text-sm text-[#4b5563] sm:text-base">
        <li>
          <Link
            href="/"
            className="rounded-sm hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
          >
            Trang chủ
          </Link>
        </li>
        {items.map((item) => (
          <li key={`${item.href ?? "current"}-${item.label}`} className="flex min-w-0 items-center gap-2">
            <ChevronRight className="size-3.5 shrink-0 text-[#9ca3af]" aria-hidden="true" />
            {item.href ? (
              <Link
                href={item.href}
                className="rounded-sm hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
              >
                {item.label}
              </Link>
            ) : (
              <span className="font-medium text-[#1e2f41]" aria-current="page">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function SupportStrip() {
  const items = [
    {
      label: "Câu hỏi thường gặp",
      href: "https://dichvucong.gov.vn/ho-tro",
      icon: HelpCircle,
    },
    {
      label: "Hướng dẫn sử dụng",
      href: "https://dichvucong.gov.vn/huong-dan",
      icon: BookOpen,
    },
  ] as const;

  return (
    <section className="bg-[#f5f5f5]" aria-label="Thông tin hỗ trợ">
      <div className="mx-auto grid w-full max-w-[900px] grid-cols-1 gap-2 px-4 py-5 sm:grid-cols-2 sm:gap-8">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.label}
              href={item.href}
              className="group flex items-center justify-center gap-4 rounded-lg p-3 hover:bg-white focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
            >
              <span className="relative flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white sm:size-16">
                <Image
                  src="/target/p/home/img/home/trongdong.png"
                  alt=""
                  width={80}
                  height={80}
                  className="absolute inset-0 size-full object-cover opacity-25"
                />
                <Icon className="relative size-7 text-[#903938]" aria-hidden="true" />
              </span>
              <span className="font-medium text-[#1e2f41] group-hover:text-[#ce7a58]">
                {item.label}
              </span>
            </a>
          );
        })}
      </div>
    </section>
  );
}

function NationalFooter() {
  return (
    <footer className="bg-[#903938] px-4 py-3 text-white">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-center justify-center gap-2 text-center text-sm sm:flex-row sm:text-base">
        <HeartHandshake className="size-5 shrink-0" aria-hidden="true" />
        <span>Cơ quan chủ quản: Trung tâm dữ liệu quốc gia - Bộ Công an.</span>
        <a
          href="tel:18001096"
          className="inline-flex items-center gap-1 font-semibold hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        >
          <Phone className="size-4" aria-hidden="true" />
          Tổng đài hỗ trợ: 18001096
        </a>
      </div>
    </footer>
  );
}

export function NationalPortalShell({ breadcrumbs, children }: NationalPortalShellProps) {
  return (
    <div className="flex min-h-screen flex-1 flex-col bg-white text-[#1e2f41]">
      <a
        href="#noi-dung-chinh"
        className="sr-only z-[100] rounded bg-white px-4 py-2 text-[#903938] focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Chuyển đến nội dung chính
      </a>
      <NationalHeader />
      <Breadcrumbs items={breadcrumbs} />
      <main id="noi-dung-chinh" className="flex-1">
        {children}
      </main>
      <SupportStrip />
      <NationalFooter />
    </div>
  );
}
