# Decisions and project state

Updated 29 September 2026. Separate user-confirmed facts from proposed engineering choices.

## Confirmed context

- Ravi is studying applied AI/data science and CA.
- User has joined the Amazon Developer Hackathon.
- User intends to build the recommended finance assistant and use AWS.
- User reports $100 signup credits; account details are not verified.
- User deferred requesting additional credits until needed.
- User reports VS Code, Python 3.12.10, Node.js v24.12.0, Git 2.51.2.windows.1.
- User requested all project Markdown files and a dated/time-specific plan.

## Proposed implementation decisions

| Decision | Rationale | Revisit when |
| --- | --- | --- |
| Alexa+ simulated experience + AWS Builder | Fits the product and accessible tooling | Rules or scope change |
| Existing Bedrock model | Concentrate time on reliable workflow | Model access/cost prevents use |
| Deterministic Python money logic | Inspectable numerical outputs | Never delegate core arithmetic to prose generation |
| INR-only synthetic demo | Limits data/currency complexity | After MVP |
| React frontend | Interactive evidence and scenario display | Setup constraints emerge |
| Local storage then S3/DynamoDB | Keep engine independent of cloud setup | Core logic passes |
| MCP/voice/OCR optional | Protect submission schedule | M3 complete early |
| Workspace root is the project root | Docs pack says README/AGENTS sit in the project root | Project is renamed or moved |
| Engine uses the standard library only; pytest for tests | Nothing to pin or break for pure calculations | An HTTP framework is chosen |

## Schema decisions implemented 29 September 2026

These fill gaps the data contract left open. Each is enforced by tests in `backend/tests`.

| Decision | Detail |
| --- | --- |
| Amount format | ASCII digits, optional `.` and one or two decimals, up to 13 integer digits. No whitespace, `+`, separators, or exponents. JSON numbers are rejected; amounts must be strings. |
| Total amount | Must be greater than zero. |
| Status consistency | `open` requires settled < total; `settled` requires settled = total; `cancelled` allows any settled ≤ total. |
| IDs | 1–64 characters of letters, digits, `.`, `_`, `-`, starting with a letter or digit. Unique per record type; an invoice and an obligation may share an ID. |
| Text fields | Trimmed, non-empty, at most 200 characters, no control characters. Stored verbatim as data. |
| Date format | Strict `YYYY-MM-DD`. `due_date` is required; the expected date may be empty. |
| Header order | Any order is accepted; the set of headers must match exactly. |
| Row numbers | Spreadsheet-style: the header is row 1, the first data row is row 2. Blank lines are skipped but still counted. |
| Source file ID | `sha256:` plus the first 16 hex characters of the file's SHA-256. |
| Timing warnings | An open item with a missing expected date, or one before the as-of date, imports with a warning. It is not an error. |
| Reimport | Replaying identical content under the same `dataset_version` returns the stored dataset. Different content under an existing version is rejected. |
| Dataset store | In memory only. Persistence is scheduled for 13 October. |

## Open decisions

- Final project name and GitHub URL.
- Actual AWS plan, remaining credits, expiry, region, model ID and quotas.
- Backend HTTP framework, deployment and reviewer access path.
- Public licensed repository versus private reviewer access.
- Available daily work hours and whether team members will join.

## Change record

| Date | Change | Reason | Evidence/status |
| --- | --- | --- | --- |
| 28 Sep 2026 | Documentation baseline created | User requested Markdown pack and deadlines | Design only; no app code |
| 29 Sep 2026 | Backend package, synthetic fixture, schema validation, atomic CSV import | Roadmap items through 1 Oct | 143 tests pass; forecast engine not started |

Do not import unrelated competition submission artifacts or the separate model-training project into this repository.
