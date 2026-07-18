import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { JusticeShell } from "@/components/justice/JusticeShell";
import { MarriageEForm } from "@/components/justice/MarriageEForm";
import { standardMarriageExperience } from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
  withProcedureSelection,
} from "@/lib/procedure-selection";

export const metadata: Metadata = {
  title: "Tờ khai đăng ký kết hôn",
  description: "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn.",
};

interface MarriageEFormPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function MarriageEFormPage({
  searchParams,
}: MarriageEFormPageProps) {
  const query = await searchParams;
  const selectedService = getSelectedService(
    standardMarriageExperience,
    query.service,
  );
  const selectedReceptionUnit = getSelectedReceptionUnit(query.receptionUnit);

  if (!selectedService || !selectedReceptionUnit) {
    redirect(
      withProcedureSelection(standardMarriageExperience.routes.apply, {
        receptionUnit: selectedReceptionUnit,
        serviceId: selectedService?.id,
      }),
    );
  }

  return (
    <JusticeShell activeNav="procedures">
      <MarriageEForm
        selectedReceptionUnit={selectedReceptionUnit}
        selectedServiceId={selectedService.id}
      />
    </JusticeShell>
  );
}
