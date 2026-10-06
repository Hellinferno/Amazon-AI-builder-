# Security and data handling

Status: controls implemented locally on 6 October 2026 where noted below; verification belongs in TEST_PLAN.md. Implemented: business context from configuration only (imports for another `business_id` return 403); tool allowlist with argument validation; record text treated as data (injection test in `backend/tests/app/test_mock_conversation.py`); no send/transfer/filing capability; explicit-only scenario saves; localhost bind by default; CORS limited to the Vite dev origin; `.env` and `data/local/` git-ignored; `.env.example` holds names only.

## Data scope

Use synthetic records for development, demos, and published fixtures. Do not upload real customer bank statements or invoices without a separate data-handling decision. Display the dataset as synthetic in the UI and video.

## Credentials

Keep AWS credentials server-side in the supported credential chain. Exclude `.env`, local credentials, and sensitive logs from Git. Never place secrets in React build-time variables, screenshots, feedback entries, or README examples. If a credential is exposed, revoke/rotate it and inspect repository history before sharing.

## Access and storage

Private storage by default. Backend resolves business context and checks every record/scenario read. Do not accept tenant identity from unrestricted model arguments. A hosted demo needs access control, request throttling, and an isolated synthetic dataset per user/session or read-only sample mode. A localhost-only app must bind locally unless intentionally configured otherwise.

## Untrusted inputs

Validate CSV schema, size, row count, dates, and amounts. Imported document text is untrusted data. Agent instructions cannot be overridden by a record. Escape rendered text; avoid arbitrary HTML, SQL, shell execution, or dynamic code from model outputs. Limit tools to the implemented allowlist.

## Actions

The MVP drafts messages without sending. It does not initiate transfers, modify bank records, or submit filings. Saved scenarios are user-triggered. Keep an audit trail of dataset version and scenario assumptions without storing unnecessary personal data.

## Release review

Check repository, logs, video, and screenshots for credentials and real data. Test cross-session access if deployed. Document actual retention and deletion behavior. Provide reviewer credentials only through the appropriate private testing instructions, never in a public repository.
