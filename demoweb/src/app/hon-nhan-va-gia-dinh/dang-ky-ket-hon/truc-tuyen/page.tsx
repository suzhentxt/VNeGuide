import type { Metadata } from "next";

import { JusticeProcedureList } from "@/components/justice/JusticeProcedureList";
import { JusticeShell } from "@/components/justice/JusticeShell";
import { standardMarriageExperience } from "@/data/procedure-experiences";
import {
  getSelectedReceptionUnit,
  getSelectedService,
} from "@/lib/procedure-selection";

export const metadata: Metadata = {
  title: "Danh sách thủ tục | Hệ thống ngành Tư pháp",
  description:
    "Tra cứu và bắt đầu nộp hồ sơ trực tuyến cho thủ tục đăng ký kết hôn.",
};

interface OnlineMarriageProcedurePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function OnlineMarriageProcedurePage({
  searchParams,
}: OnlineMarriageProcedurePageProps) {
  const query = await searchParams;
  const selectedService = getSelectedService(
    standardMarriageExperience,
    query.service,
  );
  const selectedReceptionUnit = getSelectedReceptionUnit(query.receptionUnit);

  return (
    <JusticeShell activeNav="procedures">
      <JusticeProcedureList
        initialReceptionUnit={selectedReceptionUnit}
        initialServiceId={selectedService?.id}
      />
    </JusticeShell>
  );
}
