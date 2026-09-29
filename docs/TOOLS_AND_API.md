# Proposed tools and API

Status: design contract. Endpoints and tools below do not yet exist.

## Agent tools

Business identity and dataset version come from trusted session context, not arbitrary model arguments.

| Tool | Validated arguments | Result |
| --- | --- | --- |
| get_cashflow | horizon_end | Dated balances, minimum/date, closing cash, warnings, evidence |
| list_overdue_invoices | none | Open past-due amounts and source IDs |
| simulate_payment_delay | invoice_id, delay_days, horizon_end | Baseline and scenario, effective shifted date, difference, shortfall |
| get_record_evidence | record_type, record_id | Source fields and provenance within current dataset |
| draft_collection_reminder | invoice_id, tone | Editable unsent draft grounded in actual record |

Saving is an explicit application action, not an autonomous tool side effect. Return money as decimal strings with currency. Include `dataset_version` and `as_of_date` on every financial result.

## Response envelope

```json
{
  "status": "ok",
  "dataset_version": "demo-v1",
  "as_of_date": "2026-10-05",
  "currency": "INR",
  "facts": {},
  "evidence": [],
  "warnings": [],
  "error": null
}
```

Use `status: error` and a structured error code for invalid arguments, missing data, stale dataset, or provider failure. Never return invented financial facts after a tool error. Evidence entries use record type + ID + file/row reference.

## Proposed HTTP surface

| Method / route | Purpose |
| --- | --- |
| GET /health | Process readiness; no secrets or unnecessary provider calls |
| POST /api/datasets/import | Validate and atomically import records |
| POST /api/demo/reset | Restore synthetic fixture in local/demo mode only |
| POST /api/chat | Process conversation within selected dataset |
| POST /api/scenarios | Save explicitly approved scenario |
| GET /api/scenarios/{id} | Retrieve scenario after business-context check |
| GET /api/records/{type}/{id} | Read authorized supporting evidence |

Use appropriate 4xx errors for invalid inputs and access failures, and explicit 5xx/provider errors for service faults. Disable global demo-reset operations in any shared production environment.

## Conversation rules

Disambiguate customer/invoice names; show concrete dates for relative dates. Ask for missing financial assumptions. Limit agent loops, reject unrecognized tools, and give the UI a useful timeout error. An explanatory sentence must not change tool-returned money amounts. Treat requests to send reminders or transfer funds as unsupported actions in this MVP.

## Optional MCP

Expose the same tools through a real MCP server only after protocol/transport testing. Required competition version and source links live in submission/HACKATHON_CHECKLIST.md and docs/RESOURCES.md. Do not call ordinary REST endpoints an MCP implementation.
