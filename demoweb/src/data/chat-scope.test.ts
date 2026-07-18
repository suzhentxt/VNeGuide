import assert from "node:assert/strict";
import test from "node:test";

import { getConfirmedProcedureRoute, getProcedureContextByCode } from "./chat-scope.ts";

test("every supported service first opens its confirmed detail page", () => {
  for (const code of ["2.000635", "1.013314", "1.004194"]) {
    const procedure = getProcedureContextByCode(code);
    const route = getConfirmedProcedureRoute(code);
    assert.ok(procedure);
    assert.ok(route?.includes(`/hon-nhan-va-gia-dinh/${procedure.slug}?`));
    assert.ok(route?.includes("confirmed=1"));
    assert.ok(!route?.includes("nop-ho-so"));
  }
});

test("an unsupported code cannot navigate to a procedure page", () => {
  assert.equal(getConfirmedProcedureRoute("unsupported"), null);
});
