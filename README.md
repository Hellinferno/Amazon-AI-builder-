# Cashflow Assistant

A planned conversational cash-flow assistant for small-business owners, built for the Amazon Developer Hackathon 2026.

**Status: accounting engine complete (milestone M1 passed), 6 October 2026.** The backend validates and imports the synthetic dataset, computes the dated baseline forecast, simulates a delayed receipt without touching the baseline, and reports overdue items, all with source-row provenance. The agent, the web interface, persistence, and every AWS connection are not built yet. The working project name may change.

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

There is no runnable application yet. The backend is a Python library with tests. These commands were run on Windows 11 with Python 3.12.10 on 6 October 2026, from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e backend
.\.venv\Scripts\python.exe -m pytest backend -q
```

Expected result: `232 passed`. These commands also passed on 6 October 2026 in a fresh copy of `backend/` and `data/` with a new virtual environment. The 29 September subset (143 tests) was reproduced from a clean clone of commit `91c7a70`.

| Path | Contents |
| --- | --- |
| `backend/src/cashflow/money.py`, `dates.py`, `models.py` | Integer-paise money, strict ISO dates, frozen domain records |
| `backend/src/cashflow/validation.py`, `importer.py` | Schema validation, atomic CSV import, in-memory dataset store |
| `backend/src/cashflow/forecast.py` | Dated baseline forecast: daily balances, minimum, first negative date, shortfall, provenance |
| `backend/src/cashflow/scenario.py` | Delayed-receipt scenario bound to a dataset version; baseline stays immutable |
| `backend/src/cashflow/overdue.py` | Overdue invoices and obligations as of the snapshot date |
| `backend/tests/` | Automated tests, including the golden fixture oracle |
| `data/synthetic/demo-v1/` | Synthetic golden fixture and its expected results |

Engine usage from Python, with the fixture loaded (this is the library API; the HTTP and agent layers are not built yet). Dates are passed as `datetime.date` values; parse text dates with `cashflow.dates.parse_date`. `created_at` must be an ISO 8601 UTC timestamp. The snippet below was run verbatim on 6 October 2026 and printed the values in the comments:

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

Do not treat the proposed API names in the docs as implemented.

## Release facts to fill in

- GitHub URL: https://github.com/Hellinferno/Amazon-AI-builder-
- Tested release commit: `91c7a70` (initial commit, 29 September 2026)
- Model ID, region, and dependency versions: TBD
- Demo video URL: TBD
- License choice and LICENSE file: TBD
- Live demo, if deployed: TBD

No license is granted by this documentation pack. Choose and add the appropriate license before publishing an open-source repository.
