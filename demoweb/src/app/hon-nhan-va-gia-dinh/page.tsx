import type { Metadata } from "next";

import { MarriageCategoryLanding } from "@/components/national/MarriageCategoryLanding";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";

export const metadata: Metadata = {
  title: "Hôn nhân và gia đình - Cổng Dịch vụ công Quốc gia",
  description:
    "Thông tin thủ tục hành chính và dịch vụ công trực tuyến trong lĩnh vực hôn nhân và gia đình.",
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
