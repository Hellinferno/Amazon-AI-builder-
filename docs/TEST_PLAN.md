# Verification plan

Status, 6 October 2026: 339 backend tests (232 engine, 107 application) and 5 frontend tests pass. The agent evaluation prompt set runs against the mock planner and scripted providers; the UI and persistence cases are covered by tests plus a mock-mode browser rehearsal. **Live AWS cases are not run**: no real Bedrock call has been made. The following cases define required evidence.

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
| 6 Oct 2026 | `ab77505` (pushed to origin/main) | Fresh clone into `D:\tmp\cashflow-clone-06oct`; new venv; `pip install -r backend\requirements-dev.txt`; `pip install -e backend`; `pytest backend -q` | Local, no model or AWS | 232 passed in 1.40s (Python 3.12.10) | <https://github.com/Hellinferno/Amazon-AI-builder-> |
| 6 Oct 2026 | Working tree after `facfec9` | Application layer: tool envelopes and golden values, argument validation, allowlist; the fixed prompt set (baseline, delayed customer, follow-up delay change, ambiguous customer, missing expected date, evidence request, reminder draft, send request, injected record text, provider timeout/error); orchestrator limits and grounding with scripted providers; saved scenarios, stale handling, local JSON store, reset; HTTP API via test client; configuration | Local, mock provider and scripted providers, no AWS | 339 passed in 3.4s (232 engine + 107 app) | `backend/tests/app/` |
| 6 Oct 2026 | Same | Frontend: golden dashboard render, chat → scenario switch with grounded chips, assistant failure keeps figures, backend unreachable alert, reminder draft editable and labelled unsent | jsdom, fetch mocked with the backend's envelope shapes | 5 passed (`npx vitest run`, vmThreads pool); `tsc --noEmit` clean; `vite build` ok | `frontend/src/test/App.test.tsx` |
| 6 Oct 2026 | Same | Mock-mode browser rehearsal: uvicorn on 127.0.0.1:8010 + Vite dev server; suggested question "What if Customer A pays two weeks late?", follow-up "Can we cover Friday's payroll if it is three weeks instead?", Save scenario, Reset sample | Local, mock | Dashboard switched to scenario (closing INR -15,000.00, first negative 9 Oct 2026, shortfall INR 15,000.00); follow-up reused INV-001 with 21 days and set the horizon to 9 Oct; saved scenario listed then cleared by reset; no console errors; screenshots unavailable in the preview tool, structure verified via the accessibility tree | docs/TASKS.md work-session record |
| 6 Oct 2026 | Same | Clean copy of `backend/`, `data/`, `frontend/` sources into `D:\tmp\cashflow-clean-06oct-b`; new venv; `pip install -r backend\requirements-dev.txt`; `pip install -e backend`; `pytest backend -q`; `npm ci`; `npm run build`; `vitest run` | Local, mock | Backend 339 passed in 7.18s (one `StarletteDeprecationWarning` because `httpx2` was absent; `httpx2` is now pinned). `npm ci` added 105 packages; `npm run build` first failed because `tsconfig.json` type-checked `vite.config.ts` (`process` undefined) — fixed by limiting `include` to `src`, after which the build succeeded in the copy; `vitest run` 5 passed | `D:\tmp\cashflow-clean-06oct-b` (not tracked) |
| — | — | Live AWS cases: one real Bedrock call, the prompt set against a real model trace, full rehearsal in live mode | — | NOT RUN (needs credentials and model access) | — |

Release gate: all critical money/date/import cases pass, real AWS evidence exists, README commands work, no unresolved data-leak/access defect, and demo results match the tested version.
