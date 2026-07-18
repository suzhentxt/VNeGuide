# Context-aware extraction evaluation

The runner is locked to `data/evaluation/synthetic_multiturn_extraction.jsonl`, which contains only invented
Vietnamese requests. Each follow-up turn carries the active procedure and target field that
the conversation core passes to
`ExtractionTurnContext(active_procedure_code, expected_field_id)`. Cases without an active
procedure pass `context=None`.

Default tests use a fake extractor and never call a network service:

```powershell
python -m pytest tests/evals/test_extraction_evaluator.py -q
```

Run the real provider only with explicit acknowledgement and synthetic data:

```powershell
python -m tests.evals.run_live_extraction_eval `
  --confirm-live `
  --env-file .env `
  --output C:\tmp\vneguide-extraction-eval.json
```

Before it loads/builds a provider, the command verifies the fixture against
`data/qa/synthetic_multiturn_extraction.jsonl.sha256` using the data-package LF normalization
rule. A missing, malformed, renamed, or mismatched fixture/manifest fails closed without making a
provider call. The command also refuses the mock provider and refuses to overwrite a report. The report contains
only provider/model metadata, UTC timestamp, fixture hash, aggregate intent/procedure accuracy,
exact slot precision/recall/F1, evidence-grounding rate, fallback rate, counts, and aggregate
latency. It also records the Git revision, working-tree dirty flag and LF-normalized fixture
SHA-256. It does not include case
messages, evidence strings, raw model output, API keys, or an environment dump.

Slot scoring namespaces form fields and rule-context signals separately. A wrong value counts as
one false positive and one false negative. Procedure accuracy is measured only on cases with an
expected supported procedure; intent accuracy uses every case. Grounding checks every predicted
field/signal evidence span against the current message only.

Text cases expect only signals whose reviewed origin is `intent_extraction` or
`user_declaration`. Signals with origin `document_check` are intentionally absent: they must come
from a validated document/OCR adapter, not from a user's text claim.
