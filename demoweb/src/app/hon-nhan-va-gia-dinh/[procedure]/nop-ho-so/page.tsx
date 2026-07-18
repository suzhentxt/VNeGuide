import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { JusticeShell } from "@/components/justice/JusticeShell";
import { MarriageApplication } from "@/components/justice/MarriageApplication";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
  withProcedureSelection,
} from "@/lib/procedure-selection";

interface ProcedureApplicationPageProps {
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
}: ProcedureApplicationPageProps): Promise<Metadata> {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    return {};
  }

  return {
    title: `Nộp hồ sơ - ${experience.title}`,
    description: `Mô phỏng quy trình nộp hồ sơ trực tuyến cho ${experience.title.toLocaleLowerCase("vi")}.`,
  };
}

export default async function ProcedureApplicationPage({
  params,
  searchParams,
}: ProcedureApplicationPageProps) {
  const [{ procedure }, query] = await Promise.all([params, searchParams]);
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    notFound();
  }

  const selectedService = getSelectedService(experience, query.service);
  const selectedReceptionUnit = getSelectedReceptionUnit(query.receptionUnit);

  if (!selectedService || !selectedReceptionUnit) {
    redirect(
      withProcedureSelection(experience.routes.apply, {
        receptionUnit: selectedReceptionUnit,
        serviceId: selectedService?.id,
      }),
    );
  }

  const initialStep = query.step === "3" ? 3 : 1;

  return (
    <JusticeShell activeNav="procedures">
      <MarriageApplication
        experience={experience}
        initialStep={initialStep}
        selectedReceptionUnit={selectedReceptionUnit}
        selectedServiceId={selectedService.id}
      />
    </JusticeShell>
  );
}
