import type { Metadata } from "next";

import { MarriageServiceDirectory } from "@/components/national/MarriageServiceDirectory";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";
import { standardMarriageExperience } from "@/data/procedure-experiences";

export const metadata: Metadata = {
  title: "Danh sách dịch vụ công đăng ký kết hôn",
  description:
    "Danh sách dịch vụ công trực tuyến dành cho thủ tục đăng ký kết hôn.",
};

interface StandardMarriageServicesPageProps {
  searchParams: Promise<{ q?: string | string[] }>;
}

export default async function StandardMarriageServicesPage({
  searchParams,
}: StandardMarriageServicesPageProps) {
  const { q } = await searchParams;
  const query = Array.isArray(q) ? (q[0] ?? "") : (q ?? "");

  return (
    <NationalPortalShell
      breadcrumbs={[{ label: "Danh sách dịch vụ công" }]}
    >
      <MarriageServiceDirectory
        experience={standardMarriageExperience}
        query={query}
      />
    </NationalPortalShell>
  );
}
