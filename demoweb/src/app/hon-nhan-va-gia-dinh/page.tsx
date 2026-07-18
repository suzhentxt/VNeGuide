import type { Metadata } from "next";

import { MarriageCategoryLanding } from "@/components/national/MarriageCategoryLanding";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";

export const metadata: Metadata = {
  title: "Ba thủ tục VNeGuide hỗ trợ",
  description:
    "Chuẩn bị hồ sơ cho đăng ký tạm trú, bản sao Giấy khai sinh và xác nhận điều kiện nhà ở.",
};

export default function MarriageCategoryPage() {
  return (
    <NationalPortalShell
      breadcrumbs={[{ label: "Dành cho công dân" }]}
    >
      <MarriageCategoryLanding />
    </NationalPortalShell>
  );
}
