"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronRight, Landmark, MapPin, Search } from "lucide-react";

import {
  ministryOptions,
  parsePortalOptionsPayload,
  type PortalOption,
  provinceOptions,
} from "@/data/portal-authorities";
import { marriageRoutes, popularProcedures } from "@/data/marriage";

interface AgencySidebarProps {
  actionLabel?: "Đồng ý" | "Nộp hồ sơ";
  actionHref?: string;
}

type Jurisdiction = "province" | "ministry";
type LocalAuthority = "ward" | "department";
type OptionsStatus = "idle" | "loading" | "ready" | "error";

const LOCAL_OPTIONS_TIMEOUT_MS = 12_000;

export function AgencySidebar({
  actionLabel = "Đồng ý",
  actionHref = marriageRoutes.apply,
}: AgencySidebarProps) {
  const [jurisdiction, setJurisdiction] =
    useState<Jurisdiction>("province");
  const [localAuthority, setLocalAuthority] =
    useState<LocalAuthority>("ward");
  const [jurisdictionValue, setJurisdictionValue] = useState("");
  const [localAuthorityValue, setLocalAuthorityValue] = useState("");
  const [localOptions, setLocalOptions] = useState<PortalOption[]>([]);
  const [localOptionsStatus, setLocalOptionsStatus] =
    useState<OptionsStatus>("idle");
  const localOptionsRequestRef = useRef<AbortController | null>(null);

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

        const payload: unknown = await response.json();
        const options = parsePortalOptionsPayload(payload);
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

  const jurisdictionOptions =
    jurisdiction === "province" ? provinceOptions : ministryOptions;

  return (
    <aside
      className="h-fit overflow-hidden rounded-sm border border-[#e2e2e2] bg-white"
      aria-labelledby="agency-filter-title"
    >
      <h2
        id="agency-filter-title"
        className="bg-[#1e2f41]/10 px-4 py-3 text-lg font-semibold"
      >
        Chọn cơ quan thực hiện
      </h2>
      <form action={actionHref} className="space-y-4 p-4" method="get">
        <fieldset>
          <legend className="sr-only">Cấp cơ quan thực hiện</legend>
          <div className="flex flex-wrap gap-x-6 gap-y-3">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                checked={jurisdiction === "province"}
                type="radio"
                name="national-agency-level"
                value="province"
                className="size-4 accent-[#ce7a58]"
                onChange={() => {
                  setJurisdiction("province");
                  setJurisdictionValue("");
                  setLocalAuthority("ward");
                  void loadLocalOptions("", "ward");
                }}
              />
              <span>Tỉnh/ Thành phố</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                checked={jurisdiction === "ministry"}
                type="radio"
                name="national-agency-level"
                value="ministry"
                className="size-4 accent-[#ce7a58]"
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

        <label className="block space-y-1.5">
          <span className="font-medium">
            {jurisdiction === "province" ? "Tỉnh/ Thành phố" : "Bộ ngành"}
          </span>
          <span className="relative block">
            <MapPin
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[#6b7280]"
              aria-hidden="true"
            />
            <select
              required
              value={jurisdictionValue}
              name={jurisdiction === "province" ? "tinh-thanh" : "bo-nganh"}
              className="h-11 w-full appearance-none rounded border border-[#d1d5db] bg-white pr-9 pl-9 focus:border-[#ce7a58] focus:outline-none focus:ring-2 focus:ring-[#ce7a58]/25"
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
              {jurisdictionOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </span>
        </label>

        {jurisdiction === "province" ? (
          <>
            <fieldset>
              <legend className="sr-only">Loại đơn vị trực thuộc</legend>
              <div className="flex flex-wrap gap-x-8 gap-y-3">
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    checked={localAuthority === "ward"}
                    type="radio"
                    name="national-local-level"
                    value="ward"
                    className="size-4 accent-[#ce7a58]"
                    onChange={() => {
                      setLocalAuthority("ward");
                      void loadLocalOptions(jurisdictionValue, "ward");
                    }}
                  />
                  <span>Phường/ Xã</span>
                </label>
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    checked={localAuthority === "department"}
                    type="radio"
                    name="national-local-level"
                    value="department"
                    className="size-4 accent-[#ce7a58]"
                    onChange={() => {
                      setLocalAuthority("department");
                      void loadLocalOptions(jurisdictionValue, "department");
                    }}
                  />
                  <span>Sở</span>
                </label>
              </div>
            </fieldset>

            <label className="block space-y-1.5">
              <span className="font-medium">Cơ quan</span>
              <span className="relative block">
                <Landmark
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[#6b7280]"
                  aria-hidden="true"
                />
                <select
                  value={localAuthorityValue}
                  name="co-quan"
                  aria-busy={localOptionsStatus === "loading"}
                  disabled={
                    !jurisdictionValue || localOptionsStatus === "loading"
                  }
                  className="h-11 w-full appearance-none rounded border border-[#d1d5db] bg-white pr-9 pl-9 focus:border-[#ce7a58] focus:outline-none focus:ring-2 focus:ring-[#ce7a58]/25 disabled:cursor-not-allowed disabled:bg-[#f3f4f6]"
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
              </span>
            </label>

            {localOptionsStatus === "error" ? (
              <div
                className="flex items-center justify-between gap-3 text-sm text-[#9f2525]"
                role="alert"
              >
                <span>Không thể tải danh sách cơ quan.</span>
                <button
                  className="shrink-0 cursor-pointer font-semibold underline underline-offset-2 hover:text-[#6f1717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  type="button"
                  onClick={() =>
                    void loadLocalOptions(jurisdictionValue, localAuthority)
                  }
                >
                  Thử lại
                </button>
              </div>
            ) : null}
          </>
        ) : null}

        <p className="text-sm leading-relaxed text-[#dc2626]">
          Hệ thống chỉ hiển thị những cơ quan đã áp dụng dịch vụ công trực tuyến.
        </p>

        <button
          type="submit"
          className="flex h-11 w-full cursor-pointer items-center justify-center rounded bg-[#ce7a58] px-4 font-semibold text-white shadow-sm hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
        >
          {actionLabel}
        </button>
      </form>
    </aside>
  );
}

export function PopularProcedures() {
  return (
    <aside
      className="hidden h-fit overflow-hidden rounded-sm border border-[#e2e2e2] bg-white md:block"
      aria-labelledby="popular-procedures-title"
    >
      <h2
        id="popular-procedures-title"
        className="bg-[#1e2f41]/10 px-4 py-3 text-lg font-semibold"
      >
        Tìm kiếm nhiều nhất
      </h2>
      <ul className="divide-y divide-[#e5e7eb] px-4">
        {popularProcedures.map((procedure) => (
          <li key={procedure}>
            <a
              href="#tim-kiem-nhieu-nhat"
              className="group flex gap-3 py-3 text-sm leading-[1.35] font-semibold hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
            >
              <ChevronRight
                className="mt-0.5 size-3.5 shrink-0 text-[#ce7a58]"
                aria-hidden="true"
              />
              <span className="line-clamp-3">{procedure}</span>
            </a>
          </li>
        ))}
      </ul>
      <div className="border-t border-[#e5e7eb] p-3">
        <a
          href="#tim-kiem"
          className="flex items-center justify-center gap-2 rounded border border-[#ce7a58] px-3 py-2 text-sm font-semibold text-[#ce7a58] hover:bg-[#ce7a58] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
        >
          <Search className="size-4" aria-hidden="true" />
          Tìm thủ tục khác
        </a>
      </div>
    </aside>
  );
}
