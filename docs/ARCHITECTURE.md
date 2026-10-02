# Proposed architecture

Status: design, not deployed infrastructure.

## Components

| Component | Responsibility | Initial / later |
| --- | --- | --- |
| React frontend | Conversation, sample loading, evidence, scenarios | Initial |
| Python HTTP backend | Validate requests, select business context, orchestrate calls | Initial |
| Pure accounting module | Money arithmetic, dated balances, overdue lists | Initial |
| Strands agent with Bedrock | Choose tools and explain validated results | After engine |
| Storage adapter | Persist records and scenarios | Local first; DynamoDB later |
| File adapter | Save source files and record provenance | Local synthetic files first; S3 later |
| Optional MCP adapter | Expose the same typed tools via Streamable HTTP | Stretch |

Use an ordinary Python backend framework selected during scaffolding. Keep cloud calls behind adapters so engine tests need no credentials. A local frontend/backend calling Bedrock can demonstrate AWS usage; deployment is a separate implementation decision.

## Request flow

1. Frontend sends a question and selected session/dataset version.
2. Backend resolves authorized business context; the model cannot choose arbitrary tenant IDs.
3. Agent chooses validated accounting tools.
4. Tools load records, compute deterministic results, and return evidence and warnings.
5. Agent summarizes results; numeric output is checked against returned facts.
6. UI displays the answer, source records, and optional scenario comparison.
7. Explicit Save persists the scenario; draft reminders stay local to review.

## Proposed source layout

- `backend/`: package manifest, app, accounting, schemas, agent, storage adapters, tests.
- `frontend/`: React app, package manifest, lockfile, component tests.
- `data/synthetic/`: reproducible fixture files with provenance.
- `docs/`: design, setup, accounting, test, and planning documents.
- `submission/`: hackathon checklist and authored submission material.
- `infra/`: optional reproducible deployment configuration.

As of 2 October 2026, `backend/` (pure accounting module and tests) and `data/synthetic/` exist; `frontend/` and `infra/` do not. Create code directories as needed.

## Reliability decisions

Use a configurable limit on agent tool calls and output length. Validate tool arguments and responses. Preserve computation results if model explanation fails. Return an explicit service error instead of silently replacing live responses with mocks. Prevent retries from duplicating imports or saved scenarios.

## Optional MCP

Only claim MCP compatibility after a real client handshake, tool-list call, and tool invocation pass with the required protocol and transport. The simulation path remains the submission route unless the working implementation is explicitly changed and documented.
