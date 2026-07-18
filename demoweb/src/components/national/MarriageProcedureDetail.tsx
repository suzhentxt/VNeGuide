import Link from "next/link";
import type { ReactNode } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  MessageCircleMore,
  Scale,
} from "lucide-react";

import type {
  DossierItem,
  ImplementationMethod,
  MetadataField,
} from "@/data/marriage";
import {
  standardMarriageExperience,
  type ProcedureExperience,
} from "@/data/procedure-experiences";
import {
  AgencySidebar,
  PopularProcedures,
} from "@/components/national/NationalSidebars";

interface DetailAccordionProps {
  id: string;
  title: string;
  children: ReactNode;
  open?: boolean;
}

function DetailAccordion({
  id,
  title,
  children,
  open = false,
}: DetailAccordionProps) {
  return (
    <details className="group border-b border-[#e2e2e2]" open={open}>
      <summary
        id={`${id}-summary`}
        className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-left text-lg font-bold text-[#903938] hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58] [&::-webkit-details-marker]:hidden"
      >
        {title}
        <ChevronDown
          className="size-5 shrink-0 transition-transform group-open:rotate-180"
          aria-hidden="true"
        />
      </summary>
      <div className="pb-5" aria-labelledby={`${id}-summary`}>
        {children}
      </div>
    </details>
  );
}

function MetadataGrid({ fields }: { fields: readonly MetadataField[] }) {
  return (
    <dl className="grid grid-cols-1 border-t border-l border-[#d1d5db] md:grid-cols-2">
      {fields.map((field) => (
        <div
          key={field.label}
          className={`grid min-w-0 grid-cols-1 border-r border-b border-[#d1d5db] sm:grid-cols-[minmax(145px,36%)_1fr] ${
            field.wide ? "md:col-span-2 md:grid-cols-[minmax(190px,25%)_1fr]" : ""
          }`}
        >
          <dt className="bg-[#f3f3f3]/70 px-3 py-2 font-bold text-[#374151] sm:border-r sm:border-[#d1d5db]">
            {field.label}
          </dt>
          <dd className="min-w-0 px-3 py-2 text-[#1f2937]">{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ImplementationTable({
  methods,
}: {
  methods: readonly ImplementationMethod[];
}) {
  return (
    <div className="overflow-x-auto rounded-sm border border-[#d1d5db]">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <caption className="sr-only">Các cách thức thực hiện thủ tục</caption>
        <thead>
          <tr className="border-b-2 border-[#ce7a58] bg-[#e5e7eb] text-[#1e293b]">
            <th scope="col" className="w-[18%] border-r border-[#d1d5db] px-4 py-3 font-semibold">
              Hình thức nộp
            </th>
            <th scope="col" className="w-[15%] border-r border-[#d1d5db] px-4 py-3 font-semibold">
              Thời gian
            </th>
            <th scope="col" className="w-[15%] border-r border-[#d1d5db] px-4 py-3 font-semibold">
              Phí, lệ phí
            </th>
            <th scope="col" className="px-4 py-3 font-semibold">
              Mô tả
            </th>
          </tr>
        </thead>
        <tbody>
          {methods.map((method) => (
            <tr key={method.method} className="border-b border-[#d1d5db] last:border-b-0">
              <th scope="row" className="border-r border-[#d1d5db] px-4 py-3 font-medium">
                {method.method}
              </th>
              <td className="border-r border-[#d1d5db] px-4 py-3">{method.duration}</td>
              <td className="border-r border-[#d1d5db] px-4 py-3 text-[#166534]">
                {method.fee}
              </td>
              <td className="px-4 py-3 text-sm leading-relaxed text-[#4b5563]">
                {method.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DossierTable({ items }: { items: readonly DossierItem[] }) {
  return (
    <div className="overflow-x-auto rounded-sm border border-[#d1d5db]">
      <table className="w-full min-w-[620px] border-collapse text-left">
        <caption className="sr-only">Thành phần hồ sơ thủ tục</caption>
        <thead>
          <tr className="border-b-2 border-[#ce7a58] bg-[#e5e7eb]">
            <th scope="col" className="w-16 border-r border-[#d1d5db] px-4 py-3 text-center">
              STT
            </th>
            <th scope="col" className="border-r border-[#d1d5db] px-4 py-3">
              Tên giấy tờ
            </th>
            <th scope="col" className="w-36 px-4 py-3">
              Số lượng
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.name} className="border-b border-[#d1d5db] align-top last:border-b-0">
              <td className="border-r border-[#d1d5db] px-4 py-3 text-center">{index + 1}</td>
              <td className="border-r border-[#d1d5db] px-4 py-3 leading-relaxed">
                {item.name}
              </td>
              <td className="px-4 py-3">{item.quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MarriageProcedureDetail({
  experience = standardMarriageExperience,
}: {
  experience?: ProcedureExperience;
}) {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 pb-10">
      <div className="grid grid-cols-1 gap-7 md:grid-cols-12">
        <article className="order-2 min-w-0 md:order-1 md:col-span-8" aria-labelledby="procedure-title">
          <h1 id="procedure-title" className="text-2xl font-semibold text-[#1f2937]">
            {experience.title}
          </h1>

          <div className="mt-4 flex flex-col justify-between gap-4 border-b border-[#d1d5db] pb-4 sm:flex-row sm:items-start">
            <div className="space-y-2">
              <a
                href="https://dichvucong.gov.vn/phan-anh-kien-nghi"
                className="group flex items-center gap-2 font-semibold hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
              >
                <ChevronRight className="size-4 text-[#ce7a58]" aria-hidden="true" />
                Gửi phản ánh kiến nghị
              </a>
              <a
                href="https://dichvucong.gov.vn/tham-van-thu-tuc-hanh-chinh"
                className="group flex items-center gap-2 font-semibold hover:text-[#ce7a58] focus-visible:outline-2 focus-visible:outline-[#ce7a58]"
              >
                <ChevronRight className="size-4 text-[#ce7a58]" aria-hidden="true" />
                Gửi ý kiến tham vấn
              </a>
            </div>
            <div className="flex items-center gap-2 text-sm text-[#6b7280]">
              <FileText className="size-5 text-[#dc2626]" aria-hidden="true" />
              Mã thủ tục: <strong className="text-[#1e2f41]">{experience.code}</strong>
            </div>
          </div>

          <section className="mt-5" aria-labelledby="procedure-metadata-title">
            <h2 id="procedure-metadata-title" className="sr-only">
              Thông tin thủ tục
            </h2>
            <MetadataGrid fields={experience.metadata} />
          </section>

          <section className="mt-6" aria-label="Nội dung chi tiết thủ tục">
            <DetailAccordion id="execution-order" title="Trình tự thực hiện" open>
              <ol className="space-y-3 pl-1">
                {experience.steps.map((step, index) => (
                  <li key={step} className="flex items-start gap-3 leading-relaxed text-[#374151]">
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[#ce7a58]/15 text-sm font-bold text-[#903938]">
                      {index + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </DetailAccordion>

            <DetailAccordion id="implementation-methods" title="Cách thức thực hiện" open>
              <ImplementationTable methods={experience.methods} />
            </DetailAccordion>

            <DetailAccordion id="dossier" title="Thành phần hồ sơ" open>
              <p className="mb-3 font-semibold text-[#374151]">Giấy tờ phải xuất trình và nộp:</p>
              <DossierTable items={experience.nationalDossier} />
            </DetailAccordion>

            <DetailAccordion id="conditions" title="Yêu cầu, điều kiện thực hiện">
              <ul className="space-y-3">
                {experience.conditions.map((condition) => (
                  <li key={condition} className="flex items-start gap-3 leading-relaxed text-[#374151]">
                    <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-[#166534]" aria-hidden="true" />
                    {condition}
                  </li>
                ))}
              </ul>
            </DetailAccordion>

            <DetailAccordion id="agency" title="Cơ quan thực hiện">
              <p className="leading-relaxed text-[#374151]">
                {experience.performingAgency}
              </p>
            </DetailAccordion>

            <DetailAccordion id="legal-bases" title="Căn cứ pháp lý">
              <ul className="space-y-3">
                {experience.legalBases.map((basis) => (
                  <li key={basis} className="flex items-start gap-3 leading-relaxed text-[#374151]">
                    <Scale className="mt-0.5 size-5 shrink-0 text-[#ce7a58]" aria-hidden="true" />
                    {basis}
                  </li>
                ))}
              </ul>
            </DetailAccordion>

            <DetailAccordion id="result" title="Kết quả thực hiện">
              <div className="flex items-start gap-3 rounded-lg bg-[#f0fdf4] p-4 text-[#166534]">
                <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <div className="leading-relaxed">
                  <p className="font-semibold">{experience.result.label}</p>
                  <p className="mt-1 text-sm">Mã kết quả: {experience.result.code}</p>
                </div>
              </div>
            </DetailAccordion>

            <DetailAccordion id="keywords" title="Từ khóa">
              <p className="text-[#4b5563]">Không có thông tin</p>
            </DetailAccordion>

            <DetailAccordion id="description" title="Mô tả">
              <p className="text-[#4b5563]">Không có thông tin</p>
            </DetailAccordion>
          </section>

          <div className="mt-7 flex flex-col items-stretch justify-between gap-3 rounded-lg bg-[#f9fafb] p-4 sm:flex-row sm:items-center">
            <p className="flex items-center gap-2 font-medium text-[#374151]">
              <MessageCircleMore className="size-5 text-[#ce7a58]" aria-hidden="true" />
              Bạn đã sẵn sàng thực hiện thủ tục?
            </p>
            <Link
              href="#agency-filter-title"
              className="inline-flex h-11 items-center justify-center rounded bg-[#ce7a58] px-6 font-semibold text-white shadow-sm hover:bg-[#b96749] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#903938]"
            >
              Chọn cơ quan để nộp
            </Link>
          </div>
        </article>

        <div className="order-1 space-y-4 md:order-2 md:col-span-4">
          <AgencySidebar
            actionHref={experience.routes.submission}
            actionLabel="Nộp hồ sơ"
            serviceId={experience.services[0].id}
          />
          <PopularProcedures />
        </div>
      </div>
    </div>
  );
}
