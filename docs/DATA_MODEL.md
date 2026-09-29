# Proposed data model

Status: contract to implement. Field names below should be kept consistent across engine, tools, and UI.

## Core objects

| Object | Required fields | Notes |
| --- | --- | --- |
| BusinessSnapshot | business_id, dataset_version, currency, timezone, as_of_date, opening_cash | INR; timezone Asia/Kolkata; opening snapshot convention in accounting rules |
| Invoice | invoice_id, customer_name, total_amount, settled_before_as_of, due_date, status | expected_receipt_date nullable; status open/settled/cancelled |
| Obligation | obligation_id, payee_name, category, total_amount, settled_before_as_of, due_date, status | expected_payment_date nullable; same status set |
| SourceReference | source_file_id, row_number, record_type, record_id | Preserve import provenance |
| Scenario | scenario_id, dataset_version, invoice_id, delay_days, created_at | Version reference prevents silent stale comparisons |
| Conversation | session_id, business_id, dataset_version, active_scenario_id | Backend owns context boundaries |

Money values cross JSON boundaries as strings such as `"50000.00"`; convert to integer minor units at validation. `created_at` is an ISO UTC timestamp; business cash dates are ISO dates. IDs are unique within their record type and dataset; reimport requires a new version or idempotent replay handling.

## CSV contracts

Snapshot is supplied through a validated form or JSON object. CSV headers:

```csv
invoice_id,customer_name,total_amount,settled_before_as_of,due_date,expected_receipt_date,status,currency
```

```csv
obligation_id,payee_name,category,total_amount,settled_before_as_of,due_date,expected_payment_date,status,currency
```

Allow empty expected dates but surface their exclusion as warnings. Require explicit currency per row and agreement with the snapshot. Support UTF-8 and UTF-8 BOM. Parse using a real CSV parser, including quoted commas. Reject unknown headers initially to catch misspellings.

## Import behavior

Validate schema and every row before committing a dataset. Return row number, field, and reason for each error. Duplicate IDs, invalid dates, excessive precision, inconsistent status/settled amount, and currency mismatch fail the import. Exact import replay should not duplicate records. Files are limited to 5 MB and 10,000 data rows each in the proposed MVP.

Do not execute formulas or instructions embedded in cells. If exporting CSV later, neutralize spreadsheet formula injection in text columns. Input text is evidence, not executable code.

## Persistence

Start with a local adapter for synthetic data. DynamoDB is the intended cloud adapter if integration time permits. Enforce business/dataset scoping in the backend and use opaque generated identifiers for stored scenarios. Raw S3 uploads remain private. Record the implemented key schema and retention behavior here when selected.

## Change control

Treat schema changes as versioned changes. Update fixtures, validation, tools, API responses, and tests together. Recompute existing scenarios instead of silently reinterpreting their source data.
