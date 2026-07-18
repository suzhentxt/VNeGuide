import assert from "node:assert/strict";
import test from "node:test";

import { declarationGate } from "./guided-application.ts";
import type { GuidedFieldDefinition } from "../data/guided-fields.ts";

const definitions: GuidedFieldDefinition[] = [
  { field_id: "name", label: "Họ tên", type: "string", requirement: "required" },
  { field_id: "note", label: "Ghi chú", type: "string", requirement: "optional" },
];

test("a required declaration field blocks the next step", () => {
  const result = declarationGate(definitions, {});
  assert.equal(result.canAdvance, false);
  assert.deepEqual(result.missing.map((field) => field.field_id), ["name"]);
});

test("wallet or assistant values require explicit confirmation", () => {
  const result = declarationGate(definitions, {
    name: {
      value: "NGUYEN VAN A",
      confirmed: false,
      dirty: true,
      source: "wallet",
      sync_status: "dirty",
      error: null,
    },
  });
  assert.equal(result.canAdvance, false);
  assert.deepEqual(result.unconfirmed.map((field) => field.field_id), ["name"]);
});

test("a self-entered or explicitly accepted value can advance", () => {
  const result = declarationGate(definitions, {
    name: {
      value: "NGUYEN VAN A",
      confirmed: true,
      dirty: true,
      source: "manual",
      sync_status: "dirty",
      error: null,
    },
  });
  assert.equal(result.canAdvance, true);
});
