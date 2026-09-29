# Cashflow Assistant

A planned conversational cash-flow assistant for small-business owners, built for the Amazon Developer Hackathon 2026.

**Status: early implementation, 29 September 2026.** The backend can validate and import the synthetic dataset. Cash-flow forecasting, scenarios, the agent, the web interface, and every AWS connection are not built yet. The working project name may change.

Repository: <https://github.com/Hellinferno/Amazon-AI-builder-> — initial commit `91c7a70` pushed to `main` on 29 September 2026.

## Start here

1. Read [START_HERE.md](START_HERE.md) for Windows setup and the immediate task.
2. Follow [ROADMAP.md](ROADMAP.md) for dates, times in IST, and completion gates.
3. Use [TASKS.md](docs/TASKS.md) as the working checklist.
4. Read [PRD.md](docs/PRD.md), [ACCOUNTING_RULES.md](docs/ACCOUNTING_RULES.md), and [DATA_MODEL.md](docs/DATA_MODEL.md) before writing calculations.
5. Coding assistants should follow [AGENTS.md](AGENTS.md).

## Planned demonstration

A business owner asks whether payroll remains affordable when a customer pays late. The assistant reads structured records, calculates baseline and delayed-payment scenarios, shows supporting invoice IDs, and drafts a collection reminder for review.

Initial implementation: Python calculations, React interface, Amazon Bedrock with Strands orchestration, and a simulated Alexa+ interaction. Start with local storage; introduce S3 and DynamoDB after the core workflow is verified. No trained-from-scratch model is in this project scope.

## Documentation index

| File | Purpose |
| --- | --- |
| [START_HERE.md](START_HERE.md) | Install the docs and prepare VS Code |
| [AGENTS.md](AGENTS.md) | Instructions for coding assistants |
| [PRD.md](docs/PRD.md) | Users, scope, acceptance criteria |
| [ROADMAP.md](docs/ROADMAP.md) | Dated milestones and daily deadlines |
| [TASKS.md](docs/TASKS.md) | Implementation and release checklist |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components and integration flow |
| [ACCOUNTING_RULES.md](docs/ACCOUNTING_RULES.md) | Money, dates, cash flow, scenarios |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Proposed schema and import contract |
| [TOOLS_AND_API.md](docs/TOOLS_AND_API.md) | Agent tools and proposed API |
| [AWS_SETUP.md](docs/AWS_SETUP.md) | Phased AWS setup and cost controls |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | Calculation and integration evidence |
| [SECURITY.md](docs/SECURITY.md) | Data and credential handling |
| [DECISIONS.md](docs/DECISIONS.md) | Confirmed context and open decisions |
| [RESOURCES.md](docs/RESOURCES.md) | Official source links |
| [HACKATHON_CHECKLIST.md](submission/HACKATHON_CHECKLIST.md) | Submission requirements and access |
| [DEVPOST_DRAFT.md](submission/DEVPOST_DRAFT.md) | Draft narrative to finish after building |
| [DEMO_SCRIPT.md](submission/DEMO_SCRIPT.md) | Planned 2:45 demonstration |
| [PRODUCT_FEEDBACK.md](submission/PRODUCT_FEEDBACK.md) | Evidence-based feedback template |
| [FRICTION_LOG.md](submission/FRICTION_LOG.md) | Actual development issues and workarounds |

## Running the application

There is no runnable application yet. The backend is a Python library with tests. These commands were run on Windows 11 with Python 3.12.10 on 29 September 2026, from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e backend
.\.venv\Scripts\python.exe -m pytest backend -q
```

Expected result: `143 passed`. These commands also passed in a fresh copy of `backend/` and `data/` with a new virtual environment, and from a clean clone of commit `91c7a70` on 29 September 2026.

| Path | Contents |
| --- | --- |
| `backend/src/cashflow/` | Money and date types, schema validation, atomic CSV import |
| `backend/tests/` | Automated tests |
| `data/synthetic/demo-v1/` | Synthetic golden fixture and its expected results |

Do not treat the proposed API names in the docs as implemented.

## Release facts to fill in

- GitHub URL: https://github.com/Hellinferno/Amazon-AI-builder-
- Tested release commit: `91c7a70` (initial commit, 29 September 2026)
- Model ID, region, and dependency versions: TBD
- Demo video URL: TBD
- License choice and LICENSE file: TBD
- Live demo, if deployed: TBD

No license is granted by this documentation pack. Choose and add the appropriate license before publishing an open-source repository.
