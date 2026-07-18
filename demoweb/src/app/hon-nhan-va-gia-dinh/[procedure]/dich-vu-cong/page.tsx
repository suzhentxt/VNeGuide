import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MarriageServiceDirectory } from "@/components/national/MarriageServiceDirectory";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";

interface ProcedureServicesPageProps {
  params: Promise<{ procedure: string }>;
  searchParams: Promise<{ q?: string | string[] }>;
}

export function generateStaticParams() {
  return additionalProcedureExperiences.map((experience) => ({
    procedure: experience.slug,
  }));
}

export async function generateMetadata({
  params,
}: ProcedureServicesPageProps): Promise<Metadata> {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    return {};
  }

  return {
    title: `Danh sách dịch vụ công - ${experience.title}`,
    description: `Danh sách dịch vụ công trực tuyến dành cho ${experience.title.toLocaleLowerCase("vi")}.`,
  };
}

export default async function ProcedureServicesPage({
  params,
  searchParams,
}: ProcedureServicesPageProps) {
  const { procedure } = await params;
  const { q } = await searchParams;
  const experience = getProcedureExperience(procedure);
  const query = Array.isArray(q) ? (q[0] ?? "") : (q ?? "");

  if (!experience) {
    notFound();
  }

  return (
    <NationalPortalShell breadcrumbs={[{ label: "Danh sách dịch vụ công" }]}>
      <MarriageServiceDirectory experience={experience} query={query} />
    </NationalPortalShell>
  );
}
