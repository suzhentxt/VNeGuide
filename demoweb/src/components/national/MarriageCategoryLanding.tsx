import Link from "next/link";
import {
  ChevronDown,
  FileText,
  HeartHandshake,
  Search,
} from "lucide-react";

import { marriageCategories, marriageRoutes } from "@/data/marriage";
import { procedureExperiences } from "@/data/procedure-experiences";

const procedureExperiencesByTitle = new Map(
  procedureExperiences.map((experience) => [experience.title, experience]),
);

export function MarriageCategoryLanding() {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 pb-10">
      <div className="mb-7 flex flex-col gap-3 lg:flex-row lg:items-center">
        <form
          action={marriageRoutes.services}
          className="flex min-w-0 flex-1 overflow-hidden rounded-lg border border-[#c9cdcf] bg-white shadow-sm focus-within:border-[#ce7a58] focus-within:ring-2 focus-within:ring-[#ce7a58]/20"
          role="search"
        >
          <label htmlFor="marriage-procedure-search" className="sr-only">
            Tìm kiếm thủ tục hôn nhân và gia đình
          </label>
          <input
            id="marriage-procedure-search"
            name="q"
            type="search"
            placeholder="Nhập từ khóa tìm kiếm thủ tục hành chính"
            className="h-12 min-w-0 flex-1 px-4 text-base outline-none placeholder:text-[#8f969c]"
          />
          <button
            type="submit"
            className="flex w-14 cursor-pointer items-center justify-center bg-[#ce7a58] text-white hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-white"
            aria-label="Tìm kiếm"
          >
            <Search className="size-5" aria-hidden="true" />
          </button>
        </form>
        <Link
          href={marriageRoutes.services}
          className="flex h-12 shrink-0 items-center justify-center rounded-lg bg-[#ffc251] px-6 font-semibold text-[#1e2f41] shadow-sm hover:bg-[#f5b938] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
        >
          Dịch vụ công trực tuyến
        </Link>
      </div>

      <section aria-labelledby="marriage-category-title">
        <div className="flex items-stretch gap-3 sm:gap-4">
          <div className="flex size-16 shrink-0 items-center justify-center rounded-lg bg-[#ce7a58] text-white shadow-lg sm:size-20 md:size-[100px]">
            <HeartHandshake className="size-9 sm:size-11 md:size-14" aria-hidden="true" />
          </div>
          <div
            className="flex min-h-16 flex-1 items-center overflow-hidden rounded-lg bg-[#ffc600]/15 bg-cover bg-right bg-no-repeat px-4 sm:min-h-20 md:min-h-[100px]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,198,0,.13), rgba(255,198,0,.13)), url('/target/p/home/theme/img/hac.svg')",
            }}
          >
            <h1
              id="marriage-category-title"
              className="text-xl font-semibold text-[#1e2f41] sm:text-2xl"
            >
              Hôn nhân và gia đình
            </h1>
          </div>
        </div>
        <p className="mt-4 max-w-2xl text-center text-sm leading-relaxed text-[#4b5563] sm:text-left sm:text-base">
          Cung cấp thông tin thủ tục hành chính, dịch vụ công trực tiếp liên quan.
        </p>
      </section>

      <section className="mt-8" aria-labelledby="marriage-procedures-heading">
        <h2 id="marriage-procedures-heading" className="sr-only">
          Danh mục thủ tục hôn nhân và gia đình
        </h2>
        <div className="divide-y divide-[#e5e7eb] border-y border-[#e5e7eb]">
          {marriageCategories.map((category, index) => (
            <details key={category.title} className="group py-2" open={index === 0}>
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-lg p-3 text-left hover:bg-[#f9fafb] focus-visible:outline-2 focus-visible:outline-[#ce7a58] [&::-webkit-details-marker]:hidden">
                <span className="text-lg font-semibold text-[#1f2937] sm:text-xl">
                  {category.title}
                </span>
                <ChevronDown
                  className="size-5 shrink-0 text-[#9ca3af] transition-transform group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <ul className="ml-2 pb-3 sm:ml-6 lg:ml-8">
                {category.procedures.map((procedure) => {
                  const experience = procedureExperiencesByTitle.get(procedure);

                  return (
                    <li key={procedure}>
                      {experience ? (
                        <Link
                          href={experience.routes.services}
                          className="group/link flex items-start gap-3 rounded-md px-2 py-3 text-sm leading-relaxed text-[#4b5563] hover:bg-[#ce7a58]/5 hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58] sm:text-base lg:text-lg"
                          data-integration-status="integrated"
                        >
                          <FileText
                            className="mt-0.5 size-5 shrink-0 text-[#ce7a58]"
                            aria-hidden="true"
                          />
                          <span>{procedure}</span>
                        </Link>
                      ) : (
                        <div
                          className="flex items-start gap-3 rounded-md px-2 py-3 text-sm leading-relaxed text-[#6b7280] sm:text-base lg:text-lg"
                          data-integration-status="pending"
                        >
                          <FileText
                            className="mt-0.5 size-5 shrink-0 text-[#9ca3af]"
                            aria-hidden="true"
                          />
                          <span className="min-w-0 flex-1">{procedure}</span>
                          <span className="mt-0.5 shrink-0 rounded-full bg-[#f3f4f6] px-2.5 py-0.5 text-xs font-semibold text-[#6b7280] sm:text-sm">
                            Chưa tích hợp
                          </span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          ))}
        </div>
      </section>

      <div className="text-center">
        <Link
          href={marriageRoutes.services}
          className="mt-7 inline-flex w-full items-center justify-center rounded-lg bg-[#ce7a58] px-8 py-3 font-semibold text-white shadow-md transition hover:bg-[#b96749] hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938] sm:w-auto"
        >
          Xem tất cả thủ tục hành chính
        </Link>
      </div>

      <section className="mt-10" aria-labelledby="marriage-faq-title">
        <h2 id="marriage-faq-title" className="mb-4 text-xl font-semibold">
          Câu hỏi thường gặp
        </h2>
        <div className="space-y-3">
          <details className="group rounded-lg border border-[#e2e2e2] bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-4 font-medium focus-visible:outline-2 focus-visible:outline-[#ce7a58] [&::-webkit-details-marker]:hidden">
              Có thể nộp hồ sơ đăng ký kết hôn trực tuyến không?
              <ChevronDown
                className="size-5 shrink-0 text-[#ce7a58] transition-transform group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <p className="border-t border-[#e5e7eb] px-4 py-3 leading-relaxed text-[#4b5563]">
              Có. Người yêu cầu có thể kê khai mẫu hộ tịch điện tử, đính kèm tài liệu và theo dõi hồ sơ trực tuyến trên Cổng Dịch vụ công.
            </p>
          </details>
          <details className="group rounded-lg border border-[#e2e2e2] bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-4 font-medium focus-visible:outline-2 focus-visible:outline-[#ce7a58] [&::-webkit-details-marker]:hidden">
              Hai bên có cần trực tiếp nhận kết quả không?
              <ChevronDown
                className="size-5 shrink-0 text-[#ce7a58] transition-transform group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <p className="border-t border-[#e5e7eb] px-4 py-3 leading-relaxed text-[#4b5563]">
              Hai bên nam, nữ phải có mặt để đối chiếu giấy tờ, xác nhận sự tự nguyện kết hôn và ký Giấy chứng nhận kết hôn.
            </p>
          </details>
        </div>
      </section>
    </div>
  );
}
