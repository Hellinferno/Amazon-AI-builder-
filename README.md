# Cashflow Assistant

A conversational cash-flow assistant for small-business owners, built for the Amazon Developer Hackathon 2026 as a **simulated Alexa+ web experience** on AWS (Amazon Bedrock).

**Status, 6 October 2026: the full local product runs in mock mode.** The deterministic accounting engine, six typed tools, a bounded tool-calling conversation loop with a numerical grounding check, a FastAPI backend with local scenario persistence, and a React interface are implemented and tested. The Amazon Bedrock provider is written but has **not** been exercised against a real AWS account yet; every model-driven answer so far came from the visibly labelled mock planner. Nothing is deployed.

Repository: <https://github.com/Hellinferno/Amazon-AI-builder->

## Start here

1. Read [START_HERE.md](START_HERE.md) for Windows setup and the immediate task.
2. Follow [ROADMAP.md](ROADMAP.md) for dates, times in IST, and completion gates.
3. Use [TASKS.md](docs/TASKS.md) as the working checklist.
4. Read [PRD.md](docs/PRD.md), [ACCOUNTING_RULES.md](docs/ACCOUNTING_RULES.md), and [DATA_MODEL.md](docs/DATA_MODEL.md) before writing calculations.
5. Coding assistants should follow [AGENTS.md](AGENTS.md).

## What it does

A business owner asks whether payroll remains affordable when a customer pays late. The assistant calls read-only accounting tools over structured records, shows the baseline and the delayed-payment scenario side by side with supporting invoice IDs, and drafts a collection reminder for review. Every figure in an answer must come from a tool result; the backend checks this and replaces any ungrounded explanation with a template built from the tool output.

The demo uses a synthetic dataset (`data/synthetic/demo-v1`, as-of 5 October 2026, INR). The interface says so on every screen.

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
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Schema and import contract |
| [TOOLS_AND_API.md](docs/TOOLS_AND_API.md) | Implemented agent tools and HTTP API |
| [AWS_SETUP.md](docs/AWS_SETUP.md) | Phased AWS setup and cost controls |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | Calculation and integration evidence |
| [SECURITY.md](docs/SECURITY.md) | Data and credential handling |
| [DECISIONS.md](docs/DECISIONS.md) | Confirmed context and decisions |
| [RESOURCES.md](docs/RESOURCES.md) | Official source links |
| [HACKATHON_CHECKLIST.md](submission/HACKATHON_CHECKLIST.md) | Submission requirements and access |
| [DEVPOST_DRAFT.md](submission/DEVPOST_DRAFT.md) | Draft narrative to finish after building |
| [DEMO_SCRIPT.md](submission/DEMO_SCRIPT.md) | Planned 2:45 demonstration |
| [PRODUCT_FEEDBACK.md](submission/PRODUCT_FEEDBACK.md) | Evidence-based feedback template |
| [FRICTION_LOG.md](submission/FRICTION_LOG.md) | Actual development issues and workarounds |

## Running the application

Prerequisites: Python 3.12, Node.js 20 or newer (tested with 24.12), Git. These commands were run on Windows 11 on 6 October 2026 from the project root in PowerShell. Nothing below needs an AWS account.

### Backend (mock mode, default)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e backend
.\.venv\Scripts\python.exe -m pytest backend -q
.\.venv\Scripts\python.exe -m uvicorn cashflow_app.main:app --host 127.0.0.1 --port 8000
```

Expected test result: `339 passed` (232 engine tests plus 107 application tests). The server loads the synthetic fixture and serves <http://127.0.0.1:8000/docs>. Mock mode is the default: a rule-based planner drives the same tools the model would use, and every answer ends with a visible mock-mode footer. Configuration names are listed in [.env.example](.env.example); copy it to `.env` or set variables in the shell.

### Frontend

```powershell
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Expected: `5 passed` component tests; the dev server at <http://127.0.0.1:5173> proxies `/api` to the backend on port 8000 (set `BACKEND_URL` to point elsewhere, for example `$env:BACKEND_URL="http://127.0.0.1:8010"`). Open the page, pick “What if Customer A pays two weeks late?”, then “And if it is three weeks instead?”. The tiles, chart, and table switch to the scenario; the records list shows the rows behind each figure; “Save scenario” stores it in `data/local/scenarios.json`; “Reset sample” restores the fixture.

### Live mode (Amazon Bedrock)

Not yet verified in this repository. When an AWS account with Bedrock access is available, authenticate through the standard credential chain and set:

```powershell
$env:APP_MODE="live"; $env:AWS_REGION="<region>"; $env:BEDROCK_MODEL_ID="<model or inference profile ID>"
```

The server refuses to start in live mode without both values. The first real call and its evidence (date, region, model, token usage) must be recorded in [TEST_PLAN.md](docs/TEST_PLAN.md) before any AWS integration is claimed.

## Code layout

| Path | Contents |
| --- | --- |
| `backend/src/cashflow/` | Pure accounting engine: integer-paise money, strict dates, atomic CSV import, dated forecast, delayed-receipt scenario, overdue report. No dependencies. |
| `backend/src/cashflow_app/tools.py` | Six typed read-only tools with the shared response envelope and record evidence |
| `backend/src/cashflow_app/agent/` | Provider interface, mock planner, Bedrock Converse provider, template composer, bounded orchestrator with grounding check |
| `backend/src/cashflow_app/service.py`, `api.py`, `storage.py`, `session.py` | Business-context resolution, FastAPI routes, scenario stores, conversation sessions |
| `backend/tests/` | Engine tests; `backend/tests/app/` holds tool, conversation, orchestrator, storage, API, and config tests |
| `frontend/src/` | React app: chat, summary tiles, accessible balance chart and table, scenario save/load, evidence panel, editable unsent reminder draft, CSV import, reset |
| `data/synthetic/demo-v1/` | Synthetic golden fixture and its expected results |

Engine usage from Python (dates are `datetime.date` values; `created_at` is an ISO 8601 UTC timestamp). This snippet was run verbatim on 6 October 2026:

```python
from datetime import date
from pathlib import Path
import json

from cashflow.importer import import_dataset
from cashflow.forecast import compute_forecast
from cashflow.scenario import define_scenario, apply_scenario
from cashflow.overdue import overdue_report

fixture = Path("data/synthetic/demo-v1")
snapshot = json.loads((fixture / "snapshot.json").read_text(encoding="utf-8"))
result = import_dataset(
    snapshot, (fixture / "invoices.csv").read_bytes(), (fixture / "obligations.csv").read_bytes()
)
assert result.ok, result.errors
dataset = result.dataset

baseline = compute_forecast(dataset, date(2026, 10, 9))
print(baseline.as_dict()["daily_closing"])   # {'2026-10-05': '50000.00', ..., '2026-10-09': '25000.00'}

scenario = define_scenario(
    dataset, "INV-001", 14, scenario_id="demo-delay", created_at="2026-10-05T09:00:00Z"
)
delayed = apply_scenario(dataset, scenario, date(2026, 10, 9))
print(delayed.as_dict()["closing_cash"], delayed.as_dict()["first_negative_date"])  # -15000.00 2026-10-09

print(overdue_report(dataset).as_dict()["invoices"])  # [] for the golden fixture
```

## Release facts to fill in

- GitHub URL: https://github.com/Hellinferno/Amazon-AI-builder-
- Latest commit reproduced from a fresh clone: see TEST_PLAN.md evidence register; release commit TBD
- Model ID and region: TBD (live mode unverified)
- Demo video URL: TBD
- License choice and LICENSE file: TBD
- Live demo, if deployed: TBD

No license is granted by this documentation pack. Choose and add the appropriate license before publishing an open-source repository.
