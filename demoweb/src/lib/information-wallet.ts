import type { JsonValue, ProcedureFieldState } from "@/types/chat";

export interface InformationWallet {
  full_name?: JsonValue;
  date_of_birth?: JsonValue;
  personal_id?: JsonValue;
  residence?: JsonValue;
}

const aliases = {
  full_name: ["requester_full_name", "applicant_full_name"],
  date_of_birth: ["requester_date_of_birth", "applicant_date_of_birth"],
  personal_id: ["requester_personal_id", "applicant_personal_id"],
  residence: ["requester_residence"],
} as const;

export function createWallet(fields: Record<string, ProcedureFieldState>): InformationWallet {
  const wallet: InformationWallet = {};
  for (const [walletKey, fieldIds] of Object.entries(aliases)) {
    const field = fieldIds.map((fieldId) => fields[fieldId]).find(
      (candidate) => candidate?.confirmed && candidate.value !== "" && candidate.value !== null,
    );
    if (field) wallet[walletKey as keyof InformationWallet] = field.value;
  }
  return wallet;
}

export function walletValuesForProcedure(
  wallet: InformationWallet,
  availableFieldIds: readonly string[],
): Record<string, JsonValue> {
  const available = new Set(availableFieldIds);
  const values: Record<string, JsonValue> = {};
  for (const [walletKey, fieldIds] of Object.entries(aliases)) {
    const value = wallet[walletKey as keyof InformationWallet];
    if (value === undefined || value === null || value === "") continue;
    const fieldId = fieldIds.find((candidate) => available.has(candidate));
    if (fieldId) values[fieldId] = value;
  }
  return values;
}
