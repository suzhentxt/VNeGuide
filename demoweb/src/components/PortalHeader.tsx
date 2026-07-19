"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  ChevronRightIcon,
  MenuIcon,
  PortalHomeIcon,
  XIcon,
} from "@/components/icons";
import type { NavigationItem } from "@/types/portal";

const PUBLIC_PORTAL_ORIGIN = "https://dichvucong.gov.vn";
const LOGIN_URL =
  "https://sso.dancuquocgia.gov.vn/auth?response_type=code&client_id=sso-c12-dvc-web&redirect_uri=https%3A%2F%2Fdichvucong.gov.vn%2Fsso&scope=openid";

const portalHref = (path: string) => `${PUBLIC_PORTAL_ORIGIN}${path}`;

const navigationItems: NavigationItem[] = [
  {
    label: "Thông tin và dịch vụ",
    children: [
      {
        label: "Thủ tục hành chính",
        children: [
          {
            label: "Tra cứu TTHC",
            href: portalHref("/tra-cuu-thu-tuc/danh-sach"),
          },
          {
            label: "Thủ tục hành chính",
            href: portalHref("/thu-tuc-hanh-chinh"),
          },
          {
            label: "Tham vấn thủ tục hành chính",
            href: portalHref("/tham-van-thu-tuc-hanh-chinh"),
          },
          {
            label: "Thủ tục hành chính liên thông",
            href: portalHref("/thu-tuc-hanh-chinh-lien-thong"),
          },
          { label: "Thống kê", href: portalHref("/thong-ke") },
          { label: "Cơ quan", href: portalHref("/co-quan") },
          {
            label: "Quyết định công bố",
            href: portalHref("/quyet-dinh-cong-bo"),
          },
        ],
      },
      {
        label: "Dịch vụ công trực tuyến",
        href: portalHref("/dvc-dich-vu-cong-truc-tuyen"),
      },
      {
        label: "Dịch vụ công nổi bật",
        href: portalHref("/dich-vu-cong-noi-bat"),
      },
      { label: "Tra cứu hồ sơ", href: portalHref("/tra-cuu-ho-so") },
      {
        label: "Câu hỏi thường gặp",
        href: portalHref("/cau-hoi-thuong-gap"),
      },
    ],
  },
  {
    label: "Thanh toán trực tuyến",
    href: portalHref("/thanh-toan-truc-tuyen"),
  },
  {
    label: "Phản ánh kiến nghị",
    children: [
      {
        label: "Gửi PAKN",
        href: portalHref("/nop-phan-anh-kien-nghi"),
      },
      {
        label: "Tra cứu kết quả trả lời",
        href: portalHref("/tra-cuu-phan-anh-kien-nghi"),
      },
    ],
  },
  {
    label: "Hỗ trợ",
    children: [
      { label: "Giới thiệu", href: portalHref("/gioi-thieu") },
      {
        label: "Điều khoản sử dụng",
        href: portalHref("/dieu-khoan-su-dung"),
      },
      {
        label: "Hướng dẫn sử dụng",
        href: portalHref("/huong-dan-su-dung/huong-dan-chung"),
      },
      { label: "Tin tức", href: portalHref("/tin-tuc") },
      { label: "Video", href: portalHref("/video") },
      { label: "Hình ảnh", href: portalHref("/hinh-anh") },
    ],
  },
];

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#CE7A58] focus-visible:ring-offset-2";

interface AuthLinksProps {
  mobile?: boolean;
  onNavigate?: () => void;
}

function AuthLinks({ mobile = false, onNavigate }: AuthLinksProps) {
  return (
    <a
      className={`${
        mobile ? "w-full" : "w-[130px]"
      } ${focusRing} box-border inline-flex h-10 items-center justify-center rounded-[3px] border border-[#CE7A58] px-3 text-center text-[18px] leading-[24px] font-medium text-[#CE7A58] transition-colors hover:bg-[#CE7A58] hover:text-white`}
      href={LOGIN_URL}
      onClick={onNavigate}
    >
      Đăng nhập
    </a>
  );
}

interface MenuItemsProps {
  items: NavigationItem[];
  mobile?: boolean;
  onNavigate?: () => void;
  depth?: number;
}

function DesktopMenuItems({ items, depth = 0 }: MenuItemsProps) {
  return (
    <ul
      className={`${
        depth === 0
          ? "pointer-events-none invisible absolute top-full left-0 z-50 min-w-full opacity-0 shadow-md transition-[opacity,visibility] duration-150 group-hover/menu:pointer-events-auto group-hover/menu:visible group-hover/menu:opacity-100 group-open/menu:pointer-events-auto group-open/menu:visible group-open/menu:opacity-100"
          : "invisible absolute top-0 left-full z-50 min-w-max opacity-0 shadow-md transition-[opacity,visibility] duration-150 group-hover/sub:pointer-events-auto group-hover/sub:visible group-hover/sub:opacity-100 group-open/sub:pointer-events-auto group-open/sub:visible group-open/sub:opacity-100"
      } list-none bg-[#E9926F] p-0 text-[16px] text-white`}
    >
      {items.map((item) => (
        <li
          className="relative border-b border-white/10 last:border-b-0"
          key={item.label}
        >
          {item.children ? (
            <details className="group/sub">
              <summary
                className={`${focusRing} flex w-full cursor-pointer list-none items-center justify-between gap-4 whitespace-nowrap p-[10px] text-left transition-colors hover:bg-[#CE7A58] focus:bg-[#CE7A58] group-open/sub:bg-[#CE7A58] [&::-webkit-details-marker]:hidden`}
              >
                <span>{item.label}</span>
                <ChevronRightIcon
                  aria-hidden="true"
                  className="size-4 transition-transform group-open/sub:rotate-90"
                />
              </summary>
              <DesktopMenuItems items={item.children} depth={depth + 1} />
            </details>
          ) : (
            <a
              className={`${focusRing} block whitespace-nowrap p-[10px] transition-colors hover:bg-[#CE7A58] focus:bg-[#CE7A58]`}
              href={item.href}
            >
              {item.label}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

function MobileMenuItems({
  items,
  onNavigate,
  depth = 0,
}: MenuItemsProps) {
  return (
    <ul
      className={`${
        depth === 0 ? "bg-[#E9926F] text-white" : "bg-[#D77A56]"
      } list-none p-0 text-[18px]`}
    >
      {items.map((item) => (
        <li
          className="border-b border-white/10 last:border-b-0"
          key={item.label}
        >
          {item.children ? (
            <>
              <div
                className="flex items-center gap-2 px-[10px] py-[9px] font-semibold"
                style={{ paddingLeft: `${10 + depth * 12}px` }}
              >
                <ChevronRightIcon aria-hidden="true" className="size-4" />
                <span>{item.label}</span>
              </div>
              <MobileMenuItems
                depth={depth + 1}
                items={item.children}
                onNavigate={onNavigate}
              />
            </>
          ) : (
            <a
              className={`${focusRing} block p-[10px] transition-colors hover:bg-[#CE7A58] focus:bg-[#CE7A58]`}
              href={item.href}
              onClick={onNavigate}
              style={{ paddingLeft: `${10 + depth * 12}px` }}
            >
              {item.label}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

function DesktopNavigation() {
  return (
    <nav
      aria-label="Điều hướng chính"
      className="hidden bg-[#F5F5F5] min-[992px]:block"
    >
      <div className="mx-auto w-full max-w-[1200px] px-[15px]">
        <ul className="flex list-none p-0 text-[20px] leading-[1.3333]">
          <li>
            <Link
              aria-label="Trang chủ"
              className={`${focusRing} flex h-[42px] items-center bg-[#CE7A58] px-[15px] py-[10px] text-white transition-colors`}
              href="/"
            >
              <PortalHomeIcon aria-hidden="true" className="size-5" />
            </Link>
          </li>

          {navigationItems.map((item) => (
            <li className="relative" key={item.label}>
              {item.children ? (
                <details className="group/menu">
                  <summary
                    className={`${focusRing} box-border flex h-[42px] cursor-pointer list-none items-center whitespace-nowrap px-[12px] py-[10px] font-medium transition-colors group-hover/menu:bg-[#CE7A58] group-hover/menu:text-white group-open/menu:bg-[#CE7A58] group-open/menu:text-white [&::-webkit-details-marker]:hidden`}
                  >
                    <span>{item.label}</span>
                  </summary>
                  <DesktopMenuItems items={item.children} />
                </details>
              ) : (
                <a
                  className={`${focusRing} box-border flex h-[42px] items-center whitespace-nowrap px-[12px] py-[10px] font-medium transition-colors hover:bg-[#CE7A58] hover:text-white`}
                  href={item.href}
                >
                  {item.label}
                </a>
              )}
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}

interface MobileNavigationProps {
  firstLinkRef: React.RefObject<HTMLAnchorElement | null>;
  onNavigate: () => void;
  openSubmenu: string | null;
  setOpenSubmenu: React.Dispatch<React.SetStateAction<string | null>>;
}

function MobileNavigation({
  firstLinkRef,
  onNavigate,
  openSubmenu,
  setOpenSubmenu,
}: MobileNavigationProps) {
  return (
    <div className="px-[15px]">
      <ul className="list-none p-0 text-[20px] leading-[1.3333]">
        <li className="border-b border-white/10">
          <Link
            aria-label="Trang chủ"
            className={`${focusRing} flex min-h-[42px] items-center bg-[#CE7A58] px-[15px] py-[10px] text-white`}
            href="/"
            onClick={onNavigate}
            ref={firstLinkRef}
          >
            <PortalHomeIcon aria-hidden="true" className="size-5" />
          </Link>
        </li>

        {navigationItems.map((item, index) => {
          const submenuId = `mobile-submenu-${index}`;
          const isOpen = openSubmenu === item.label;

          return (
            <li className="border-b border-white/10" key={item.label}>
              {item.children ? (
                <>
                  <button
                    aria-controls={submenuId}
                    aria-expanded={isOpen}
                    className={`${focusRing} flex w-full items-center justify-between px-[15px] py-[10px] text-left font-medium transition-colors hover:bg-[#CE7A58] hover:text-white ${
                      isOpen ? "bg-[#CE7A58] text-white" : ""
                    }`}
                    onClick={() =>
                      setOpenSubmenu((current) =>
                        current === item.label ? null : item.label,
                      )
                    }
                    type="button"
                  >
                    <span>{item.label}</span>
                    <ChevronRightIcon
                      aria-hidden="true"
                      className={`size-4 shrink-0 transition-transform duration-200 ${
                        isOpen ? "rotate-90" : ""
                      }`}
                    />
                  </button>

                  {isOpen ? (
                    <div id={submenuId}>
                      <MobileMenuItems
                        items={item.children}
                        onNavigate={onNavigate}
                      />
                    </div>
                  ) : null}
                </>
              ) : (
                <a
                  className={`${focusRing} block px-[15px] py-[10px] font-medium transition-colors hover:bg-[#CE7A58] hover:text-white`}
                  href={item.href}
                  onClick={onNavigate}
                >
                  {item.label}
                </a>
              )}
            </li>
          );
        })}
      </ul>

      <div className="p-[15px]">
        <AuthLinks mobile onNavigate={onNavigate} />
      </div>
    </div>
  );
}

export function PortalHeader() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [openSubmenu, setOpenSubmenu] = useState<string | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const firstMobileLinkRef = useRef<HTMLAnchorElement>(null);

  const closeDrawer = () => {
    setDrawerOpen(false);
    setOpenSubmenu(null);
  };

  useEffect(() => {
    if (!drawerOpen) {
      return;
    }

    const menuButton = menuButtonRef.current;
    firstMobileLinkRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        setOpenSubmenu(null);
        menuButton?.focus();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const drawer = document.getElementById("portal-mobile-navigation");
      const drawerElements = drawer
        ? Array.from(
            drawer.querySelectorAll<HTMLElement>(
              'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
          ).filter((element) => element.offsetParent !== null)
        : [];
      const focusableElements = [
        menuButton,
        ...drawerElements,
      ].filter((element): element is HTMLElement => element !== null);

      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      menuButton?.focus();
    };
  }, [drawerOpen]);

  useEffect(() => {
    const desktopQuery = window.matchMedia("(min-width: 992px)");
    const handleDesktopChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        setDrawerOpen(false);
        setOpenSubmenu(null);
      }
    };

    desktopQuery.addEventListener("change", handleDesktopChange);
    return () => desktopQuery.removeEventListener("change", handleDesktopChange);
  }, []);

  return (
    <header id="trang-chu">
      <div className="border-b border-transparent bg-white py-[15px] max-[991px]:border-[#E2E2E2]">
        <div className="relative mx-auto w-full max-w-[1200px] px-[15px]">
          <Link
            aria-label="Cổng Dịch vụ công Quốc gia - Trang chủ"
            className={`${focusRing} block w-full max-w-[536px] max-[991px]:mx-auto max-[991px]:mb-[10px]`}
            href="/"
          >
            <Image
              alt="Cổng Dịch vụ công Quốc gia"
              className="h-auto w-full"
              height={164}
              preload
              src="/target/p/home/theme/img/header/logo.png"
              width={1072}
            />
          </Link>

          <div className="absolute top-[20px] right-[15px] hidden min-[992px]:block">
            <AuthLinks />
          </div>
        </div>
      </div>

      <DesktopNavigation />

      <button
        aria-controls="portal-mobile-navigation"
        aria-expanded={drawerOpen}
        aria-label={drawerOpen ? "Đóng trình đơn" : "Mở trình đơn"}
        className={`${focusRing} fixed top-0 right-0 z-[1100] hidden size-9 items-center justify-center bg-[#CE7A58] text-white transition-colors hover:bg-[#BC5D37] max-[991px]:flex`}
        onClick={() => {
          if (drawerOpen) {
            closeDrawer();
          } else {
            setDrawerOpen(true);
          }
        }}
        ref={menuButtonRef}
        type="button"
      >
        {drawerOpen ? (
          <XIcon aria-hidden="true" className="size-6" />
        ) : (
          <MenuIcon aria-hidden="true" className="size-6" />
        )}
      </button>

      <button
        aria-hidden={!drawerOpen}
        aria-label="Đóng trình đơn"
        className={`fixed inset-0 z-[1080] hidden bg-black/20 transition-opacity duration-300 max-[991px]:block ${
          drawerOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0"
        }`}
        onClick={closeDrawer}
        tabIndex={-1}
        type="button"
      />

      <nav
        aria-hidden={!drawerOpen}
        aria-label="Điều hướng chính trên thiết bị di động"
        className={`fixed top-0 bottom-0 left-0 z-[1090] hidden w-[260px] overflow-y-auto bg-[#F5F5F5] text-[#1E2F41] transition-transform duration-300 ease-in-out max-[991px]:block ${
          drawerOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        id="portal-mobile-navigation"
        inert={!drawerOpen}
      >
        <MobileNavigation
          firstLinkRef={firstMobileLinkRef}
          onNavigate={closeDrawer}
          openSubmenu={openSubmenu}
          setOpenSubmenu={setOpenSubmenu}
        />
      </nav>
    </header>
  );
}
