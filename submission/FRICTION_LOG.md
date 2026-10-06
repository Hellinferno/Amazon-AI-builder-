# Development friction log

Status: three observed entries as of 6 October 2026. Entries are recorded as they happen, not reconstructed for submission.

The organizer permits optional friction entries describing real development problems. See [official rules](https://amazonappdev2026.devpost.com/rules).

### FL-001 — Vitest worker pools fail to start on Windows with a space in the project path

- Date/time and timezone: 6 October 2026, about 14:50 IST.
- Tool/API/SDK and version: Vitest 5.0.3, Node.js v24.12.0, Windows 11 Pro, project path `D:\AMAZON AI HACKATHON\frontend`.
- Task attempted: run the React component tests with `npx vitest run`.
- Minimal reproduction steps: create a Vite + React + jsdom project under a directory whose path contains spaces; run `vitest run` with the default pool.
- Expected result: tests execute.
- Actual result and sanitized error: `[vitest-pool]: Failed to start forks worker … Caused by: [vitest-pool-runner]: Timeout waiting for worker to respond` after 60 s. The stack trace shows the path URL-encoded (`AMAZON%20AI%20HACKATHON`). `--pool threads` worked once and then timed out the same way; `--pool vmThreads` started every time.
- Severity: major (blocked the frontend test suite).
- Impact on this project: about 20 minutes; the pool is now pinned to `vmThreads` in `frontend/vite.config.ts` with longer per-test timeouts because jsdom start-up is slow here (first test about 3 s).
- Workaround tried and outcome: `pool: "vmThreads"` plus `testTimeout: 30_000`; all five tests pass.
- Actionable improvement suggestion: make the worker start timeout configurable (it is a constant `START_TIMEOUT` in the bundle) and surface a clearer message when a worker cannot start.
- Evidence reference: `frontend/vite.config.ts` comment; TEST_PLAN.md evidence register.
- Status: worked around.

### FL-002 — jsdom 30 declares a Node engine range newer than the current Node 24 LTS line installed here

- Date/time and timezone: 6 October 2026, about 14:45 IST.
- Tool/API/SDK and version: jsdom 30.1.2 (`engines.node: ^22.22.2 || ^24.15.0 || >=26.0.0`), Node.js v24.12.0.
- Task attempted: `npm install` of the pinned frontend dev dependencies.
- Expected result: clean install.
- Actual result and sanitized error: `npm warn EBADENGINE` for jsdom; the package still installed and ran.
- Severity: minor.
- Impact on this project: pinned `jsdom` to 29.1.1 (engine `>=24.0.0`) so a clean install on a reviewer's Node 24 produces no engine warnings.
- Workaround tried and outcome: version pin; warning gone.
- Actionable improvement suggestion: none for the organizers; this is an ecosystem note.
- Evidence reference: `frontend/package.json`.
- Status: resolved.

### FL-003 — FastAPI 0.142 silently depends on `opentelemetry-api`

- Date/time and timezone: 6 October 2026, about 14:20 IST.
- Tool/API/SDK and version: FastAPI 0.142.2, pip 25.0.1.
- Task attempted: after trying `strands-agents` and removing it with its transitive dependencies, import FastAPI in tests.
- Expected result: FastAPI imports with its own declared dependencies intact.
- Actual result and sanitized error: `ImportError: cannot import name 'context' from 'opentelemetry' (unknown location)` from `fastapi/telemetry/_api.py` because `opentelemetry-api` had been removed together with the Strands tree.
- Severity: minor (self-inflicted by the uninstall, but the dependency was not obvious).
- Impact on this project: 5 minutes; reinstalling FastAPI restored it, and `requirements-dev.txt` now pins `opentelemetry-api==1.45.0`.
- Workaround tried and outcome: `pip install fastapi==0.142.2`; `pip check` reports no broken requirements.
- Actionable improvement suggestion: none for the organizers.
- Evidence reference: `backend/requirements-dev.txt`.
- Status: resolved.

## Logging guidance

Describe observations precisely. Separate an access restriction documented by the provider from a product defect. Strip credentials and real financial information from errors. Record successful workarounds and corrected misunderstandings as well as unresolved issues. A normal setup experience should remain normal; there is no quota for friction entries.

## Index

| ID | Tool | Short issue | Severity | Status |
| --- | --- | --- | --- | --- |
| FL-001 | Vitest 5.0.3 / Node 24.12 / Windows | Worker pool start timeout with a space in the path | major | worked around |
| FL-002 | jsdom 30.1.2 | Engine range excludes Node 24.12 | minor | resolved |
| FL-003 | FastAPI 0.142.2 | Undeclared-looking `opentelemetry-api` import after a dependency cleanup | minor | resolved |
