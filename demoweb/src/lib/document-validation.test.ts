import assert from "node:assert/strict";
import test from "node:test";

import {
  documentBlockingMessages,
  documentRequirements,
  documentResultPresentation,
} from "./document-validation.ts";

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

test("only a strict pass clears the document gate", () => {
  const required = { legal_dwelling: true, minor_consent: true };
  const messages = documentBlockingMessages(required, {
    legal_dwelling: { status: "pass" },
    minor_consent: { status: "needs_review" },
  });
  assert.deepEqual(messages, ["Ý kiến đồng ý của cha, mẹ hoặc người giám hộ: không hợp lệ, cần thay tài liệu"]);
});

test("wrong or pending documents remain blocked", () => {
  const messages = documentBlockingMessages(
    { legal_dwelling: true, minor_consent: true },
    {
      legal_dwelling: { status: "fail" },
      minor_consent: { status: "running" },
    },
  );
  assert.equal(messages.length, 2);
});

test("shows exactly two terminal document results", () => {
  assert.equal(documentResultPresentation("pass"), "valid_official_review");
  assert.equal(documentResultPresentation("fail"), "invalid");
  assert.equal(documentResultPresentation("needs_review"), "invalid");
  assert.equal(documentResultPresentation("error"), "invalid");
  assert.equal(documentResultPresentation("running"), null);
  assert.equal(documentResultPresentation("idle"), null);
});
