"use client";

import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { SearchIcon, XIcon } from "@/components/icons";
import {
  ministryOptions,
  parsePortalOptionsPayload,
  type PortalOption,
  provinceOptions,
} from "@/data/portal-authorities";
import { toast } from "sonner";

const serviceLinks = [
  {
    label: "Dịch vụ công trực tuyến",
    href: "https://dichvucong.gov.vn/dvc-dich-vu-cong-truc-tuyen",
  },
  {
    label: "Thủ tục hành chính của Đảng",
    href: "https://dichvucong.dcs.vn/web/home",
  },
  {
    label: "Dịch vụ công liên thông: Khai sinh, Khai tử",
    href: "https://lienthong.dichvucong.gov.vn/#/?vneid=1",
  },
] as const;

const SEARCH_RESULTS_URL =
  "https://dichvucong.gov.vn/dvc-ket-qua-thu-tuc";
const LEGACY_SEARCH_RESULTS_URL =
  "https://vpcp.dichvucong.gov.vn/p/home/dvc-ket-qua-thu-tuc.html";
const ADVANCED_RESULTS_URL =
  "https://vpcp.dichvucong.gov.vn/p/home/dvc-danh-sach-dich-vu-cong.html";
const LOCAL_OPTIONS_TIMEOUT_MS = 12_000;

function normalizeKeyword(value: string) {
  return value.replace(/[&/\\#,+()$~%'":*?<>{}^]/g, " ").trim();
}

type Jurisdiction = "province" | "ministry";
type LocalAuthority = "ward" | "department";
type OptionsStatus = "idle" | "loading" | "ready" | "error";

export function HeroSearch() {
  const [keyword, setKeyword] = useState("");
  const [advancedKeyword, setAdvancedKeyword] = useState("");
  const [jurisdiction, setJurisdiction] =
    useState<Jurisdiction>("province");
  const [localAuthority, setLocalAuthority] =
    useState<LocalAuthority>("ward");
  const [jurisdictionValue, setJurisdictionValue] = useState("");
  const [localAuthorityValue, setLocalAuthorityValue] = useState("");
  const [localOptions, setLocalOptions] = useState<PortalOption[]>([]);
  const [localOptionsStatus, setLocalOptionsStatus] =
    useState<OptionsStatus>("idle");
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [announcement, setAnnouncement] = useState("");

  const dialogRef = useRef<HTMLDivElement>(null);
  const advancedButtonRef = useRef<HTMLButtonElement>(null);
  const advancedKeywordRef = useRef<HTMLInputElement>(null);
  const localOptionsRequestRef = useRef<AbortController | null>(null);
  const dialogTitleId = useId();
  const dialogDescriptionId = useId();
  const jurisdictionName = useId();
  const localAuthorityName = useId();

  const closeAdvancedSearch = useCallback(() => {
    setIsAdvancedOpen(false);
    setJurisdiction("province");
    setLocalAuthority("ward");
    setJurisdictionValue("");
    setLocalAuthorityValue("");
    setLocalOptions([]);
    setLocalOptionsStatus("idle");
    localOptionsRequestRef.current?.abort();
  }, []);

  const loadLocalOptions = useCallback(
    async (provinceId: string, kind: LocalAuthority) => {
      localOptionsRequestRef.current?.abort();
      setLocalAuthorityValue("");

      if (!provinceId) {
        setLocalOptions([]);
        setLocalOptionsStatus("idle");
        return;
      }

      const controller = new AbortController();
      localOptionsRequestRef.current = controller;
      setLocalOptions([]);
      setLocalOptionsStatus("loading");
      let didTimeout = false;
      const timeoutId = window.setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, LOCAL_OPTIONS_TIMEOUT_MS);

      try {
        const response = await fetch(
          `/api/portal-options?kind=${kind}&provinceId=${provinceId}`,
          { cache: "no-store", signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error("Portal options request failed.");
        }

        const result: unknown = await response.json();
        const options = parsePortalOptionsPayload(result);
        if (options === null) {
          throw new Error("Portal options response was invalid.");
        }

        if (!controller.signal.aborted) {
          setLocalOptions(options);
          setLocalOptionsStatus("ready");
        }
      } catch {
        if (!controller.signal.aborted || didTimeout) {
          setLocalOptions([]);
          setLocalOptionsStatus("error");
        }
      } finally {
        window.clearTimeout(timeoutId);
      }
    },
    [],
  );

  useEffect(
    () => () => {
      localOptionsRequestRef.current?.abort();
    },
    [],
  );

  useEffect(() => {
    if (!isAdvancedOpen) {
      return;
    }

    const triggerElement = advancedButtonRef.current;
    const focusFrame = window.requestAnimationFrame(() => {
      advancedKeywordRef.current?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeAdvancedSearch();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const focusableElements = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      );

      if (!focusableElements?.length) {
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
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("keydown", handleKeyDown);
      triggerElement?.focus();
    };
  }, [closeAdvancedSearch, isAdvancedOpen]);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submittedKeyword = keyword.trim();

    const searchParams = new URLSearchParams({
      keyword: normalizeKeyword(submittedKeyword),
    });

    setAnnouncement(
      submittedKeyword
        ? `Đã gửi tìm kiếm cho "${submittedKeyword}".`
        : "Đã gửi tìm kiếm dịch vụ công.",
    );
    toast.info("Đang chuyển sang Cổng Dịch vụ công Quốc gia để hiển thị kết quả.");
    window.location.assign(`${SEARCH_RESULTS_URL}?${searchParams.toString()}`);
  };

  const openAdvancedSearch = () => {
    setAdvancedKeyword(keyword);
    setIsAdvancedOpen(true);
  };

  const handleAdvancedSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submittedKeyword = advancedKeyword.trim();
    const normalizedKeyword = normalizeKeyword(submittedKeyword);

    setKeyword(submittedKeyword);
    setAnnouncement("Đã gửi tìm kiếm nâng cao.");

    const jurisdictionOptions =
      jurisdiction === "province" ? provinceOptions : ministryOptions;
    const selectedJurisdiction = jurisdictionOptions.find(
      (option) => option.id === jurisdictionValue,
    );
    const selectedLocalAuthority = localOptions.find(
      (option) => option.id === localAuthorityValue,
    );

    if (!selectedJurisdiction) {
      setAnnouncement("Vui lòng chọn cấp thực hiện.");
      return;
    }

    if (
      jurisdiction === "province" &&
      jurisdictionValue &&
      !localAuthorityValue
    ) {
      const searchParams = new URLSearchParams({
        originKey: submittedKeyword,
        tukhoa: normalizedKeyword,
        tinh_thanh: selectedJurisdiction.label,
      });
      window.location.assign(
        `${LEGACY_SEARCH_RESULTS_URL}?${searchParams.toString()}`,
      );
      return;
    }

    const searchParams = new URLSearchParams({
      tu_khoa: submittedKeyword,
      bo_nganh:
        jurisdiction === "ministry" ? selectedJurisdiction.label : "",
      tinh_thanh:
        jurisdiction === "province" ? selectedJurisdiction.label : "",
      so:
        jurisdiction === "province" &&
        localAuthority === "department" &&
        selectedLocalAuthority
          ? selectedLocalAuthority.label
          : "",
      quan_huyen:
        jurisdiction === "province" &&
        localAuthority === "ward" &&
        selectedLocalAuthority
          ? selectedLocalAuthority.label
          : "",
      phuong_xa: "",
      id_tinh_thanh: jurisdiction === "province" ? jurisdictionValue : "-1",
      id_quan_huyen:
        jurisdiction === "province" && localAuthority === "ward"
          ? localAuthorityValue || "-1"
          : "-1",
      id_phuong_xa: "-1",
      id_so:
        jurisdiction === "province" && localAuthority === "department"
          ? localAuthorityValue || "-1"
          : "-1",
      id_bo_nganh: jurisdiction === "ministry" ? jurisdictionValue : "-1",
    });
    window.location.assign(`${ADVANCED_RESULTS_URL}?${searchParams.toString()}`);
  };

  const handleOverlayKeyDown = (
    event: ReactKeyboardEvent<HTMLDivElement>,
  ) => {
    if (event.key === "Escape") {
      closeAdvancedSearch();
    }
  };

  return (
    <>
      <section
        aria-label="Tra cứu dịch vụ công"
        className="bg-[#CE7A58] bg-[url('/target/p/home/theme/img/home/banner.jpg')] bg-cover bg-center bg-no-repeat py-10"
      >
        <div className="w-full px-[15px]">
          <div className="mx-auto max-w-[991px]">
            <form
              aria-label="Tìm kiếm dịch vụ công"
              className="relative max-[768px]:mb-10"
              role="search"
              onSubmit={handleSearch}
            >
              <label className="sr-only" htmlFor="portal-search-keyword">
                Nhập từ khoá tìm kiếm
              </label>
              <input
                id="portal-search-keyword"
                className="h-10 w-full rounded-[4px] border-0 bg-white py-0 pr-[245px] pl-3 text-[18px] font-normal text-[#1E2F41] shadow-none placeholder:text-[#8F969C] focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#CE7A58] max-[768px]:pr-10"
                maxLength={100}
                placeholder="Nhập từ khoá tìm kiếm"
                type="search"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
              />
              <button
                ref={advancedButtonRef}
                aria-haspopup="dialog"
                className="absolute top-0 right-[60px] z-10 flex h-10 w-[180px] cursor-pointer items-center justify-center border-0 border-l border-solid border-l-[#E2E2E2] bg-transparent px-[10px] py-[7px] text-center text-[18px] text-[#1E2F41] transition-colors hover:text-[#903938] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#903938] max-[768px]:top-auto max-[768px]:right-0 max-[768px]:bottom-[-45px] max-[768px]:w-full max-[768px]:justify-end max-[768px]:border-l-0 max-[768px]:text-right max-[768px]:text-white max-[768px]:hover:text-white max-[768px]:hover:underline"
                type="button"
                onClick={openAdvancedSearch}
              >
                Tìm kiếm nâng cao
              </button>
              <button
                aria-label="Tìm kiếm"
                className="absolute top-0 right-0 flex h-10 w-[60px] cursor-pointer items-center justify-center rounded-r-[3px] bg-[#F5F5F5] text-[#1E2F41] transition-colors hover:bg-[#903938] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#903938] max-[768px]:w-10"
                type="submit"
              >
                <SearchIcon
                  aria-hidden="true"
                  className="h-[18px] w-[18px] max-[768px]:h-4 max-[768px]:w-4"
                  strokeWidth={1.8}
                />
              </button>
            </form>

            <div className="mt-[30px] grid grid-cols-3 gap-[30px] max-[768px]:mt-[10px] max-[768px]:grid-cols-1 max-[768px]:gap-[10px]">
              {serviceLinks.map((service) => (
                <a
                  key={service.label}
                  className="flex min-h-[60px] w-full cursor-pointer items-center justify-center rounded-[4px] bg-[#FFC251] px-5 py-[6px] text-center text-[18px] leading-[1.3333] font-medium text-black transition-colors hover:bg-[#FFB01E] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  href={service.href}
                  onClick={() =>
                    setAnnouncement(
                      `Đã chọn ${service.label.toLocaleLowerCase("vi")}.`,
                    )
                  }
                >
                  {service.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>

      <p aria-live="polite" className="sr-only" role="status">
        {announcement}
      </p>

      {isAdvancedOpen ? (
        <div
          className="fixed inset-0 z-[1000] flex items-start justify-center overflow-y-auto bg-black/50"
          onKeyDown={handleOverlayKeyDown}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeAdvancedSearch();
            }
          }}
        >
          <div
            ref={dialogRef}
            aria-describedby={dialogDescriptionId}
            aria-labelledby={dialogTitleId}
            aria-modal="true"
            className="relative my-[30px] max-h-[calc(100vh-60px)] w-full max-w-[471px] overflow-y-auto bg-white px-[30px] py-5 text-[#1E2F41] animate-[portal-fade-in_180ms_ease-out] motion-reduce:animate-none"
            role="dialog"
          >
            <button
              aria-label="Đóng tìm kiếm nâng cao"
              className="absolute top-5 right-5 flex h-6 w-6 cursor-pointer items-center justify-center text-black transition-colors hover:text-[#903938] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
              type="button"
              onClick={closeAdvancedSearch}
            >
              <XIcon aria-hidden="true" className="h-5 w-5" strokeWidth={2} />
            </button>

            <form onSubmit={handleAdvancedSearch}>
              <h2
                id={dialogTitleId}
                className="mb-[15px] pr-8 text-[20px] leading-[1.3333] font-medium"
              >
                Nhập từ khoá tìm kiếm
              </h2>
              <p id={dialogDescriptionId} className="sr-only">
                Chọn từ khoá và cấp cơ quan để tìm kiếm dịch vụ công.
              </p>

              <div className="mb-5">
                <label className="sr-only" htmlFor="advanced-search-keyword">
                  Từ khoá tìm kiếm nâng cao
                </label>
                <input
                  ref={advancedKeywordRef}
                  id="advanced-search-keyword"
                  className="h-10 w-full rounded-[4px] border border-[#C9CDCF] bg-white px-3 text-[18px] font-medium text-[#1E2F41] placeholder:font-normal placeholder:text-[#8F969C] focus:border-[#CE7A58] focus:outline-none focus:ring-2 focus:ring-[#CE7A58]/40"
                  maxLength={100}
                  placeholder="Nhập từ khoá tìm kiếm"
                  required
                  type="search"
                  value={advancedKeyword}
                  onChange={(event) => setAdvancedKeyword(event.target.value)}
                />
              </div>

              <fieldset className="mb-5">
                <legend className="mb-[15px] text-[20px] font-medium">
                  Chọn cấp thực hiện
                </legend>
                <div className="flex flex-wrap gap-y-3">
                  <label className="flex w-[190px] cursor-pointer items-center gap-[10px] text-[18px] max-[480px]:w-1/2">
                    <input
                      checked={jurisdiction === "province"}
                      className="h-5 w-5 shrink-0 accent-[#CE7A58]"
                      name={jurisdictionName}
                      type="radio"
                      value="province"
                      onChange={() => {
                        setJurisdiction("province");
                        setJurisdictionValue("");
                        setLocalAuthority("ward");
                        void loadLocalOptions("", "ward");
                      }}
                    />
                    <span>Tỉnh/Thành phố</span>
                  </label>
                  <label className="flex w-[190px] cursor-pointer items-center gap-[10px] text-[18px] max-[480px]:w-1/2">
                    <input
                      checked={jurisdiction === "ministry"}
                      className="h-5 w-5 shrink-0 accent-[#CE7A58]"
                      name={jurisdictionName}
                      type="radio"
                      value="ministry"
                      onChange={() => {
                        setJurisdiction("ministry");
                        setJurisdictionValue("");
                        void loadLocalOptions("", "ward");
                      }}
                    />
                    <span>Bộ ngành</span>
                  </label>
                </div>
              </fieldset>

              <div className="mb-5">
                <label className="sr-only" htmlFor="advanced-jurisdiction">
                  {jurisdiction === "province"
                    ? "Chọn Tỉnh/Thành phố"
                    : "Chọn Bộ ngành"}
                </label>
                <select
                  id="advanced-jurisdiction"
                  className="h-10 w-full rounded-[4px] border border-[#C9CDCF] bg-white px-3 text-[18px] font-medium text-[#1E2F41] focus:border-[#CE7A58] focus:outline-none focus:ring-2 focus:ring-[#CE7A58]/40"
                  required
                  value={jurisdictionValue}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setJurisdictionValue(nextValue);
                    if (jurisdiction === "province") {
                      void loadLocalOptions(nextValue, localAuthority);
                    }
                  }}
                >
                  <option disabled value="">
                    {jurisdiction === "province"
                      ? "Chọn Tỉnh/Thành phố"
                      : "Chọn Bộ ngành"}
                  </option>
                  {(jurisdiction === "province"
                    ? provinceOptions
                    : ministryOptions
                  ).map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {jurisdiction === "province" ? (
                <>
                  <fieldset className="mb-5">
                    <legend className="sr-only">Chọn đơn vị trực thuộc</legend>
                    <div className="flex flex-wrap gap-y-3">
                      <label className="flex w-[190px] cursor-pointer items-center gap-[10px] text-[18px] max-[480px]:w-1/2">
                        <input
                          checked={localAuthority === "ward"}
                          className="h-5 w-5 shrink-0 accent-[#CE7A58]"
                          name={localAuthorityName}
                          type="radio"
                          value="ward"
                          onChange={() => {
                            setLocalAuthority("ward");
                            void loadLocalOptions(jurisdictionValue, "ward");
                          }}
                        />
                        <span>Phường/Xã</span>
                      </label>
                      <label className="flex w-[190px] cursor-pointer items-center gap-[10px] text-[18px] max-[480px]:w-1/2">
                        <input
                          checked={localAuthority === "department"}
                          className="h-5 w-5 shrink-0 accent-[#CE7A58]"
                          name={localAuthorityName}
                          type="radio"
                          value="department"
                          onChange={() => {
                            setLocalAuthority("department");
                            void loadLocalOptions(
                              jurisdictionValue,
                              "department",
                            );
                          }}
                        />
                        <span>Sở</span>
                      </label>
                    </div>
                  </fieldset>

                  <div className="mb-5">
                    <label
                      className="sr-only"
                      htmlFor="advanced-local-authority"
                    >
                      {localAuthority === "ward"
                        ? "Chọn Phường/Xã"
                        : "Chọn Sở"}
                    </label>
                    <select
                      id="advanced-local-authority"
                      aria-busy={localOptionsStatus === "loading"}
                      className="h-10 w-full rounded-[4px] border border-[#C9CDCF] bg-white px-3 text-[18px] font-medium text-[#1E2F41] focus:border-[#CE7A58] focus:outline-none focus:ring-2 focus:ring-[#CE7A58]/40"
                      disabled={
                        !jurisdictionValue || localOptionsStatus === "loading"
                      }
                      value={localAuthorityValue}
                      onChange={(event) =>
                        setLocalAuthorityValue(event.target.value)
                      }
                    >
                      <option value="">
                        {localOptionsStatus === "loading"
                          ? "Đang tải danh sách..."
                          : localOptionsStatus === "error"
                            ? "Không thể tải danh sách"
                            : localOptionsStatus === "ready" &&
                                localOptions.length === 0
                              ? "Không có dữ liệu"
                              : localAuthority === "ward"
                                ? "Chọn Phường/Xã"
                                : "Chọn Sở"}
                      </option>
                      {localOptions.map((authority) => (
                        <option key={authority.id} value={authority.id}>
                          {authority.label}
                        </option>
                      ))}
                    </select>
                    {localOptionsStatus === "error" ? (
                      <div
                        className="mt-2 flex items-center justify-between gap-3 text-sm text-[#9f2525]"
                        role="alert"
                      >
                        <span>Không thể tải danh sách từ Cổng Dịch vụ công.</span>
                        <button
                          className="shrink-0 cursor-pointer font-semibold underline underline-offset-2 hover:text-[#6f1717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                          type="button"
                          onClick={() =>
                            void loadLocalOptions(
                              jurisdictionValue,
                              localAuthority,
                            )
                          }
                        >
                          Thử lại
                        </button>
                      </div>
                    ) : null}
                  </div>
                </>
              ) : null}

              <div className="mb-5">
                <button
                  className="flex h-10 w-full cursor-pointer items-center justify-center rounded-[4px] bg-[#CE7A58] px-5 text-[18px] font-medium text-white transition-opacity hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  type="submit"
                >
                  Tìm kiếm
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
