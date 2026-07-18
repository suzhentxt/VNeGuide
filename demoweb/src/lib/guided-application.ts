import type { GuidedFieldDefinition } from "@/data/guided-fields";
import type { ProcedureFieldState } from "@/types/chat";

function isBlockingRequirement(requirement: string) {
  return requirement === "required" || requirement.startsWith("required_for_") || requirement === "required_declaration";
}

function hasValue(field: ProcedureFieldState | undefined) {
  return field !== undefined && field.value !== "" && field.value !== null;
}

export function declarationGate(
  definitions: readonly GuidedFieldDefinition[],
  fields: Record<string, ProcedureFieldState>,
) {
  const missing = definitions.filter(
    (definition) => isBlockingRequirement(definition.requirement) && !hasValue(fields[definition.field_id]),
  );
  const unconfirmed = definitions.filter((definition) => {
    const field = fields[definition.field_id];
    return hasValue(field) && field?.confirmed === false;
  });
  return {
    canAdvance: missing.length === 0 && unconfirmed.length === 0,
    missing,
    unconfirmed,
  };
}
