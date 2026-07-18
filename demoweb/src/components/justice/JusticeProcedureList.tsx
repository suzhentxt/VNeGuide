"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Search,
  X,
} from "lucide-react";
import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  standardMarriageExperience,
  type ProcedureExperience,
} from "@/data/procedure-experiences";
import {
  receptionUnits,
  withProcedureSelection,
} from "@/lib/procedure-selection";

const focusableSelector = [
  "button:not([disabled])",
  "a[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

interface FieldProps {
  children: React.ReactNode;
  label: string;
}

function Field({ children, label }: FieldProps) {
  return (
    <label className="block space-y-2">
      <span className="block text-sm font-semibold text-[#637381]">
        {label} <span className="text-red-500">*</span>
      </span>
      {children}
    </label>
  );
}

export function JusticeProcedureList({
  experience = standardMarriageExperience,
  initialReceptionUnit,
  initialServiceId,
}: {
  experience?: ProcedureExperience;
  initialReceptionUnit?: string;
  initialServiceId?: string;
}) {
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = useState(true);
  const [unitOpen, setUnitOpen] = useState(false);
  const [unitQuery, setUnitQuery] = useState("");
  const [selectedUnit, setSelectedUnit] = useState(() =>
    receptionUnits.includes(
      initialReceptionUnit as (typeof receptionUnits)[number],
    )
      ? initialReceptionUnit ?? ""
      : "",
  );
  const [selectedServiceId, setSelectedServiceId] = useState(() =>
    experience.services.some((service) => service.id === initialServiceId)
      ? initialServiceId ?? ""
      : "",
  );
  const [serviceError, setServiceError] = useState(false);
  const [unitError, setUnitError] = useState(false);
  const [searchQuery, setSearchQuery] = useState(experience.shortTitle);
  const [levelFilter, setLevelFilter] = useState("all");
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const openDialogButtonRef = useRef<HTMLButtonElement>(null);
  const unitSearchRef = useRef<HTMLInputElement>(null);

  const filteredUnits = useMemo(() => {
    const normalizedQuery = unitQuery.trim().toLocaleLowerCase("vi");

    if (!normalizedQuery) {
      return receptionUnits;
    }

    return receptionUnits.filter((unit) =>
      unit.toLocaleLowerCase("vi").includes(normalizedQuery),
    );
  }, [unitQuery]);

  const normalizedSearchQuery = searchQuery.trim().toLocaleLowerCase("vi");
  const procedureVisible =
    (levelFilter === "all" || levelFilter === "commune") &&
    (!normalizedSearchQuery ||
      experience.title.toLocaleLowerCase("vi").includes(normalizedSearchQuery) ||
      experience.shortTitle
        .toLocaleLowerCase("vi")
        .includes(normalizedSearchQuery) ||
      experience.code.toLocaleLowerCase("vi").includes(normalizedSearchQuery));

  useEffect(() => {
    if (!dialogOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    const returnFocusTarget = openDialogButtonRef.current;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      returnFocusTarget?.focus();
    };
  }, [dialogOpen]);

  useEffect(() => {
    if (unitOpen) {
      unitSearchRef.current?.focus();
    }
  }, [unitOpen]);

  const closeDialog = () => {
    setUnitOpen(false);
    setDialogOpen(false);
  };

  const handleDialogKeyDown = (
    event: ReactKeyboardEvent<HTMLDivElement>,
  ) => {
    if (event.key === "Escape") {
      event.preventDefault();
      if (unitOpen) {
        setUnitOpen(false);
      } else {
        closeDialog();
      }
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusableElements = dialogRef.current
      ? Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
        ).filter((element) => element.offsetParent !== null)
      : [];

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

  const handleConfirm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const service = experience.services.find(
      (candidate) => candidate.id === selectedServiceId,
    );

    if (!service) {
      setServiceError(true);
      return;
    }

    if (!selectedUnit) {
      setUnitError(true);
      setUnitOpen(true);
      return;
    }

    router.push(
      withProcedureSelection(experience.routes.submission, {
        receptionUnit: selectedUnit,
        serviceId: service.id,
      }, { confirmed: "1" }),
    );
  };

  return (
    <>
      <section className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-10 sm:px-8 lg:px-12 lg:py-16">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-2xl font-bold text-[#111827] sm:text-[28px]">
            Tra cứu thủ tục hành chính{" "}
            <span className="font-normal italic">
              ({procedureVisible ? 1 : 0} thủ tục)
            </span>
          </h1>
        </div>

        <div className="rounded-2xl border border-[#e6e9ee] bg-white p-5 shadow-[0_12px_32px_rgba(33,43,54,0.06)] sm:p-7">
          <form
            aria-label="Tìm kiếm thủ tục hành chính"
            className="space-y-5"
            role="search"
            onSubmit={(event) => event.preventDefault()}
          >
            <label className="relative block">
              <span className="sr-only">Tên thủ tục hành chính</span>
              <input
                className="h-14 w-full rounded-full border border-[#d9e0ea] bg-white px-6 pr-16 text-base outline-none transition placeholder:text-[#8b95a5] focus:border-[#ce7a58] focus:ring-2 focus:ring-[#ce7a58]/20"
                name="tu-khoa"
                placeholder="Nhập tên thủ tục hành chính cần tìm"
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
              <button
                aria-label="Tìm kiếm"
                className="absolute top-1/2 right-2 flex size-11 -translate-y-1/2 items-center justify-center rounded-full bg-[#903938] text-white transition-colors hover:bg-[#7d302f] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58]"
                type="submit"
              >
                <Search aria-hidden="true" className="size-5" />
              </button>
            </label>

            <label className="block max-w-[300px] space-y-2 text-sm font-semibold text-[#637381]">
              <span className="block">Cấp thực hiện</span>
              <span className="relative block">
                <select
                  className="h-14 w-full appearance-none rounded-xl border border-[#d9e0ea] bg-[#f8fafc] px-4 pr-10 text-base font-normal text-[#212b36] outline-none focus:border-[#ce7a58] focus:ring-2 focus:ring-[#ce7a58]/20"
                  name="cap-thuc-hien"
                  value={levelFilter}
                  onChange={(event) => setLevelFilter(event.target.value)}
                >
                  <option value="all">Tất cả</option>
                  <option value="commune">Cấp Xã</option>
                </select>
                <ChevronDown
                  aria-hidden="true"
                  className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2"
                />
              </span>
            </label>
          </form>

          <div className="mt-8 overflow-hidden rounded-xl border border-[#e3e8ef]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] border-collapse text-left">
                <thead className="bg-[#f5f7fa] text-sm font-semibold text-[#42526b]">
                  <tr>
                    <th className="px-5 py-4">Mã thủ tục</th>
                    <th className="px-5 py-4">Thủ tục hành chính</th>
                    <th className="px-5 py-4">Lĩnh vực</th>
                    <th className="px-5 py-4">Cấp thực hiện</th>
                    <th className="px-5 py-4 text-center">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {procedureVisible ? (
                    <tr className="border-t border-[#e3e8ef] bg-white align-middle">
                    <td className="px-5 py-6 font-semibold text-[#111827]">
                      {experience.code}
                    </td>
                    <td className="px-5 py-6">
                      <Link
                        className="inline-flex items-center gap-3 font-semibold text-[#23406e] hover:text-[#903938] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58]"
                        href={experience.routes.detail}
                      >
                        <FileText
                          aria-hidden="true"
                          className="size-5 shrink-0 text-[#1769aa]"
                        />
                        {experience.shortTitle}
                      </Link>
                    </td>
                    <td className="px-5 py-6">{experience.field}</td>
                    <td className="px-5 py-6">{experience.level}</td>
                    <td className="px-5 py-6 text-center">
                      <button
                        ref={openDialogButtonRef}
                        className="inline-flex h-11 items-center justify-center rounded-xl bg-[#ce7a58] px-5 font-semibold text-white transition-colors hover:bg-[#b86647] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                        type="button"
                        onClick={() => setDialogOpen(true)}
                      >
                        Nộp hồ sơ
                      </button>
                    </td>
                    </tr>
                  ) : (
                    <tr className="border-t border-[#e3e8ef] bg-white">
                      <td
                        className="px-5 py-10 text-center text-[#637381]"
                        colSpan={5}
                      >
                        Không tìm thấy thủ tục phù hợp.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 text-sm">
            <label className="inline-flex items-center gap-3 text-[#637381]">
              Số hàng/trang
              <select className="h-10 rounded-lg border border-[#d9e0ea] bg-white px-3 text-[#212b36] outline-none focus:border-[#ce7a58]">
                <option>10</option>
              </select>
            </label>

            <div className="flex items-center gap-3">
              <span className="font-semibold text-[#111827]">Trang 1/1</span>
              <div className="flex items-center gap-1">
                {[
                  { Icon: ChevronsLeft, label: "Trang đầu" },
                  { Icon: ChevronLeft, label: "Trang trước" },
                  { Icon: ChevronRight, label: "Trang sau" },
                  { Icon: ChevronsRight, label: "Trang cuối" },
                ].map(({ Icon, label }) => (
                  <button
                    aria-label={label}
                    className="flex size-10 items-center justify-center rounded-full border border-[#e3e8ef] text-[#98a1af]"
                    disabled
                    key={label}
                    type="button"
                  >
                    <Icon aria-hidden="true" className="size-4" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-center">
          <Link
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-[#ce7a58] px-5 font-semibold text-[#9b4b3b] transition-colors hover:bg-[#fff4ef] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
            href={experience.routes.services}
          >
            <ArrowLeft aria-hidden="true" className="size-4" />
            Quay lại
          </Link>
        </div>
      </section>

      {dialogOpen ? (
        <div
          aria-labelledby="justice-information-dialog-title"
          aria-modal="true"
          className="fixed inset-0 z-[200] flex items-center justify-center overflow-y-auto bg-black/75 p-3 sm:p-6"
          role="dialog"
          onKeyDown={handleDialogKeyDown}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDialog();
            }
          }}
        >
          <div
            ref={dialogRef}
            className="relative my-auto max-h-[calc(100vh-24px)] w-full max-w-[1000px] overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl sm:max-h-[calc(100vh-48px)] sm:p-8"
          >
            <div className="mb-7 flex items-start justify-between gap-4">
              <h2
                className="text-xl font-bold text-[#111827] sm:text-2xl"
                id="justice-information-dialog-title"
              >
                Thông tin chung
              </h2>
              <button
                ref={closeButtonRef}
                aria-label="Đóng hộp thoại"
                className="flex size-9 shrink-0 items-center justify-center rounded-full text-[#637381] transition-colors hover:bg-[#f3f5f7] hover:text-[#111827] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58]"
                type="button"
                onClick={closeDialog}
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>

            <form className="space-y-6" onSubmit={handleConfirm}>
              {unitOpen ? (
                <div className="rounded-2xl border border-[#d9e0ea] bg-white p-4 shadow-[0_8px_24px_rgba(33,43,54,0.12)] sm:p-5">
                  <label className="relative block border-b border-[#e3e8ef] pb-3">
                    <span className="sr-only">Tìm đơn vị tiếp nhận</span>
                    <Search
                      aria-hidden="true"
                      className="absolute top-1/2 left-3 size-5 -translate-y-[70%] text-[#637381]"
                    />
                    <input
                      ref={unitSearchRef}
                      className="h-11 w-full rounded-lg border-0 bg-transparent pr-3 pl-11 text-base outline-none placeholder:text-[#637381] focus:ring-2 focus:ring-[#ce7a58]/30"
                      placeholder="Tìm kiếm"
                      type="search"
                      value={unitQuery}
                      onChange={(event) => setUnitQuery(event.target.value)}
                    />
                  </label>

                  <div
                    aria-label="Danh sách đơn vị tiếp nhận"
                    className="mt-2 max-h-[370px] space-y-1 overflow-y-auto pr-1"
                    role="listbox"
                  >
                    {filteredUnits.length > 0 ? (
                      filteredUnits.map((unit) => (
                        <button
                          aria-selected={selectedUnit === unit}
                          className={`block w-full rounded-xl px-4 py-3 text-left text-base transition-colors hover:bg-[#eef2f7] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#ce7a58] ${
                            selectedUnit === unit
                              ? "bg-[#eef2f7] font-semibold"
                              : ""
                          }`}
                          key={unit}
                          role="option"
                          type="button"
                          onClick={() => {
                            setSelectedUnit(unit);
                            setUnitError(false);
                            setUnitOpen(false);
                            setUnitQuery("");
                          }}
                        >
                          {unit}
                        </button>
                      ))
                    ) : (
                      <p className="px-4 py-8 text-center text-[#637381]">
                        Không tìm thấy đơn vị phù hợp.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  <Field label="Cấp thực hiện">
                    <input
                      className="h-[52px] w-full rounded-xl border border-[#d9e0ea] bg-[#f8fafc] px-5 text-base text-[#212b36]"
                      readOnly
                      value={experience.level}
                    />
                  </Field>
                  <Field label="Thủ tục hành chính">
                    <input
                      className="h-[52px] w-full rounded-xl border border-[#d9e0ea] bg-[#f8fafc] px-5 text-base text-[#212b36]"
                      readOnly
                      value={experience.title}
                    />
                  </Field>
                  <Field label="Dịch vụ công">
                    <span className="relative block">
                      <select
                        aria-describedby={
                          serviceError ? "online-service-error" : undefined
                        }
                        className="min-h-[52px] w-full appearance-none rounded-xl border border-[#d9e0ea] bg-[#f8fafc] px-5 py-3 pr-12 text-base text-[#212b36] outline-none transition focus:border-[#ce7a58] focus:ring-2 focus:ring-[#ce7a58]/20"
                        required
                        value={selectedServiceId}
                        onChange={(event) => {
                          setSelectedServiceId(event.target.value);
                          setServiceError(false);
                        }}
                      >
                        <option disabled value="">
                          Chọn dịch vụ công
                        </option>
                        {experience.services.map((service) => (
                          <option key={service.id} value={service.id}>
                            {service.authority} — {service.level}
                          </option>
                        ))}
                      </select>
                      <ChevronDown
                        aria-hidden="true"
                        className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-[#637381]"
                      />
                    </span>
                    {serviceError ? (
                      <p
                        className="text-sm text-red-600"
                        id="online-service-error"
                        role="alert"
                      >
                        Vui lòng chọn dịch vụ công trước khi xác nhận.
                      </p>
                    ) : null}
                  </Field>
                </>
              )}

              <div className="space-y-2">
                <span className="block text-sm font-semibold text-[#637381]">
                  Đơn vị tiếp nhận <span className="text-red-500">*</span>
                </span>
                <button
                  aria-expanded={unitOpen}
                  aria-haspopup="listbox"
                  aria-describedby={unitError ? "reception-unit-error" : undefined}
                  className="flex min-h-[52px] w-full items-center justify-between gap-4 rounded-xl border border-[#d9e0ea] bg-[#f8fafc] px-5 py-3 text-left text-base outline-none transition hover:border-[#b7c0cd] focus-visible:border-[#ce7a58] focus-visible:ring-2 focus-visible:ring-[#ce7a58]/20"
                  type="button"
                  onClick={() => setUnitOpen((current) => !current)}
                >
                  <span
                    className={
                      selectedUnit ? "text-[#212b36]" : "text-[#637381]"
                    }
                  >
                    {selectedUnit || "Tìm kiếm"}
                  </span>
                  <ChevronDown
                    aria-hidden="true"
                    className={`size-4 shrink-0 text-[#637381] transition-transform ${
                      unitOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {unitError ? (
                  <p id="reception-unit-error" className="text-sm text-red-600" role="alert">
                    Vui lòng chọn đơn vị tiếp nhận trước khi xác nhận.
                  </p>
                ) : null}
              </div>

              <label className="block space-y-2">
                <span className="block text-sm font-semibold text-[#637381]">
                  Đối tượng thực hiện
                </span>
                <span className="relative block">
                  <select className="h-[52px] w-full appearance-none rounded-xl border border-[#d9e0ea] bg-white px-4 pr-12 text-base text-[#212b36] outline-none focus:border-[#ce7a58] focus:ring-2 focus:ring-[#ce7a58]/20">
                    <option>Làm thủ tục cho bản thân</option>
                    <option>Người khác ủy quyền</option>
                    <option>Doanh nghiệp ủy quyền</option>
                    <option>Làm thủ tục cho người khác</option>
                    <option>Đại diện cơ quan, tổ chức</option>
                  </select>
                  <ChevronDown
                    aria-hidden="true"
                    className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-[#637381]"
                  />
                </span>
              </label>

              <div className="flex items-center justify-between gap-4 pt-1">
                <button
                  className="h-12 rounded-xl border border-[#d9e0ea] bg-white px-6 font-semibold text-[#111827] transition-colors hover:bg-[#f5f7fa] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58]"
                  type="button"
                  onClick={closeDialog}
                >
                  Hủy
                </button>
                <button
                  className="h-12 rounded-xl bg-[#ce7a58] px-7 font-semibold text-white transition-colors hover:bg-[#b86647] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  type="submit"
                >
                  Xác nhận
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
