# Work checklist

Status date: 29 September 2026. Checkboxes represent evidence-backed completion only. Refer to [ROADMAP.md](ROADMAP.md) for IST deadlines.

## Known context

- [x] User reports hackathon joined.
- [x] User reports Python, Node.js, Git, and VS Code available.
- [x] Initial Markdown documentation pack prepared.
- [x] Project folder and local virtual environment confirmed. Evidence: project root `D:\AMAZON AI HACKATHON`; interpreter `.venv\Scripts\python.exe`, Python 3.12.10.
- [x] GitHub repository URL recorded. Evidence: <https://github.com/Hellinferno/Amazon-AI-builder->; initial commit `91c7a70` pushed to `main` on 29 Sep 2026.

## M0 — 30 September, 10 p.m.

- [x] Install docs into project without overwriting unrelated work. Evidence: copied into an empty root; no existing file was replaced.
- [x] Add `.gitignore`, Python package manifest, and frontend manifest when scaffolded. Done: `.gitignore`, `backend/pyproject.toml`, committed in `91c7a70`. Open: frontend manifest (frontend not scaffolded; roadmap 10 Oct).
- [x] Confirm interpreter and compatible dependency versions. Evidence: pytest 9.1.1 installed and ran on Python 3.12.10; pins in `backend/requirements-dev.txt`. The engine has no runtime dependencies.
- [x] Create synthetic fixture and validate schema decisions. Evidence: `data/synthetic/demo-v1/`; `test_fixture.py` and `test_validation.py` pass; decisions recorded in DECISIONS.md.

## M1 — 6 October, 10 p.m.

- [x] Money/date validation; CSV parsing and atomic import. Evidence: 143 tests pass, 29 Sep 2026.
- [x] Opening balance, dated forecast, negative-cash detection. Evidence: `backend/src/cashflow/forecast.py`; `test_forecast.py` reproduces the golden daily table from `expected_results.json`, horizon boundaries, negative opening, first negative date, minimum/date, shortfall; 2 Oct 2026.
- [x] Overdue and partial-payment handling. Evidence: `backend/src/cashflow/overdue.py`; `test_overdue.py` (due before as-of only, due today not overdue, remainder after partial settlement, overdue plus future expected date coexist); partial settlement in `test_forecast.py` and `test_scenario.py`; 2 Oct 2026.
- [x] Delayed-payment scenario with immutable baseline. Evidence: `backend/src/cashflow/scenario.py`; `test_scenario.py` reproduces the INV-001 14-day golden result, zero-day identity, beyond-horizon retention, dataset immutability, stale-version rejection; 2 Oct 2026.
- [x] Provenance IDs and warnings for missing assumptions. Evidence: every `Movement` and `UnresolvedItem` carries source file/row, dataset version, currency, and assumption origin (`baseline` or `scenario:<id>`); forecast-level warnings list excluded and beyond-horizon items; 2 Oct 2026.
- [x] Required calculation and import tests pass. Evidence: `.venv\Scripts\python.exe -m pytest backend -q` → `215 passed`, 2 Oct 2026; see TEST_PLAN.md evidence register. Open for M1 gate (6 Oct): document engine usage in README, defect sweep.

## M2 — 12 October, 10 p.m.

- [ ] Confirm AWS plan, credits/expiry, region, and model access.
- [ ] Configure local AWS authentication and least-privilege permissions.
- [ ] Verify one real Bedrock call; record model/region and date.
- [ ] Integrate bounded Strands tool workflow.
- [ ] Implement frontend and structured results.
- [ ] Verify follow-up conversation and numerical grounding.

## M3 — 17 October, 10 p.m.

- [ ] Save/load scenarios and enforce dataset-version checks.
- [ ] Integrate selected storage adapters; document actual ones.
- [ ] Implement review-only reminder draft.
- [ ] Add evidence panels, sample reset, accessible controls, error states.
- [ ] Complete full rehearsal; decide optional feature cuts.

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
| 2 Oct 2026, afternoon | Roadmap items 2–5 Oct: dated baseline forecast and running balance; immutable delayed-receipt scenario; overdue report and missing-date warnings; boundary, partial-payment, duplicate-ID and invalid-import coverage | Three new modules (`forecast.py`, `scenario.py`, `overdue.py`) and three new test files; 72 new tests. Golden baseline and 14-day delay reproduce `expected_results.json` exactly. No defects found in the import layer; duplicate-ID and invalid-import rejection were already covered on 29 Sep and remain green. Engine decisions recorded in DECISIONS.md. Committed to `main` and pushed to origin on 2 Oct 2026 (see `git log`). | `.venv\Scripts\python.exe -m pytest backend -q` → `215 passed in 0.91s`; clean copy of `backend/` + `data/` in a fresh venv → `215 passed` | 6 Oct: M1 gate — README engine usage, defect sweep. 7 Oct: AWS/Bedrock access check |
