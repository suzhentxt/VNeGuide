import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { CivilRecordEForm } from "@/components/justice/CivilRecordEForm";
import { JusticeShell } from "@/components/justice/JusticeShell";
import { MarriageEForm } from "@/components/justice/MarriageEForm";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
  withProcedureSelection,
} from "@/lib/procedure-selection";

interface ProcedureEFormPageProps {
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
}: ProcedureEFormPageProps): Promise<Metadata> {
  const { procedure } = await params;
  const experience = getProcedureExperience(procedure);

  if (!experience) {
    return {};
  }

  return {
    title: `Tờ khai - ${experience.title}`,
    description: `Mẫu hộ tịch điện tử tương tác cho ${experience.title.toLocaleLowerCase("vi")}.`,
  };
}

export default async function ProcedureEFormPage({
  params,
  searchParams,
}: ProcedureEFormPageProps) {
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

  return (
    <JusticeShell activeNav="procedures">
      {experience.formKind === "marriage" ? (
        <MarriageEForm
          experience={experience}
          selectedReceptionUnit={selectedReceptionUnit}
          selectedServiceId={selectedService.id}
        />
      ) : (
        <CivilRecordEForm
          experience={experience}
          selectedReceptionUnit={selectedReceptionUnit}
          selectedServiceId={selectedService.id}
        />
      )}
    </JusticeShell>
  );
}
