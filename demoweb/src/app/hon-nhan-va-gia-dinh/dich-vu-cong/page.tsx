import type { Metadata } from "next";

import { MarriageServiceDirectory } from "@/components/national/MarriageServiceDirectory";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";
import { procedureExperiences } from "@/data/procedure-experiences";

export const metadata: Metadata = {
  title: "Danh sách ba thủ tục VNeGuide hỗ trợ",
  description:
    "Danh sách ba thủ tục đã có data package được xác minh.",
};

interface MarriageServicesPageProps {
  searchParams: Promise<{ q?: string | string[] }>;
}

export default async function MarriageServicesPage({
  searchParams,
}: MarriageServicesPageProps) {
  const { q } = await searchParams;
  const query = Array.isArray(q) ? (q[0] ?? "") : (q ?? "");

  return (
    <NationalPortalShell
      breadcrumbs={[{ label: "Danh sách dịch vụ công" }]}
    >
      <MarriageServiceDirectory
        experiences={procedureExperiences}
        query={query}
      />
    </NationalPortalShell>
  );
}
