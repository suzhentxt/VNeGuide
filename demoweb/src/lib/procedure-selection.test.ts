import assert from "node:assert/strict";
import test from "node:test";

import { getReceptionUnitLabel } from "./procedure-selection.ts";

test("keeps the reviewed portal authority label for the submission summary", () => {
  assert.equal(getReceptionUnitLabel("Công an phường Hải Châu"), "Công an phường Hải Châu");
});

test("rejects missing, control-character, or overlong authority labels", () => {
  assert.equal(getReceptionUnitLabel(undefined), undefined);
  assert.equal(getReceptionUnitLabel("Công an\nphường"), undefined);
  assert.equal(getReceptionUnitLabel("A".repeat(201)), undefined);
});
