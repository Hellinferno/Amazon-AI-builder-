# Work checklist

Status date: 6 October 2026. Checkboxes represent evidence-backed completion only. Refer to [ROADMAP.md](ROADMAP.md) for IST deadlines.

## Known context

- [x] User reports hackathon joined.
- [x] User reports Python, Node.js, Git, and VS Code available.
- [x] Initial Markdown documentation pack prepared.
- [x] Project folder and local virtual environment confirmed. Evidence: project root `D:\AMAZON AI HACKATHON`; interpreter `.venv\Scripts\python.exe`, Python 3.12.10.
- [x] GitHub repository URL recorded. Evidence: <https://github.com/Hellinferno/Amazon-AI-builder->; initial commit `91c7a70` pushed to `main` on 29 Sep 2026.

## M0 — 30 September, 10 p.m.

- [x] Install docs into project without overwriting unrelated work. Evidence: copied into an empty root; no existing file was replaced.
- [x] Add `.gitignore`, Python package manifest, and frontend manifest when scaffolded. Done: `.gitignore`, `backend/pyproject.toml` (`91c7a70`); `frontend/package.json` with exact pins and `package-lock.json` (6 Oct 2026).
- [x] Confirm interpreter and compatible dependency versions. Evidence: pytest 9.1.1 installed and ran on Python 3.12.10; pins in `backend/requirements-dev.txt`. The engine has no runtime dependencies.
- [x] Create synthetic fixture and validate schema decisions. Evidence: `data/synthetic/demo-v1/`; `test_fixture.py` and `test_validation.py` pass; decisions recorded in DECISIONS.md.

## M1 — 6 October, 10 p.m.

- [x] Money/date validation; CSV parsing and atomic import. Evidence: 143 tests pass, 29 Sep 2026.
- [x] Opening balance, dated forecast, negative-cash detection. Evidence: `backend/src/cashflow/forecast.py`; `test_forecast.py` reproduces the golden daily table from `expected_results.json`, horizon boundaries, negative opening, first negative date, minimum/date, shortfall; 2 Oct 2026.
- [x] Overdue and partial-payment handling. Evidence: `backend/src/cashflow/overdue.py`; `test_overdue.py` (due before as-of only, due today not overdue, remainder after partial settlement, overdue plus future expected date coexist); partial settlement in `test_forecast.py` and `test_scenario.py`; 2 Oct 2026.
- [x] Delayed-payment scenario with immutable baseline. Evidence: `backend/src/cashflow/scenario.py`; `test_scenario.py` reproduces the INV-001 14-day golden result, zero-day identity, beyond-horizon retention, dataset immutability, stale-version rejection; 2 Oct 2026.
- [x] Provenance IDs and warnings for missing assumptions. Evidence: every `Movement` and `UnresolvedItem` carries source file/row, dataset version, currency, and assumption origin (`baseline` or `scenario:<id>`); forecast-level warnings list excluded and beyond-horizon items; 2 Oct 2026.
- [x] Required calculation and import tests pass. Evidence: `.venv\Scripts\python.exe -m pytest backend -q` → `215 passed`, 2 Oct 2026; see TEST_PLAN.md evidence register.
- [x] M1 gate (6 Oct): engine usage documented in README (snippet re-run verbatim on 6 Oct and printed the golden values); defect sweep done. Two defects found and fixed: a non-`date` horizon raised a bare `TypeError` instead of `DateError`; `created_at` was never validated. Evidence: `232 passed`, 6 Oct 2026; clean-copy reproduction in a fresh venv (see TEST_PLAN.md).

## M2 — 12 October, 10 p.m.

- [ ] Confirm AWS plan, credits/expiry, region, and model access. **Needs the user**: no AWS CLI, boto3 credentials, or profile on the machine as of 6 Oct.
- [ ] Configure local AWS authentication and least-privilege permissions. **Needs the user.**
- [ ] Verify one real Bedrock call; record model/region and date. Blocked on the two items above; `BedrockConverseProvider` and `APP_MODE=live` configuration are ready (`backend/src/cashflow_app/agent/bedrock.py`).
- [x] Integrate bounded tool workflow. Done as one orchestrator with a provider interface (`cashflow_app.agent.orchestrator`); Strands deferred, see DECISIONS.md. Evidence: `backend/tests/app/test_orchestrator.py` (allowlist, tool-call limit, timeout/error preservation, grounding), 6 Oct 2026.
- [x] Implement frontend and structured results. Evidence: `frontend/` (Vite + React + TypeScript); `npm run build` succeeds; `npm test` → 5 passed; mock-mode browser rehearsal on 6 Oct 2026 (chat, tiles, chart, table, evidence, save, reset).
- [x] Verify follow-up conversation and numerical grounding in mock mode and with scripted providers. Evidence: `backend/tests/app/test_mock_conversation.py` (prompt set from TEST_PLAN.md) and `test_orchestrator.py` (ungrounded live text replaced, prose without tools cannot state money). **Open for M2 gate**: the same checks against a real Bedrock trace.

## M3 — 17 October, 10 p.m.

- [x] Save/load scenarios and enforce dataset-version checks. Evidence: `backend/tests/app/test_scenarios_storage.py` and `test_api.py` (save, list, get, stale 409, explicit recompute, delete, session rebinding on dataset change), 6 Oct 2026.
- [x] Integrate selected storage adapters; document actual ones. Actual: in-memory and local JSON (`data/local/scenarios.json`, atomic writes). DynamoDB and S3 not implemented; DATA_MODEL.md records the file format.
- [x] Implement review-only reminder draft. Evidence: `cashflow_app/reminder.py`; `test_tools.py` (`sent: false`, figures from the record); UI panel labelled "Draft only — not sent" with copy-to-clipboard only.
- [x] Add evidence panels, sample reset, accessible controls, error states. Evidence: `frontend/src/test/App.test.tsx` (backend unreachable alert, assistant failure keeps figures, draft editable); records list with source lookup; chart `role="img"` with description, keyboard-focusable day targets and table alternative; `aria-live` chat log; validated two-series palette in light and dark.
- [ ] Complete full rehearsal; decide optional feature cuts. Mock-mode rehearsal done 6 Oct (see work-session record); the full rehearsal needs live mode. Current cut list: MCP, voice, OCR, DynamoDB/S3 remain out unless time allows after a live call works.

## M4 — 21 October, 10 p.m.

- [ ] Complete TEST_PLAN evidence and clean-install rehearsal.
- [ ] Update README with commands that actually work.
- [ ] Finalize license/reviewer access route.
- [ ] Complete Devpost draft, feedback, genuine friction log, and video.
- [ ] Freeze and tag tested submission commit.

## M5 — 22 October, 8 p.m.

- [ ] Complete HACKATHON_CHECKLIST.
- [ ] Ravi reviews and submits Devpost entry.
- [ ] Verify submitted state, URLs, and reviewer access.
- [ ] Preserve reproducible version and access through judging.

## Optional / deferred

- [ ] Additional $150 credit request — deferred by user; see roadmap cutoff.
- [ ] MCP adapter after core demo works.
- [ ] Voice after text workflow works.
- [ ] OCR/PDF support after CSV workflow works.

## Work-session record

| Date/time IST | Task | Actual result | Evidence or command | Next action |
| --- | --- | --- | --- | --- |
| 29 Sep 2026, 16:59–17:05 | Roadmap items 28 Sep–1 Oct: docs install, Git/venv, backend package, money/date types, fixture, schema validation, atomic CSV import with source references | 143 tests passed. One defect found and fixed during the session: a method named `date` shadowed the `date` type in `validation.py`. Nothing committed to Git yet. Frontend manifest still open under M0. | `.venv\Scripts\python.exe -m pytest backend -q` → `143 passed in 0.29s` | 2 Oct: dated baseline forecast and running balance |
| 29 Sep 2026, evening | Initial commit pushed; repository URL recorded | Commit `91c7a70` (42 files) pushed to `origin/main`. Push first failed with 403 because the OS credential store held a different GitHub account; resolved with a repo-local credential helper that sources the GitHub CLI token for Hellinferno. Clean clone of the pushed commit reproduced the suite. | `git push -u origin main`; clean clone: `.venv\Scripts\python.exe -m pytest backend -q` → `143 passed` | 1–6 Oct: dated baseline forecast, running balance, delayed-receipt scenario (M1) |
| 6 Oct 2026, afternoon | Roadmap item 6 Oct: M1 gate — README engine usage, defect sweep | README snippet re-run verbatim and reproduced the golden values. Edge-case sweep over the engine API found two defects: `compute_forecast`/`apply_scenario` with a string, `datetime`, `None`, or integer horizon raised a bare `TypeError` (now `DateError`); `define_scenario` accepted any `created_at` including `None`, `"yesterday"`, naive timestamps, and non-UTC offsets (now rejected with code `invalid_created_at`; `apply_scenario` revalidates hand-built scenarios). 17 new tests. Import edge cases probed (leading blank line, whitespace-only row, trailing space in a header, `-0.00` opening cash, 13-digit amounts, duplicate plus invalid row, JSON-string snapshot) behaved as specified; no change needed. Readiness check for 7 Oct: no `aws` CLI on PATH, `boto3` and `strands` not installed in `.venv`, no credentials in the environment. | `.venv\Scripts\python.exe -m pytest backend -q` → `232 passed in 0.74s`; clean copy of `backend/` + `data/` in `D:\tmp\cashflow-clean-06oct` with a fresh venv → see TEST_PLAN.md | 7 Oct: verify AWS account, region, model access; install boto3/Strands; one real Bedrock call |
| 6 Oct 2026, 14:00–16:00 | User asked to complete every roadmap item that needs no credentials (8–16 Oct items): typed tools, bounded conversation loop, follow-up context, React shell and dashboard, backend connection, save/load scenarios, reminder draft, evidence panels, accessibility, error/timeout/injection tests | Built `cashflow_app` (tools, mock + Bedrock providers, orchestrator with grounding, service, FastAPI, local JSON store, sessions) and `frontend/`. Strands evaluated and deferred. Mock-mode browser rehearsal against the real backend: baseline question resolved "Friday" to 9 Oct; "Customer A two weeks late" switched the dashboard to the scenario (closing INR -15,000.00, first negative 9 Oct); follow-up "three weeks instead" reused INV-001; save and reset worked; no console errors. Three friction entries logged (FL-001–003). | `.venv\Scripts\python.exe -m pytest backend -q` → `339 passed`; `npm test` → 5 passed; `npm run build` ok; clean-copy reproduction recorded in TEST_PLAN.md | User: configure AWS credentials and model access, then run the first live Bedrock call (M2 gate) |
| 6 Oct 2026, later | Push M1 gate commits | First push returned 403 because the GitHub repository had been archived (read-only). User unarchived it; `30687fd` and `ab77505` pushed to `origin/main`. Fresh clone of `ab77505` into `D:\tmp\cashflow-clone-06oct` with a new venv reproduced the suite. | `git push origin main` → `a4e52e6..ab77505`; clone + `pytest backend -q` → `232 passed in 1.40s` | 7 Oct: AWS/Bedrock access check |
| 2 Oct 2026, afternoon | Roadmap items 2–5 Oct: dated baseline forecast and running balance; immutable delayed-receipt scenario; overdue report and missing-date warnings; boundary, partial-payment, duplicate-ID and invalid-import coverage | Three new modules (`forecast.py`, `scenario.py`, `overdue.py`) and three new test files; 72 new tests. Golden baseline and 14-day delay reproduce `expected_results.json` exactly. No defects found in the import layer; duplicate-ID and invalid-import rejection were already covered on 29 Sep and remain green. Engine decisions recorded in DECISIONS.md. Committed to `main` and pushed to origin on 2 Oct 2026 (see `git log`). | `.venv\Scripts\python.exe -m pytest backend -q` → `215 passed in 0.91s`; clean copy of `backend/` + `data/` in a fresh venv → `215 passed` | 6 Oct: M1 gate — README engine usage, defect sweep. 7 Oct: AWS/Bedrock access check |
