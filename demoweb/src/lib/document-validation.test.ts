import assert from "node:assert/strict";
import test from "node:test";

import { documentBlockingMessages, documentRequirements } from "./document-validation.ts";

test("requires dwelling proof only when database lookup fails", () => {
  assert.deepEqual(documentRequirements({ legal_dwelling_data_retrievable: false }), {
    legal_dwelling: true,
    minor_consent: false,
  });
});

test("accepts CT01 consent without requiring a separate upload", () => {
  assert.equal(documentRequirements({ applicant_is_minor: true, minor_consent_present: true }).minor_consent, false);
  assert.equal(documentRequirements({ applicant_is_minor: true, minor_consent_present: false }).minor_consent, true);
});

test("pass and acknowledged review clear the document gate", () => {
  const required = { legal_dwelling: true, minor_consent: true };
  assert.deepEqual(documentBlockingMessages(required, {
    legal_dwelling: { status: "pass", reviewAcknowledged: false },
    minor_consent: { status: "needs_review", reviewAcknowledged: true },
  }), []);
});

test("wrong or pending documents remain blocked", () => {
  const messages = documentBlockingMessages(
    { legal_dwelling: true, minor_consent: true },
    {
      legal_dwelling: { status: "fail", reviewAcknowledged: false },
      minor_consent: { status: "running", reviewAcknowledged: false },
    },
  );
  assert.equal(messages.length, 2);
});
