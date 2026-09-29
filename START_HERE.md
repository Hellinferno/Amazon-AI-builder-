# Start here: Windows and VS Code

## Known setup

Ravi has joined the hackathon and reported Python 3.12.10, Node.js v24.12.0, Git 2.51.2.windows.1, and VS Code. These version checks are user-reported; package compatibility still needs a real install test. Project-folder creation is not confirmed.

The user has deferred the additional AWS credit request. Local development can proceed without it.

## Put these files in the project

Extract the ZIP to a temporary location. Copy the contents of its `cashflow-assistant` folder into your project folder, so `README.md` and `AGENTS.md` sit directly in the project root. Preserve any existing code. Compare an existing file before replacing it.

Open that project folder in VS Code. Use Terminal > New Terminal. If the project does not exist, create it first:

```powershell
mkdir cashflow-assistant
cd cashflow-assistant
code .
```

From inside the project folder, initialize Git only if it is not already a repository, and create a virtual environment only if one is not already present:

```powershell
git init
python -m venv .venv
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
```

Use Python: Select Interpreter from Ctrl+Shift+P and select `.venv\Scripts\python.exe`. Install Microsoft's Python extension if that command is unavailable. Direct interpreter commands avoid changing PowerShell execution policy.

Before committing, create a `.gitignore` excluding `.venv/`, `node_modules/`, `.env`, Python caches, local databases, real uploads, credentials, and build outputs. Do not ignore synthetic demo fixtures or lockfiles. This Markdown pack does not supply `.gitignore` or dependency manifests.

## First implementation task

Read the accounting and data contracts. Create a minimal Python package with money/date validation and deterministic cash-flow calculation. Create the synthetic fixture specified in [ACCOUNTING_RULES.md](docs/ACCOUNTING_RULES.md) and prove both expected results in automated tests before connecting a model.

Install dependencies only after creating and reviewing the actual project manifest. Pin the versions that pass the clean-install test.

## Suggested first coding-assistant instruction

Read AGENTS.md and docs/PRD.md, docs/ACCOUNTING_RULES.md, docs/DATA_MODEL.md, docs/TEST_PLAN.md, and docs/TASKS.md. Implement only milestone M1: the local accounting engine, synthetic fixture, and its tests. Use Python 3.12. Keep calculations independent of AWS and the UI. Update task statuses with actual evidence. Do not claim tests ran unless they did.

## When to connect AWS

After the engine gate, verify the account plan, active credits, expiry, region, and permitted model access. Make one small Bedrock call with real credentials supplied locally through the AWS credential chain. Follow [AWS_SETUP.md](docs/AWS_SETUP.md). Never paste keys into a chat or source file.
