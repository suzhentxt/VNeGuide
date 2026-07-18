# Mem0 long-term memory runbook

VNeGuide follows the Mem0 OSS lifecycle without replacing the existing conversation state:

1. `ConversationSession` remains the source of truth for draft, revision, suggestions and transcript.
2. Before a grounded NLG response, VNeGuide calls Mem0 `search` with `user_id`, `agent_id` and a fixed
   category filter.
3. After a turn, VNeGuide calls Mem0 `add(..., infer=False)` only when the user explicitly requests one
   of the allow-listed support styles: concise wording, simple wording or step-by-step guidance.
4. Raw transcript, names, addresses, identifiers and form values are never written to long-term memory.
5. Mem0/Qdrant failures are best-effort and must not change or discard the current draft.

## Install and enable locally

```powershell
python -m pip install -e ".[api,dev,memory]"
```

Long-term memory is disabled by default. Enabling the current adapter uses OpenAI embeddings, so do it
only after the application has obtained user consent for normalized support preferences:

```dotenv
VNEGUIDE_MEMORY_PROVIDER=mem0
VNEGUIDE_MEM0_ALLOW_EXTERNAL=1
VNEGUIDE_MEM0_EMBEDDING_MODEL=text-embedding-3-small
VNEGUIDE_MEM0_EMBEDDING_DIMS=1536
VNEGUIDE_MEM0_STORE_DIR=.vneguide-memory
VNEGUIDE_API_KEY=<secret supplied outside Git>
```

The client creating `POST /v1/chat/sessions` must include a stable, random `memory_scope_token` of
32–128 base64url characters. The API hashes this token before Mem0 sees it. The same token gives the
same anonymous `user_id` across sessions, while each chat session has a separate `run_id`. Never use a
name, phone number, email address or government identifier as this token.

```json
{
  "context": {"procedure_code": "1.004194"},
  "memory_scope_token": "<random-base64url-token-at-least-32-characters>"
}
```

`MEM0_TELEMETRY` is forced to `False` before the SDK is initialized. Vectors and history are stored in
the ignored `.vneguide-memory/` directory by default.

## Verification

```powershell
python -m pytest tests/unit/test_long_term_memory.py -q
```

The test suite exercises Mem0 `add` and `search` against embedded Qdrant with a deterministic local
embedder, so it makes no network request. A real embedding smoke requires an explicitly supplied API
key and synthetic, non-PII input.

## Production limitations

- The browser BFF does not yet create or retain `memory_scope_token`; `demoweb/**` was outside this
  change's owner scope. Existing web sessions therefore remain session-only.
- There is no user-facing consent/revoke screen or scoped deletion endpoint yet. Keep the provider
  disabled in production until those controls and HTTPS are available.
- This memory may adjust wording only. It is never evidence for eligibility, required documents,
  fees, deadlines, form values or any other business decision.
