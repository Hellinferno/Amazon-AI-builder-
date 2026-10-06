# Proposed architecture

Status: implemented locally as of 6 October 2026 (engine, tools, bounded conversation loop with a mock provider, FastAPI backend, local JSON persistence, React frontend). Not deployed; the live Bedrock path is written but unverified.

## Components

| Component | Responsibility | Initial / later |
| --- | --- | --- |
| React frontend (`frontend/`, Vite + TypeScript) | Conversation, sample loading, evidence, scenarios, reminder draft | Built 6 Oct |
| Python HTTP backend (`cashflow_app.api`, FastAPI) | Validate requests, resolve business context, call the service layer | Built 6 Oct |
| Pure accounting module (`cashflow`) | Money arithmetic, dated balances, overdue lists | Built 2 Oct |
| Typed tools (`cashflow_app.tools`) | Six read-only tools over the engine with the shared envelope | Built 6 Oct |
| Bounded conversation loop (`cashflow_app.agent`) | Provider interface; mock planner; Bedrock Converse provider; grounding check | Mock verified 6 Oct; live unverified |
| Scenario storage (`cashflow_app.storage`) | In-memory and local JSON adapters | Built 6 Oct; DynamoDB later |
| File adapter | Source files are read from `data/synthetic/`; uploads are validated in memory | S3 later |
| Optional MCP adapter | Expose the same typed tools via Streamable HTTP | Not started |

Cloud calls sit behind the provider interface so engine, tool, and API tests need no credentials. A local frontend/backend calling Bedrock can demonstrate AWS usage; deployment is a separate implementation decision. Strands was evaluated on 6 October and deferred: its custom-model interface is a streaming event protocol, which would have made the offline mock as complex as the live path; see DECISIONS.md.

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

As of 6 October 2026, `backend/` (packages `cashflow` and `cashflow_app`, tests under `backend/tests/` and `backend/tests/app/`), `frontend/` (Vite + React + TypeScript with Vitest tests), and `data/synthetic/` exist. `data/local/` holds the git-ignored scenario store. `infra/` does not exist.

## Reliability decisions

Use a configurable limit on agent tool calls and output length. Validate tool arguments and responses. Preserve computation results if model explanation fails. Return an explicit service error instead of silently replacing live responses with mocks. Prevent retries from duplicating imports or saved scenarios.

## Optional MCP

Only claim MCP compatibility after a real client handshake, tool-list call, and tool invocation pass with the required protocol and transport. The simulation path remains the submission route unless the working implementation is explicitly changed and documented.
