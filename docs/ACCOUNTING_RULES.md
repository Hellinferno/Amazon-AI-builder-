# Accounting calculation contract

Status: MVP product specification; not professional accounting or tax guidance.

## Money and period conventions

Use INR only in the MVP, represented as integer paise internally. API/CSV amounts are nonnegative decimal strings with at most two decimal places. Reject excess precision, non-finite values, negative inputs where prohibited, and mixed currencies. Opening balance may be negative. Signed forecast movements derive from inflow/outflow type.

Every dataset has an explicit `as_of_date`. Opening cash is the bank cash available at the **start** of that date. It already includes transactions before that date. Forecast interval is inclusive: `[as_of_date, horizon_end]`. Cash-flow rows on the as-of date are included exactly once. Horizon must not precede as-of and is capped at 90 days for the MVP.

Dates are ISO calendar dates in the business timezone, initially Asia/Kolkata. Resolve “next Friday” into a displayed date and confirm if ambiguous. The synthetic demo uses fixed dates regardless of today's clock.

## Formula and evidence

Closing cash on date d = opening cash + sum of expected future receipts through d − sum of unpaid obligations through d.

Display end-of-day balances, lowest projected balance/date, first negative date, and shortfall below zero. This is a date-level planning estimate; same-day payment ordering is not modeled. A nonnegative end-of-day balance does not prove intraday liquidity.

Each movement carries source ID, effective date, amount, currency, dataset version, and assumption origin. Show missing-date warnings and distinguish cash forecasts from revenue/profit.

## Open items and actual records

For invoices and obligations: remaining amount = total amount − amount settled **before** as-of. Reject settled amount exceeding total. Fully settled and cancelled items produce no projected movement.

Expected dates on/after as-of and within the horizon generate movements. Missing dates or dates before as-of on still-open items are excluded from the timed forecast and shown as unresolved; never silently move them to today. Overdue means due date < as-of and remaining amount > 0. Future expected receipt dates can coexist with overdue status.

Historical transactions support evidence only in this MVP. Do not add them to the opening balance or to projected receipts. Current-day actual reconciliation is outside scope; dataset authors must keep the opening snapshot and unsettled amounts consistent.

## Scenarios

A scenario shifts the expected date of one open invoice by nonnegative calendar days. Base date must exist and be on/after as-of. Shifted dates beyond the horizon remove that receipt from the horizon total but retain it in scenario metadata. A scenario never edits baseline records. Saved scenarios bind to the dataset version; stale scenarios must be recomputed.

## Golden synthetic fixture

As-of: 2026-10-05. Horizon: 2026-10-09. Opening cash: INR 50,000.00. All amounts below are unsettled; no other movements exist.

| Record | Kind | Due / expected date | Amount INR |
| --- | --- | --- | --- |
| INV-001 | Customer A receipt | 2026-10-07 | 40,000.00 |
| INV-002 | Customer B receipt | 2026-10-09 | 15,000.00 |
| BILL-001 | Rent payment | 2026-10-06 | 10,000.00 |
| PAY-001 | Payroll payment | 2026-10-09 | 70,000.00 |

| Date | Baseline closing INR | INV-001 delayed 14 days: closing INR |
| --- | --- | --- |
| 2026-10-05 | 50,000.00 | 50,000.00 |
| 2026-10-06 | 40,000.00 | 40,000.00 |
| 2026-10-07 | 80,000.00 | 40,000.00 |
| 2026-10-08 | 80,000.00 | 40,000.00 |
| 2026-10-09 | 25,000.00 | -15,000.00 |

Baseline closing: 50,000 + 40,000 + 15,000 − 10,000 − 70,000 = INR 25,000.
Delayed INV-001 date: 2026-10-21. Scenario closing: INR -15,000. Difference from baseline: INR -40,000. First negative date: 9 October. Minimum additional cash to reach zero by that end-of-day: INR 15,000; no safety buffer is assumed.

This is synthetic planning data, not an observed business outcome. These expected results are the test oracle; `backend/tests/test_forecast.py` and `test_scenario.py` reproduce both columns from `data/synthetic/demo-v1/expected_results.json` as of 2 October 2026.
