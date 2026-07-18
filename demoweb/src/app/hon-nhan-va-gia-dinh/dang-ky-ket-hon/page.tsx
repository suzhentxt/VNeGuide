import type { Metadata } from "next";

import { MarriageProcedureDetail } from "@/components/national/MarriageProcedureDetail";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";
import { marriageRoutes } from "@/data/marriage";

export const metadata: Metadata = {
  title: "Thủ tục đăng ký kết hôn - Cổng Dịch vụ công Quốc gia",
  description:
    "Chi tiết thủ tục đăng ký kết hôn: trình tự, cách thức thực hiện, hồ sơ và cơ quan tiếp nhận.",
};

export default function MarriageProcedurePage() {
  return (
    <NationalPortalShell
      breadcrumbs={[
        { label: "Thủ tục hành chính", href: marriageRoutes.services },
        { label: "Chi tiết thủ tục" },
      ]}
    >
      <MarriageProcedureDetail />
    </NationalPortalShell>
  );
}
