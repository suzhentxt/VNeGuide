import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";

import { JusticeShell } from "@/components/justice/JusticeShell";
import { MarriageApplication } from "@/components/justice/MarriageApplication";
import { RedirectNotice } from "@/components/RedirectNotice";
import {
  additionalProcedureExperiences,
  getProcedureExperience,
} from "@/data/procedure-experiences";
import {
  getReceptionUnitLabel,
  getSelectedService,
} from "@/lib/procedure-selection";
import { loadGuidedFields } from "@/server/guided-fields";

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
  const selectedReceptionUnit = getReceptionUnitLabel(query.receptionUnit);
  const serviceConfirmed = query.confirmed === "1";

  if (!selectedService || !selectedReceptionUnit || !serviceConfirmed) {
    redirect(`${experience.routes.detail}?canh_bao=chua_chon_dich_vu`);
  }

  const initialStep = query.step === "3" ? 3 : 1;
  const guidedFields = await loadGuidedFields(experience.code);

  return (
    <JusticeShell activeNav="procedures">
      <Suspense fallback={null}>
        <RedirectNotice />
      </Suspense>
      <MarriageApplication
        experience={experience}
        guidedFields={guidedFields}
        initialStep={initialStep}
        selectedReceptionUnit={selectedReceptionUnit}
        selectedServiceId={selectedService.id}
      />
    </JusticeShell>
  );
}
