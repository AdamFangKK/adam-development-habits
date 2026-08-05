# Release Timeline

- **2026-07-31:** The retry refactor changed the outbound provider key from the full operation identity to `event_id:attempt` after a presumed collision report. The provider documents idempotency only for one caller-supplied key and exposes `reconcile(operation_identity)` for timeout recovery.
- **2026-08-02:** Support reported duplicate delivery alerts after provider timeouts. The dashboard reads provider delivery count; it does not initiate provider sends or queue acknowledgements.
- **2026-08-04:** Queue acknowledgements were observed after the second send attempt, but no trace proves whether the first provider call accepted before timing out.
