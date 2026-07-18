import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { JusticeProcedureList } from "@/components/justice/JusticeProcedureList";
import { JusticeShell } from "@/components/justice/JusticeShell";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
} from "@/lib/procedure-selection";

interface OnlineProcedurePageProps {
  params: Promise<{ procedure: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export function generateStaticParams() {
  return additionalProcedureExperiences.map((experience) => ({
    procedure: experience.slug,
  }));
}

export async function generateMetadata({
  params,
}: OnlineProcedurePageProps): Promise<Metadata> {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    return {};
  }

  return {
    title: "Danh sách thủ tục | Hệ thống ngành Tư pháp",
    description: `Tra cứu và bắt đầu nộp hồ sơ trực tuyến cho ${experience.title.toLocaleLowerCase("vi")}.`,
  };
}

export default async function OnlineProcedurePage({
  params,
  searchParams,
}: OnlineProcedurePageProps) {
  const [{ procedure }, query] = await Promise.all([params, searchParams]);
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    notFound();
  }

  const selectedService = getSelectedService(experience, query.service);
  const selectedReceptionUnit = getSelectedReceptionUnit(query.receptionUnit);

  return (
    <JusticeShell activeNav="procedures">
      <JusticeProcedureList
        experience={experience}
        initialReceptionUnit={selectedReceptionUnit}
        initialServiceId={selectedService?.id}
      />
    </JusticeShell>
  );
}
