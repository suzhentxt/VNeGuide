import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  ChevronDown,
  Search,
  UsersRound,
} from "lucide-react";

import { marriageRoutes, type MarriageService } from "@/data/marriage";
import {
  standardMarriageExperience,
  type ProcedureExperience,
} from "@/data/procedure-experiences";
import { AgencySidebar } from "@/components/national/NationalSidebars";
import { withProcedureSelection } from "@/lib/procedure-selection";

interface ServiceEntry {
  experience: ProcedureExperience;
  service: MarriageService;
}

function normalizeSearchText(value: string): string {
  return value
    .toLocaleLowerCase("vi")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .trim();
}

function matchesQuery({ experience, service }: ServiceEntry, query: string) {
  if (!query) {
    return true;
  }

  return normalizeSearchText(
    [
      service.title,
      experience.title,
      experience.shortTitle,
      experience.code,
      service.authority,
      experience.competentAuthority,
      experience.performingAgency,
    ].join(" "),
  ).includes(query);
}

function ServiceCard({
  experience,
  service,
}: {
  experience: ProcedureExperience;
  service: MarriageService;
}) {
  return (
    <article className="border-t border-[#d1d5db] py-5 first:border-t-0 first:pt-0">
      <Link
        href={experience.routes.detail}
        className="inline-block rounded-sm text-xl font-semibold text-[#1e2f41] hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ce7a58]"
      >
        {service.title}
      </Link>

      <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-12">
        <div className="space-y-2 md:col-span-3">
          <p className="flex items-center gap-2 font-medium text-[#166534]">
            <BadgeCheck className="size-4 shrink-0" aria-hidden="true" />
            {service.level}
          </p>
          <details className="group relative">
            <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-left text-[#ce7a58] hover:underline focus-visible:outline-2 focus-visible:outline-[#ce7a58] [&::-webkit-details-marker]:hidden">
              Xem Phí/ Lệ phí
              <ChevronDown
                className="size-3.5 transition-transform group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <p className="mt-2 rounded-md bg-[#f9fafb] p-3 text-sm leading-relaxed text-[#4b5563] md:absolute md:z-10 md:max-w-sm md:border md:border-[#e5e7eb] md:bg-white md:shadow-lg">
              {service.fee}
            </p>
          </details>
        </div>

        <div className="space-y-2 md:col-span-6">
          <p className="text-sm font-semibold text-[#4b5563]">
            Mã thủ tục: {experience.code}
          </p>
          <p className="font-medium text-[#166534]">
            Cơ quan thực hiện: {service.authority}
          </p>
          <p className="flex items-center gap-2 text-[#ce7a58]">
            <UsersRound className="size-4 shrink-0" aria-hidden="true" />
            Đối tượng: {service.audience}
          </p>
        </div>

        <div className="flex md:col-span-3 md:justify-end">
          <Link
            href={withProcedureSelection(experience.routes.apply, {
              serviceId: service.id,
            })}
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded bg-[#ce7a58] px-4 font-semibold text-white shadow-sm hover:bg-[#b96749] hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] md:w-auto"
          >
            Nộp trực tuyến
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </article>
  );
}

export function MarriageServiceDirectory({
  experience = standardMarriageExperience,
  experiences,
  query = "",
}: {
  experience?: ProcedureExperience;
  experiences?: readonly ProcedureExperience[];
  query?: string;
}) {
  const directoryExperiences = experiences ?? [experience];
  const normalizedQuery = normalizeSearchText(query);
  const serviceEntries = directoryExperiences
    .flatMap((currentExperience) =>
      currentExperience.services.map((service) => ({
        experience: currentExperience,
        service,
      })),
    )
    .filter((entry) => matchesQuery(entry, normalizedQuery));
  const actionHref = experiences
    ? marriageRoutes.services
    : experience.routes.services;

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 pb-10">
      <div className="grid grid-cols-1 gap-7 md:grid-cols-12">
        <section className="order-2 min-w-0 md:order-1 md:col-span-8" aria-labelledby="service-directory-title">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 id="service-directory-title" className="text-2xl font-semibold sm:text-3xl">
                Danh sách dịch vụ công
              </h1>
              <p className="mt-2 text-sm text-[#6b7280]">
                Tìm thấy {serviceEntries.length} dịch vụ phù hợp
              </p>
            </div>
            <Link
              href="/hon-nhan-va-gia-dinh"
              className="rounded-sm text-sm font-medium text-[#ce7a58] hover:underline focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
            >
              Xem nhóm Hôn nhân và gia đình
            </Link>
          </div>

          <form
            action={actionHref}
            className="mb-5 flex overflow-hidden rounded-lg border border-[#c9cdcf] bg-white shadow-sm focus-within:border-[#ce7a58] focus-within:ring-2 focus-within:ring-[#ce7a58]/20"
            method="get"
            role="search"
          >
            <label htmlFor="service-directory-search" className="sr-only">
              Tìm kiếm dịch vụ theo tên, mã thủ tục hoặc cơ quan
            </label>
            <input
              id="service-directory-search"
              className="h-12 min-w-0 flex-1 px-4 outline-none placeholder:text-[#8f969c]"
              defaultValue={query}
              name="q"
              placeholder="Tìm theo tên, mã thủ tục hoặc cơ quan"
              type="search"
            />
            <button
              aria-label="Tìm kiếm dịch vụ công"
              className="flex w-14 cursor-pointer items-center justify-center bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-white"
              type="submit"
            >
              <Search className="size-5" aria-hidden="true" />
            </button>
          </form>

          <div className="border-y border-[#d1d5db] py-5">
            {serviceEntries.length > 0 ? (
              serviceEntries.map((entry) => (
                <ServiceCard
                  experience={entry.experience}
                  key={`${entry.experience.slug}:${entry.service.id}`}
                  service={entry.service}
                />
              ))
            ) : (
              <div className="py-10 text-center" role="status">
                <p className="font-semibold text-[#1e2f41]">
                  Không tìm thấy dịch vụ phù hợp
                </p>
                <p className="mt-2 text-sm text-[#6b7280]">
                  Hãy thử tên thủ tục, mã thủ tục hoặc tên cơ quan khác.
                </p>
                <Link
                  className="mt-4 inline-flex rounded border border-[#ce7a58] px-4 py-2 text-sm font-semibold text-[#ce7a58] hover:bg-[#ce7a58] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
                  href={actionHref}
                >
                  Xóa bộ lọc
                </Link>
              </div>
            )}
          </div>
        </section>

        <div className="order-1 md:order-2 md:col-span-4">
          <AgencySidebar actionHref={actionHref} />
        </div>
      </div>
    </div>
  );
}
