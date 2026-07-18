import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import Link from "next/link";
import { JusticeShell } from "@/components/justice/JusticeShell";
import { TemporaryResidenceForm } from "@/components/forms/TemporaryResidenceForm";
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
    description: `Biểu mẫu mô phỏng hỗ trợ chuẩn bị ${experience.title.toLocaleLowerCase("vi")}.`,
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
      {experience.formKind === "temporary-residence" ? (
        <TemporaryResidenceForm
          experience={experience}
          selectedReceptionUnit={selectedReceptionUnit}
          selectedServiceId={selectedService.id}
        />
      ) : (
        <main className="min-h-[60vh] bg-[#f3f6f8] px-4 py-12">
          <section className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow-sm sm:p-10">
            <p className="text-sm font-bold tracking-widest text-[#903938] uppercase">Mã {experience.code}</p>
            <h1 className="mt-2 text-2xl font-extrabold text-[#1e2f41]">{experience.shortTitle}</h1>
            <p className="mt-4 leading-7 text-[#52606d]">
              Luồng này đã nằm trong phạm vi hỗ trợ và có thể trao đổi với chatbox. Biểu mẫu sâu hiện ưu tiên cho thủ tục 1.004194 — Đăng ký tạm trú.
            </p>
            <Link className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-[#903938] px-5 font-bold text-white" href={experience.routes.detail}>
              Xem hướng dẫn thủ tục
            </Link>
          </section>
        </main>
      )}
    </JusticeShell>
  );
}
