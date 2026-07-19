"""Drive the real VNeGuide session end-to-end against the configured LLM.

Verifies three behaviours the user cares about:
  1. Routing  — "xin lại giấy khai sinh" reaches BIRTH_CERTIFICATE_COPY.
  2. Q&A      — an informational follow-up yields a grounded advisory reply.
  3. Guardrail — an off-domain utterance is classified out of scope.

Run from the project root so ``create_session`` picks up ``.env``.
"""

from __future__ import annotations

import os
import sys

# Windows console defaults to cp1252, which cannot encode Vietnamese.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(_reconfigure):
    _reconfigure(encoding="utf-8", errors="replace")

# Make sure the local .env is honoured even if a stale env var points elsewhere.
os.environ.pop("VNEGUIDE_LLM_ENV_FILE", None)

from vneguide.core import create_session
from vneguide.domain import NextAction, ProcedureCode


def _bar(label: str) -> None:
    print(f"\n===== {label} =====")


def _describe(result) -> None:
    state = result.state
    print(f"next_action   : {result.next_action}")
    print(f"procedure_code: {state.draft.procedure_code}")
    print(f"pending_code  : {state.pending_procedure_code}")
    print(f"source_ids    : {result.source_ids}")
    print(f"reply         : {result.reply}")


def main() -> int:
    _bar("Booting session via create_session()")
    session = create_session()
    print(f"session type: {type(session).__name__}")

    _bar("1) ROUTING — 'Tôi cần xin lại giấy khai sinh'")
    r1 = session.send("Tôi cần xin lại giấy khai sinh")
    _describe(r1)
    routed = r1.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY or (
        r1.state.pending_procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY
    )
    print(f"-> routed to BIRTH_CERTIFICATE_COPY? {routed}")

    _bar("2) CONFIRM — 'Đúng' (activate the pending procedure)")
    r2 = session.send("Đúng")
    _describe(r2)
    print(f"-> procedure active? {r2.state.draft.procedure_code is ProcedureCode.BIRTH_CERTIFICATE_COPY}")

    _bar("3) Q&A — 'Lệ phí cấp bản sao giấy khai sinh là bao nhiêu?'")
    r3 = session.send("Lệ phí cấp bản sao giấy khai sinh là bao nhiêu?")
    _describe(r3)
    print(f"-> has source_ids (grounded)? {bool(r3.source_ids)}")

    _bar("4) GUARDRAIL — off-domain 'Thời tiết hôm nay thế nào?'")
    r4 = session.send("Thời tiết hôm nay thế nào?")
    _describe(r4)
    print(f"-> out of scope? {r4.next_action is NextAction.OUT_OF_SCOPE}")

    close = getattr(session, "close", None)
    if callable(close):
        close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
