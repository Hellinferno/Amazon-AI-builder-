# Verification plan

Status: import, validation, money, and date tests run and pass as of 29 September 2026. Forecast, scenario, agent, UI, and clean-reproduction cases are not yet run. The following cases define required evidence.

## Deterministic accounting cases

| Case | Expected result |
| --- | --- |
| Golden baseline | Closing INR 25,000.00; no negative day |
| INV-001 delayed 14 days | Closing INR -15,000.00; first negative day 2026-10-09 |
| Delay of zero days | Exactly identical dated balances to baseline |
| Receipt outside horizon | Not counted within horizon; retained in scenario metadata |
| Horizon boundary | Cash on as-of and end date counted exactly once |
| Partial settlement | Only total minus settled-before-as-of is forecast |
| Historical transactions | Do not change opening cash or duplicate forecast receipts |
| Missing/past expected date | Open item excluded with explicit warning |
| Overdue status | Due before as-of and remaining > 0; due today is not overdue |
| Fully settled/cancelled | No forecast movement |
| No movements | Closing equals opening on every date |
| Negative opening | First day negative unless same-day net flow resolves it; show end-of-day convention |
| Immutable scenario | Baseline and other saved scenarios unchanged |
| Changed dataset | Stale saved scenario rejected or explicitly recomputed |
| Money precision | Decimal-string values round-trip without floating-point drift |

Golden inputs and calculations are in ACCOUNTING_RULES.md. Add conservation/property checks: closing equals opening plus total inflows minus total outflows, and identical records in a different order yield identical daily balances.

## Import and boundary tests

Reject duplicate IDs, malformed dates, mixed currencies, settled amounts above total, unknown headers, excessive precision, inconsistent status, oversized files, and row-limit overflow. An invalid row must not partially replace a valid dataset. Check BOM, quoted commas, and empty optional dates.

## Agent evaluation

Prepare a fixed prompt set: baseline question; delayed customer; follow-up delay change; ambiguous customer; missing expected date; request for evidence; draft reminder; unauthorized send request; injected instructions in invoice text; provider failure.

For each prompt record expected tool(s), returned record IDs, numerical correctness, context behavior, errors, and latency. A correct prose answer without actual tool invocation does not satisfy grounding. Run at least one real Bedrock path; keep mocks separate. Report counts and examples, not unsupported percentage claims.

## UI and persistence

Verify loading/error states, keyboard operation, text alternatives for charts, visible currency/as-of date, sample reset, unsent-draft labeling, save/reload, stale data warnings, and access isolation if hosted. Rehearse the full video on the frozen version.

## Clean reproduction

Use a fresh directory with documented prerequisites. Install from pinned manifests/lockfiles; run the documented commands; load the fixture; reproduce expected results. Record actual OS, versions, commit, and missing prerequisites. Verify both offline mock mode and authorized live mode with truthful labels.

## Evidence register

| Run date | Commit | Command/case | Mode | Result | Evidence location |
| --- | --- | --- | --- | --- | --- |
| 29 Sep 2026 | Uncommitted working tree | `.venv\Scripts\python.exe -m pytest backend -q` — money precision, date parsing, horizon bounds, schema validation, import and boundary tests, atomic commit, fixture load | Local, no model or AWS | 143 passed | `backend/tests` |
| — | — | Deterministic accounting cases that need the forecast or scenario engine | — | NOT RUN | — |

Release gate: all critical money/date/import cases pass, real AWS evidence exists, README commands work, no unresolved data-leak/access defect, and demo results match the tested version.
