import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { JusticeShell } from "@/components/justice/JusticeShell";
import { MarriageApplication } from "@/components/justice/MarriageApplication";
import { standardMarriageExperience } from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
  withProcedureSelection,
} from "@/lib/procedure-selection";

export const metadata: Metadata = {
  title: "Nộp hồ sơ đăng ký kết hôn",
  description:
    "Mô phỏng quy trình nộp hồ sơ trực tuyến cho thủ tục đăng ký kết hôn.",
};

interface MarriageApplicationPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function MarriageApplicationPage({
  searchParams,
}: MarriageApplicationPageProps) {
  const params = await searchParams;
  const selectedService = getSelectedService(
    standardMarriageExperience,
    params.service,
  );
  const selectedReceptionUnit = getSelectedReceptionUnit(
    params.receptionUnit,
  );

  if (!selectedService || !selectedReceptionUnit) {
    redirect(
      withProcedureSelection(standardMarriageExperience.routes.apply, {
        receptionUnit: selectedReceptionUnit,
        serviceId: selectedService?.id,
      }),
    );
  }

  const initialStep = params.step === "3" ? 3 : 1;

  return (
    <JusticeShell activeNav="procedures">
      <MarriageApplication
        initialStep={initialStep}
        selectedReceptionUnit={selectedReceptionUnit}
        selectedServiceId={selectedService.id}
      />
    </JusticeShell>
  );
}
