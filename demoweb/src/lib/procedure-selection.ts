import type { ProcedureExperience } from "@/data/procedure-experiences";

export const receptionUnits = [
  "Trung tâm phục vụ hành chính công, Thành phố Hà Nội",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 1",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 10",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 11",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 12",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 2",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 3",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 4",
  "Chi nhánh Trung tâm Phục vụ hành chính công số 5",
] as const;

type SearchParamValue = string | string[] | undefined;

export interface ProcedureSelection {
  receptionUnit?: string;
  serviceId?: string;
}

export function getSingleSearchParam(
  value: SearchParamValue,
): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function getSelectedService(
  experience: ProcedureExperience,
  value: SearchParamValue,
) {
  const serviceId = getSingleSearchParam(value);

  return serviceId
    ? experience.services.find((service) => service.id === serviceId)
    : undefined;
}

export function getSelectedReceptionUnit(
  value: SearchParamValue,
): (typeof receptionUnits)[number] | undefined {
  const receptionUnit = getSingleSearchParam(value);

  return receptionUnits.find((unit) => unit === receptionUnit);
}

export function withProcedureSelection(
  route: string,
  selection: ProcedureSelection,
  additionalParams: Record<string, string | undefined> = {},
) {
  const [pathname, currentQuery = ""] = route.split("?", 2);
  const query = new URLSearchParams(currentQuery);

  if (selection.serviceId) {
    query.set("service", selection.serviceId);
  }

  if (selection.receptionUnit) {
    query.set("receptionUnit", selection.receptionUnit);
  }

  Object.entries(additionalParams).forEach(([key, value]) => {
    if (value) {
      query.set(key, value);
    } else {
      query.delete(key);
    }
  });

  const serializedQuery = query.toString();
  return serializedQuery ? `${pathname}?${serializedQuery}` : pathname;
}

function getDeclarationStorageKey(
  experience: ProcedureExperience,
  selection: Required<ProcedureSelection>,
) {
  return [
    "demoweb:declaration-saved",
    experience.slug,
    selection.serviceId,
    selection.receptionUnit,
  ]
    .map(encodeURIComponent)
    .join(":");
}

export function hasSavedDeclaration(
  experience: ProcedureExperience,
  selection: Required<ProcedureSelection>,
) {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    return window.sessionStorage.getItem(
      getDeclarationStorageKey(experience, selection),
    ) === "1";
  } catch {
    return false;
  }
}

export function markDeclarationSaved(
  experience: ProcedureExperience,
  selection: Required<ProcedureSelection>,
) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(
      getDeclarationStorageKey(experience, selection),
      "1",
    );
  } catch {
    // The form remains usable when session storage is unavailable.
  }
}
