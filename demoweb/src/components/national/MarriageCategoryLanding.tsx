import { ArrowRight, Bot, FileCheck2, Home, Search } from "lucide-react";
import Link from "next/link";

import { marriageRoutes } from "@/data/marriage";
import { procedureExperiences } from "@/data/procedure-experiences";

const icons = [Home, FileCheck2, FileCheck2] as const;

export function MarriageCategoryLanding() {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 pb-12">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-[#762b2b] via-[#903938] to-[#bd654b] px-5 py-8 text-white shadow-xl sm:px-10 sm:py-12">
        <div className="grid items-center gap-8 lg:grid-cols-[1fr_320px]">
          <div>
            <p className="text-sm font-bold tracking-[0.16em] text-[#ffe2b7] uppercase">VNeGuide · Phạm vi đã xác minh</p>
            <h1 className="mt-3 max-w-3xl text-3xl font-extrabold leading-tight sm:text-5xl">
              Chuẩn bị hồ sơ cùng form và trợ lý AI
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/90 sm:text-lg">
              Demo chỉ hỗ trợ đúng ba thủ tục dưới đây. Form là nguồn dữ liệu chính; AI đề xuất nhưng không tự thay đổi thông tin bạn đã xác nhận.
            </p>
            <form action={marriageRoutes.services} className="mt-6 flex max-w-2xl overflow-hidden rounded-xl bg-white shadow-lg" role="search">
              <label className="sr-only" htmlFor="supported-procedure-search">Tìm trong ba thủ tục được hỗ trợ</label>
              <input className="min-h-13 min-w-0 flex-1 px-4 text-[#1e2f41] outline-none" id="supported-procedure-search" name="q" placeholder="Tìm theo tên hoặc mã thủ tục" type="search" />
              <button aria-label="Tìm kiếm" className="flex w-14 items-center justify-center bg-[#ffc251] text-[#1e2f41]" type="submit">
                <Search className="size-5" aria-hidden="true" />
              </button>
            </form>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-6 backdrop-blur-sm">
            <Bot className="size-10 text-[#ffc251]" aria-hidden="true" />
            <h2 className="mt-4 text-xl font-extrabold">Hero: Đăng ký tạm trú</h2>
            <p className="mt-2 leading-6 text-white/85">Luồng 1.004194 có form CT01 mô phỏng, validation cạnh field, suggestion Accept/Reject/Edit và phục hồi sau refresh.</p>
            <Link className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#ffc251] px-4 font-bold text-[#1e2f41]" href="/hon-nhan-va-gia-dinh/dang-ky-tam-tru/to-khai?service=temporary-residence-guidance&receptionUnit=Trung+t%C3%A2m+ph%E1%BB%A5c+v%E1%BB%A5+h%C3%A0nh+ch%C3%ADnh+c%C3%B4ng%2C+Th%C3%A0nh+ph%E1%BB%91+H%C3%A0+N%E1%BB%99i">
              Mở form tạm trú <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <section className="mt-9" aria-labelledby="supported-procedures-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-[#903938]">Không suy đoán ngoài data package</p>
            <h2 className="mt-1 text-2xl font-extrabold text-[#1e2f41]" id="supported-procedures-title">3 thủ tục đang hoạt động</h2>
          </div>
          <Link className="font-bold text-[#903938] underline underline-offset-4" href={marriageRoutes.services}>Xem dạng danh sách</Link>
        </div>

        <div className="mt-5 grid gap-5 md:grid-cols-3">
          {procedureExperiences.map((experience, index) => {
            const Icon = icons[index];
            const hero = experience.code === "1.004194";
            return (
              <article className={`flex flex-col rounded-2xl border bg-white p-5 shadow-sm ${hero ? "border-[#ce7a58] ring-2 ring-[#ce7a58]/15" : "border-[#dce3ea]"}`} key={experience.code}>
                <div className="flex items-start justify-between gap-3">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-[#fff2ed] text-[#903938]"><Icon className="size-5" aria-hidden="true" /></span>
                  {hero ? <span className="rounded-full bg-[#903938] px-3 py-1 text-xs font-bold text-white">Hero flow</span> : null}
                </div>
                <p className="mt-5 text-sm font-bold text-[#903938]">Mã {experience.code}</p>
                <h3 className="mt-1 text-lg font-extrabold leading-7 text-[#1e2f41]">{experience.shortTitle}</h3>
                <p className="mt-3 flex-1 text-sm leading-6 text-[#637381]">{experience.competentAuthority}</p>
                <Link className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[#903938] px-4 font-bold text-[#903938] hover:bg-[#903938] hover:text-white" href={experience.routes.detail}>
                  Xem hướng dẫn <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
