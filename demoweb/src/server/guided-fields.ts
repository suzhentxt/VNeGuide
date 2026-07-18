import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import type { GuidedFieldDefinition } from "@/data/guided-fields";

const catalogPath = resolve(process.cwd(), "../data/catalog/field_catalog.json");

export async function loadGuidedFields(procedureCode: string): Promise<GuidedFieldDefinition[]> {
  const raw = await readFile(catalogPath, "utf8");
  const catalog = JSON.parse(raw) as Array<GuidedFieldDefinition & { procedure_code: string }>;
  return catalog.filter((field) => field.procedure_code === procedureCode);
}
