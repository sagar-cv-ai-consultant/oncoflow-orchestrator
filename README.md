# OncoFlow Orchestrator

Team_vaidya's oncology clinic-operations prototype for Health-a-thon 2026.
The current version is the **manual workflow milestone**: a shared patient
worklist with prerequisite checks, staff-recorded clearance, manual chair
assignment, and a persistent audit history. Automatic scheduling and AI
assistance are **not implemented** in this version.

Only fictional patient data belongs in this prototype. It is not a clinical
decision system or a production deployment.

## Requirements

- Python **3.10 or newer**. The migrated repository was tested with Python 3.12.
- Node.js **20.19+**, or Node.js **22.12+** on the Node 22 release line.
- npm, supplied with Node.js.

No Docker, Redis, PostgreSQL, messaging credentials, or AI API key is needed.

## First-time setup

Run commands from the cloned repository root:

```sh
cd /Users/sagardeyagond/sagar_dir/hackathon/koita/oncoflow-orchestrator
python3 --version
```

If the displayed Python is older than 3.10, use a newer interpreter such as
`python3.12` instead of `python3` in the next command.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci
```

On Windows, use `py -3 -m venv .venv` and
`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`.
The npm commands select the platform's virtual-environment interpreter.

## Run the application

```sh
npm run dev
```

This starts both services from one command:

- Dashboard: <http://127.0.0.1:5173/>
- Service health: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Keep the terminal open. Press **Ctrl+C** to stop both services.
If the previous app is still running in the parent directory, stop it first:
both versions use ports 5173 and 8000. Open the dashboard URL rather than
opening `frontend/index.html` as a file.

## Repository layout

```text
oncoflow-orchestrator/
├── backend/
│   ├── src/oncoflow/
│   │   ├── adapters/fhir.py  # Status-only report input
│   │   ├── api.py            # HTTP routes, errors and startup
│   │   ├── config.py         # Database and demo configuration
│   │   ├── domain.py         # PatientVisit entity and transition rules
│   │   ├── exceptions.py     # Explicit application errors
│   │   ├── fixtures.py       # Fictional seed visits
│   │   ├── repository.py     # SQLite transactions and audit persistence
│   │   ├── schemas.py        # Validated command contracts
│   │   └── service.py        # Application use cases
│   └── tests/                # Workflow and regression tests
├── frontend/
│   ├── src/
│   │   ├── components/       # Worklist, visit details, summary and audit UI
│   │   ├── hooks/            # Polling, commands and feedback state
│   │   ├── services/         # Typed HTTP client
│   │   ├── App.tsx
│   │   ├── constants.ts
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── types.ts
│   ├── index.html
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
│   ├── presentations/       # Phase I deck and supplied submission templates
│   ├── evidence/            # Existing demonstration screenshots
│   ├── ARCHITECTURE.md
│   ├── BUILD_PLAN.md
│   ├── DEMO_GUIDE.md
│   ├── EVIDENCE_LOG.md
│   └── MIGRATION.md
├── scripts/                  # Local process and Python command runners
├── .env.example
├── package.json
├── package-lock.json
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

Runtime folders `.venv/`, `node_modules/`, `data/`, and `dist/` are ignored by
Git. They are created locally, not copied into commits. There is no nested
repository or change to the clone's existing Git history.

## Code flow and object-oriented design

The React interface calls `ClinicApi`; `useClinic` owns synchronization and
feedback. FastAPI validates incoming commands and delegates to `ClinicService`.
`SQLiteVisitRepository` loads a `PatientVisit`, checks its version and event
identifier, applies the entity's transition rules, and saves the visit and
audit event in one transaction.

`PatientVisit` owns readiness and transition rules, `FHIRReportAdapter` owns
status filtering, and the repository owns persistence. React uses idiomatic
function components and hooks. Classes are used where they express a useful
responsibility, rather than adding inheritance to presentation components.

See [architecture](docs/ARCHITECTURE.md) for the full request flow.

## Tests and coding standards

```sh
npm test                 # Python workflow and regression tests
npm run lint             # Ruff checks and strict TypeScript checking
npm run format:check     # Python and frontend formatting checks
npm run build            # TypeScript check and frontend production build
npm run check            # All checks above
npm run format           # Apply consistent formatting
```

Python uses four-space indentation, type annotations, focused classes,
docstrings, sorted imports, and a 79-character line limit. Ruff checks include
PEP 8-related errors, unused code, and import ordering. TypeScript uses strict
checking and unused-variable checks. Prettier formats frontend code and scripts.
Tool versions and frontend dependency resolution are recorded in the
requirements files and lockfile.

Tests cover the complete manual visit journey, missing prerequisites,
separation of report finality and clearance, duplicate and stale events,
corrections during ongoing care, concurrent chair assignment, persistence,
input redaction, and clinical-value exclusion from the status adapter.

`npm run build` creates frontend assets in `dist/`. A production backend and
hosted deployment are not configured by that command.

## Database and configuration

The default database is `data/oncoflow.sqlite3` inside **this repository**.
It is created at service startup and initially contains twelve fictional
visits and six demo chairs. Updates survive restarts. A fresh clone starts
with a fresh fictional day; the parent folder's database is not imported.

Set `ONCOFLOW_DB` in the terminal to use another file. Relative paths resolve
against the repository root, not the terminal's current directory:

```sh
ONCOFLOW_DB=data/review-02.sqlite3 npm run dev
```

`.env.example` documents the setting. The application does **not** automatically
load `.env` files. Do not commit runtime databases or credentials.

## Demonstrate the workflow

1. Open OF-003 and inspect its pending CBC report.
2. Expand **Demo event controls** and set CBC to **Final**.
3. Start and complete the consultation.
4. Record clearance already supplied by a clinician, then pharmacy readiness.
5. Confirm the patient's return if needed, select a free chair, and start.
6. Complete infusion and discharge, then inspect the audit history.

For an exception scenario, change a report to **Corrected** during infusion.
The UI requests staff review without automatically interrupting ongoing care.
See the [demo guide](docs/DEMO_GUIDE.md) for the narrative and scope caveats.

## Current limits

- Local synthetic demo only. No authentication, role verification or verified
  clinician identity. Do not expose it to a network or use real patient data.
- All actions are manual. No automatic scheduler, learned model, LLM assistant,
  nurse/doctor capacity planning, patient portal or external notifications.
- Three-second polling, rather than WebSocket updates.
- A FHIR-shaped **demo** adapter, not a production HIS/LIS integration. Real
  source identity mapping, authentication and upstream ordering remain future
  integration work. No HL7 ingestion is implemented.
- Audit records are append-only through the application, not tamper-proof.
- No measured clinical benefit, real-world pilot, or clinician validation is
  claimed. Workflow assumptions still need the doctor partner's review.

The historical plan and evidence are in [docs](docs/EVIDENCE_LOG.md).
The repository migration does not add automatic scheduling or AI features.
