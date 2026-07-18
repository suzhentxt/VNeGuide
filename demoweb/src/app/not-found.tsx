import Link from "next/link";

import { PortalFooter } from "@/components/PortalFooter";
import { PortalHeader } from "@/components/PortalHeader";

export default function NotFound() {
  return (
    <>
      <PortalHeader />
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-20 text-center">
        <p className="text-6xl font-extrabold text-[#903938]">404</p>
        <h1 className="text-2xl font-bold text-[#1e2f41]">
          Không tìm thấy trang
        </h1>
        <p className="max-w-md leading-7 text-[#52606d]">
          Trang bạn tìm không tồn tại trong bản mô phỏng. Bạn có thể quay lại
          trang chủ hoặc mở trợ lý VNeGuide để được hướng dẫn thủ tục.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex min-h-11 items-center rounded-lg bg-[#903938] px-5 font-bold text-white hover:bg-[#762b2b]"
          >
            Về trang chủ
          </Link>
        </div>
      </main>
      <PortalFooter />
    </>
  );
}
