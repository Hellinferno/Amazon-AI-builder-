# Verification plan

Status: import, validation, money, date, forecast, scenario, and overdue tests run and pass as of 6 October 2026 (232 tests; the M1 defect sweep added 17). The 29 September subset was also reproduced from a clean clone of the pushed initial commit `91c7a70`. Agent and UI cases are not yet run. The following cases define required evidence.

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
| 29 Sep 2026 | `91c7a70` (pushed to origin/main) | Clean clone of the pushed commit; `.venv\Scripts\python.exe -m pytest backend -q` | Local, no model or AWS | 143 passed | <https://github.com/Hellinferno/Amazon-AI-builder-> |
| 2 Oct 2026 | Uncommitted working tree on top of `b60b40b` | `.venv\Scripts\python.exe -m pytest backend -q` — all deterministic accounting cases above: golden baseline, INV-001 delayed 14 days, zero-day delay, receipt outside horizon, horizon boundary, partial settlement, settled amounts not double-counted, missing/past expected date, overdue status, settled/cancelled, no movements, negative opening, immutable scenario, changed dataset, money precision, conservation, order independence; plus the 29 Sep import and boundary tests | Local, no model or AWS | 215 passed in 0.91s | `backend/tests/test_forecast.py`, `test_scenario.py`, `test_overdue.py` |
| 2 Oct 2026 | Same working tree | Clean copy of `backend/` and `data/` into `D:\tmp\cashflow-clean`; new venv; `pip install -r backend\requirements-dev.txt`; `pip install -e backend`; `pytest backend -q` | Local, no model or AWS | 215 passed in 0.91s (Python 3.12.10) | `D:\tmp\cashflow-clean` (not tracked) |
| 6 Oct 2026 | Uncommitted working tree on top of `a4e52e6` | M1 defect sweep: non-`date` horizon rejected with `DateError` (string, `datetime`, `None`, int); `created_at` must be an ISO 8601 UTC timestamp (`invalid_created_at`), revalidated on apply; README engine-usage snippet re-run verbatim | Local, no model or AWS | 232 passed in 0.74s | `backend/tests/test_dates.py`, `test_forecast.py`, `test_scenario.py` |
| 6 Oct 2026 | Same working tree | Clean copy of `backend/` and `data/` into `D:\tmp\cashflow-clean-06oct`; new venv; `pip install -r backend\requirements-dev.txt`; `pip install -e backend`; `pytest backend -q` | Local, no model or AWS | 232 passed in 0.85s (Python 3.12.10) | `D:\tmp\cashflow-clean-06oct` (not tracked) |
| 6 Oct 2026 | `ab77505` (pushed to origin/main) | Fresh clone into `D:	mp\cashflow-clone-06oct`; new venv; `pip install -r backendequirements-dev.txt`; `pip install -e backend`; `pytest backend -q` | Local, no model or AWS | 232 passed in 1.40s (Python 3.12.10) | <https://github.com/Hellinferno/Amazon-AI-builder-> |
| — | — | Agent evaluation, UI, persistence, live AWS cases | — | NOT RUN | — |

Release gate: all critical money/date/import cases pass, real AWS evidence exists, README commands work, no unresolved data-leak/access defect, and demo results match the tested version.
