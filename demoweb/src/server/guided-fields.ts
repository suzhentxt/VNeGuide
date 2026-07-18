import fieldCatalog from "../../../data/catalog/field_catalog.json";
import type { GuidedFieldDefinition } from "@/data/guided-fields";

const catalog = fieldCatalog as Array<GuidedFieldDefinition & { procedure_code: string }>;

export async function loadGuidedFields(procedureCode: string): Promise<GuidedFieldDefinition[]> {
  return catalog.filter((field) => field.procedure_code === procedureCode);
}
