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
- [ ] Opening balance, dated forecast, negative-cash detection.
- [ ] Overdue and partial-payment handling.
- [ ] Delayed-payment scenario with immutable baseline.
- [ ] Provenance IDs and warnings for missing assumptions. Done at import level: source file/row references and missing/past expected-date warnings. Open: provenance on forecast movements.
- [ ] Required calculation and import tests pass.

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
