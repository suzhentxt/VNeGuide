import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MarriageProcedureDetail } from "@/components/national/MarriageProcedureDetail";
import { NationalPortalShell } from "@/components/national/NationalPortalShell";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";

interface ProcedurePageProps {
  params: Promise<{ procedure: string }>;
}

export function generateStaticParams() {
  return additionalProcedureExperiences.map((experience) => ({
    procedure: experience.slug,
  }));
}

export async function generateMetadata({
  params,
}: ProcedurePageProps): Promise<Metadata> {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    return {};
  }

  return {
    title: `${experience.title} - Cổng Dịch vụ công Quốc gia`,
    description: `Chi tiết ${experience.title.toLocaleLowerCase("vi")}: trình tự, cách thức thực hiện, hồ sơ và cơ quan tiếp nhận.`,
  };
}

export default async function ProcedurePage({ params }: ProcedurePageProps) {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    notFound();
  }

  return (
    <NationalPortalShell
      breadcrumbs={[
        { label: "Thủ tục hành chính", href: experience.routes.services },
        { label: "Chi tiết thủ tục" },
      ]}
    >
      <MarriageProcedureDetail experience={experience} />
    </NationalPortalShell>
  );
}
