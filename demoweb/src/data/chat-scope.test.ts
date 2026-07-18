import assert from "node:assert/strict";
import test from "node:test";

import { getConfirmedSubmissionRoute, getProcedureContextByCode } from "./chat-scope.ts";

test("every supported service has an explicit confirmed submission route", () => {
  for (const code of ["2.000635", "1.013314", "1.004194"]) {
    const procedure = getProcedureContextByCode(code);
    const route = getConfirmedSubmissionRoute(code);
    assert.ok(procedure);
    assert.ok(route?.includes(`/hon-nhan-va-gia-dinh/${procedure.slug}/nop-ho-so?`));
    assert.ok(route?.includes("confirmed=1"));
    assert.ok(route?.includes(`service=${procedure.serviceId}`));
  }
});

test("an unsupported code cannot navigate to a submission page", () => {
  assert.equal(getConfirmedSubmissionRoute("unsupported"), null);
});
